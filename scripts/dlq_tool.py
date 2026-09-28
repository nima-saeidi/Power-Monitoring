#!/usr/bin/env python3
"""
Operator CLI for the dead-letter queues used across this project's RabbitMQ
services. Every service in this repo that consumes from a queue declares a
matching "<queue_name>.dlq" via a fanout dead-letter-exchange (see
notification_service/main.py, logging_service/core/consumer.py,
postgres_storage_service/main.py, timeseries_storage_service/main.py,
main_api/core/broker.py) - a message that a consumer can't process (bad JSON,
an unhandled exception) ends up there instead of being lost or looping
forever. Nothing reads those DLQs afterwards, so without this tool they're a
write-only graveyard: a message that lands there stays there, unnoticed,
until someone manually opens the RabbitMQ management UI.

Usage:
    python scripts/dlq_tool.py status                     # depth of every known DLQ
    python scripts/dlq_tool.py status -q notification_events
    python scripts/dlq_tool.py peek notification_events -n 5     # non-destructive
    python scripts/dlq_tool.py replay notification_events -n 10  # move N back to the live queue
    python scripts/dlq_tool.py replay notification_events --all
    python scripts/dlq_tool.py purge notification_events --yes   # discard everything, no undo
    python scripts/dlq_tool.py watch --interval 60         # poll depths, warn on stdout when >0

Connects via RABBITMQ_URL if set, else RABBITMQ_HOST/PORT/USER/PASSWORD
(same env vars every service in this repo already reads), or --url.
Defaults assume you're running this on the host against the docker-compose
RabbitMQ, whose management/AMQP ports are published to 127.0.0.1 only.
"""
import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass

import aio_pika

# (label, queue_name) - the live queue name a DLQ message should be replayed
# back onto. Keep this in sync with the queue names declared in each
# service's own _declare_*_with_dlq() call.
KNOWN_QUEUES = [
    ("notification_service - email/SMS alerts", "notification_events"),
    ("logging_service / notification_service - audit & service logs", "logs_queue"),
    ("postgres_storage_service - settings/users/posts/links DB writes", "db.settings.write"),
    ("timeseries_storage_service - telemetry ingestion", "telemetry_timeseries_queue"),
]


def resolve_rabbitmq_url(cli_url: str | None) -> str:
    if cli_url:
        return cli_url
    if os.environ.get("RABBITMQ_URL"):
        return os.environ["RABBITMQ_URL"]
    host = os.environ.get("RABBITMQ_HOST", "localhost")
    port = os.environ.get("RABBITMQ_PORT", "5672")
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASSWORD", "guest")
    return f"amqp://{user}:{password}@{host}:{port}/"


@dataclass
class DlqStatus:
    label: str
    queue: str
    dlq: str
    count: int | None  # None means the DLQ doesn't exist yet (never dead-lettered anything)


async def _dlq_count(connection: aio_pika.RobustConnection, dlq_name: str) -> int | None:
    channel = await connection.channel()
    try:
        queue = await channel.declare_queue(dlq_name, durable=True, passive=True)
        return queue.declaration_result.message_count
    except aio_pika.exceptions.ChannelClosed:
        return None
    finally:
        if not channel.is_closed:
            await channel.close()


async def cmd_status(connection: aio_pika.RobustConnection, only_queue: str | None) -> None:
    targets = KNOWN_QUEUES if not only_queue else [
        (label, q) for label, q in KNOWN_QUEUES if q == only_queue
    ] or [("(unregistered queue - not one of this project's known queues)", only_queue)]

    results = []
    for label, queue in targets:
        dlq = f"{queue}.dlq"
        count = await _dlq_count(connection, dlq)
        results.append(DlqStatus(label, queue, dlq, count))

    width = max(len(r.dlq) for r in results)
    print(f"{'DLQ':<{width}}  {'MESSAGES':>8}  SOURCE QUEUE")
    any_pending = False
    for r in results:
        if r.count is None:
            print(f"{r.dlq:<{width}}  {'—':>8}  {r.label} (no DLQ yet, nothing has failed)")
        else:
            flag = "  ⚠️  needs attention" if r.count > 0 else ""
            any_pending = any_pending or r.count > 0
            print(f"{r.dlq:<{width}}  {r.count:>8}  {r.label}{flag}")

    if any_pending:
        print("\nRun `replay <queue>` to retry, or `peek <queue>` to inspect first.")


async def cmd_peek(connection: aio_pika.RobustConnection, queue: str, n: int) -> None:
    dlq_name = f"{queue}.dlq"
    channel = await connection.channel()
    try:
        try:
            dlq = await channel.declare_queue(dlq_name, durable=True, passive=True)
        except aio_pika.exceptions.ChannelClosed:
            print(f"No such DLQ: {dlq_name} (nothing has dead-lettered from '{queue}' yet)")
            return

        shown = 0
        for _ in range(n):
            message = await dlq.get(no_ack=False, fail=False)
            if message is None:
                break
            shown += 1
            _print_message(shown, message)
            # Peek only: put it straight back so `peek` never drains the DLQ.
            await message.nack(requeue=True)

        if shown == 0:
            print(f"{dlq_name} is empty.")
    finally:
        if not channel.is_closed:
            await channel.close()


