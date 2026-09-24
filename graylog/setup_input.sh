#!/bin/sh
set -e

GRAYLOG_URL="http://graylog:9000"
USER="${GRAYLOG_API_USER:-admin}"
PASS="${GRAYLOG_API_PASSWORD:-admin}"

echo "Waiting for Graylog API to become reachable..."
until curl -s -o /dev/null -m 5 -u "$USER:$PASS" "$GRAYLOG_URL/api/system/lbstatus"; do
  sleep 5
done
echo "Graylog API is up."

EXISTING=$(curl -s -m 10 -u "$USER:$PASS" -H "Accept: application/json" -H "X-Requested-By: init" \
  "$GRAYLOG_URL/api/system/inputs" | grep -c "GELFUDPInput" || true)

if [ "$EXISTING" -gt 0 ]; then
  echo "GELF UDP input already exists, skipping creation."
  exit 0
fi

echo "Creating GELF UDP input on port 12201..."
curl -s -m 15 -u "$USER:$PASS" -H "Accept: application/json" -H "Content-Type: application/json" \
  -H "X-Requested-By: init" -X POST "$GRAYLOG_URL/api/system/inputs" \
  -d '{"title":"GELF UDP Input","type":"org.graylog2.inputs.gelf.udp.GELFUDPInput","configuration":{"bind_address":"0.0.0.0","port":12201,"recv_buffer_size":262144,"decompress_size_limit":8388608},"global":true}'

echo "GELF UDP input created."
