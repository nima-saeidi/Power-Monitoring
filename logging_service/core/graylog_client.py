import httpx
from typing import Dict, Any, Optional
from core.config import settings


class GraylogClient:
    def __init__(self):
        self.base_url = settings.GRAYLOG_API_URL.rstrip('/')
        self.auth = (settings.GRAYLOG_USERNAME, settings.GRAYLOG_PASSWORD)
        self.headers = {"Accept": "application/json"}

    async def search_relative(
            self,
            query: str = "*",
            range_seconds: int = 86400,
            limit: int = 100,
            offset: int = 0
    ) -> Dict[str, Any]:
        """جستجوی لاگ‌ها در بازه زمانی گذشته (Relative Search)"""
        url = f"{self.base_url}/views/search/messages"

        # استفاده از اندپوینت استاندارد Graylog search relative
        legacy_url = f"{self.base_url}/search/universal/relative"
        params = {
            "query": query,
            "range": range_seconds,
            "limit": limit,
            "offset": offset,
            "sort": "timestamp:desc"
        }

        async with httpx.AsyncClient(auth=self.auth, headers=self.headers, timeout=10.0) as client:
            response = await client.get(legacy_url, params=params)
            response.raise_for_status()
            return response.json()


graylog_client = GraylogClient()
