"""
Cloudflare Bypass Utility for Browser Agents
Provides Cloudflare cookie retrieval and injection for browser automation.
"""
import requests
import json
import time
from typing import Dict, Optional, Tuple


class CloudflareBypassManager:
    """Manages Cloudflare cookie retrieval and injection for browser agents"""

    def __init__(self, bypass_service_url: str = "http://127.0.0.1:8000"):
        self.bypass_service_url = bypass_service_url.rstrip('/')
        self._cookie_cache = {}
        self._cache_timeout = 300  # 5 minutes

    def get_cloudflare_cookies(self, url: str) -> Tuple[Dict[str, str], Optional[str]]:
        """
        Retrieve Cloudflare cookies for a given URL using the bypass service

        Returns:
            Tuple of (cookies_dict, user_agent)
        """
        # Check cache first
        cache_key = url
        now = time.time()
        if cache_key in self._cookie_cache:
            cached_data, timestamp = self._cookie_cache[cache_key]
            if now - timestamp < self._cache_timeout:
                return cached_data

        # Fetch fresh cookies
        try:
            resp = requests.get(
                f"{self.bypass_service_url}/cookies",
                params={"url": url},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            cookies = data.get("cookies", {})
            user_agent = data.get("user_agent")

            # Cache the result
            self._cookie_cache[cache_key] = ((cookies, user_agent), now)

            return cookies, user_agent
        except Exception as e:
            print(f"⚠️ Cloudflare bypass failed for {url}: {e}")
            # Return empty cookies to allow fallback to normal operation
            return {}, None

    def clear_cache(self):
        """Clear the cookie cache"""
        self._cookie_cache.clear()