def _print_message(index: int, message: aio_pika.IncomingMessage) -> None:
    try:
        body = json.loads(message.body.decode("utf-8"))
        body_preview = json.dumps(body, ensure_ascii=False)[:300]
    except (UnicodeDecodeError, json.JSONDecodeError):
        body_preview = repr(message.body[:200])

    headers = message.headers or {}
    death = headers.get("x-death", [{}])
    reason = death[0].get("reason") if death else "unknown"
    original_routing_key = death[0].get("routing-keys", ["?"])[0] if death else "?"
    print(
        f"\n--- message {index} ---\n"
        f"  originally routed as : {original_routing_key}\n"
        f"  dead-letter reason   : {reason}\n"
        f"  body                 : {body_preview}"
    )


async def cmd_replay(connection: aio_pika.RobustConnection, queue: str, n: int | None) -> None:
    dlq_name = f"{queue}.dlq"
    channel = await connection.channel()
    try:
        try:
            dlq = await channel.declare_queue(dlq_name, durable=True, passive=True)
        except aio_pika.exceptions.ChannelClosed:
            print(f"No such DLQ: {dlq_name} (nothing has dead-lettered from '{queue}' yet)")
            return

        total = dlq.declaration_result.message_count
        limit = total if n is None else min(n, total)
        if limit == 0:
            print(f"{dlq_name} is empty - nothing to replay.")
            return

        replayed, failed = 0, 0
        for _ in range(limit):
            message = await dlq.get(no_ack=False, fail=False)
            if message is None:
                break
            try:
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=message.body,
                        headers=message.headers,
                        content_type=message.content_type,
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=queue,
                )
            except Exception as e:
                # Don't lose the message if the re-publish itself fails - put
                # it back in the DLQ rather than ack-ing it into the void.
                print(f"  ! failed to replay one message, leaving it in the DLQ: {e}")
                await message.nack(requeue=True)
                failed += 1
                continue
            await message.ack()
            replayed += 1

        print(f"Replayed {replayed} message(s) from {dlq_name} back onto '{queue}'"
              + (f", {failed} left in place after a publish error" if failed else "") + ".")
    finally:
        if not channel.is_closed:
            await channel.close()


async def cmd_purge(connection: aio_pika.RobustConnection, queue: str) -> None:
    dlq_name = f"{queue}.dlq"
    channel = await connection.channel()
    try:
        try:
            dlq = await channel.declare_queue(dlq_name, durable=True, passive=True)
        except aio_pika.exceptions.ChannelClosed:
            print(f"No such DLQ: {dlq_name} (nothing to purge)")
            return
        result = await dlq.purge()
        print(f"Purged {dlq_name} ({getattr(result, 'message_count', '?')} message(s) discarded permanently).")
    finally:
        if not channel.is_closed:
            await channel.close()


async def cmd_watch(url: str, interval: float) -> None:
    print(f"Watching {[q for _, q in KNOWN_QUEUES]} every {interval:.0f}s. Ctrl+C to stop.")
    while True:
        try:
            connection = await aio_pika.connect_robust(url)
            async with connection:
                for label, queue in KNOWN_QUEUES:
                    count = await _dlq_count(connection, f"{queue}.dlq")
                    if count:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⚠️  "
                              f"{queue}.dlq has {count} pending message(s) - {label}")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] watch: could not reach RabbitMQ: {e}")
        await asyncio.sleep(interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=None, help="AMQP URL (overrides RABBITMQ_* env vars)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Show pending message count for each DLQ")
    p_status.add_argument("-q", "--queue", default=None, help="Only show this queue's DLQ")

    p_peek = sub.add_parser("peek", help="Non-destructively inspect messages in a DLQ")
    p_peek.add_argument("queue", help="Live queue name, e.g. notification_events")
    p_peek.add_argument("-n", type=int, default=5, help="Max messages to show (default 5)")

    p_replay = sub.add_parser("replay", help="Move messages from a DLQ back onto its live queue")
    p_replay.add_argument("queue", help="Live queue name, e.g. notification_events")
    group = p_replay.add_mutually_exclusive_group(required=True)
    group.add_argument("-n", type=int, default=None, help="Replay at most N messages")
    group.add_argument("--all", action="store_true", help="Replay every message currently in the DLQ")

    p_purge = sub.add_parser("purge", help="Permanently discard every message in a DLQ")
    p_purge.add_argument("queue", help="Live queue name, e.g. notification_events")
    p_purge.add_argument("--yes", action="store_true", required=True, help="Required to confirm the purge")

    p_watch = sub.add_parser("watch", help="Poll all DLQ depths and print a warning when any is non-empty")
    p_watch.add_argument("--interval", type=float, default=60.0, help="Seconds between checks (default 60)")

    return parser


async def main_async(args: argparse.Namespace) -> int:
    url = resolve_rabbitmq_url(args.url)

    if args.command == "watch":
        await cmd_watch(url, args.interval)
        return 0

    connection = await aio_pika.connect_robust(url)
    try:
        if args.command == "status":
            await cmd_status(connection, args.queue)
        elif args.command == "peek":
            await cmd_peek(connection, args.queue, args.n)
        elif args.command == "replay":
            await cmd_replay(connection, args.queue, None if args.all else args.n)
        elif args.command == "purge":
            await cmd_purge(connection, args.queue)
    finally:
        await connection.close()
    return 0


def main() -> None:
    args = build_parser().parse_args()
    try:
        sys.exit(asyncio.run(main_async(args)))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
