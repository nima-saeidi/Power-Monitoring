import httpx
from typing import Dict, Any
from core.config import settings


class GraylogClient:
    def __init__(self):
        self.base_url = settings.GRAYLOG_API_URL.rstrip("/")
        self.auth = (settings.GRAYLOG_USERNAME, settings.GRAYLOG_PASSWORD)
        self.headers = {
            "Accept": "application/json",
            "X-Requested-By": "logging-service"
        }

    async def search_relative(
            self,
            query: str = "*",
            range_seconds: int = 86400,
            limit: int = 100,
            offset: int = 0
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/views/search/sync"

        legacy_url = f"{self.base_url}/search/universal/relative"
        params = {
            "query": query,
            "range": range_seconds,
            "limit": limit,
            "offset": offset,
            "sort": "timestamp:desc"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                legacy_url,
                params=params,
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()


graylog_client = GraylogClient()
