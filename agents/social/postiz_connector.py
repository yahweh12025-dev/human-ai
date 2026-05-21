"""
Postiz Content Bridge
Handles integration between the trading system and Postiz social media platform.
Supports both cloud-hosted and self-hosted Postiz instances.
"""

import json
import os
import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class PostizConnector:
    """
    Bridge to Postiz social media management platform.
    Handles publishing content, managing accounts, and retrieving analytics.
    Supports self-hosted Postiz instances via POSTIZ_API_URL environment variable.
    """

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Postiz connector.
        Falls back to environment variables if args are not provided.

        Args:
            api_url: Base URL for Postiz API (or set POSTIZ_API_URL env var).
                     For self-hosted: typically http://localhost:5000 or your domain.
            api_key: API key for authentication (or set POSTIZ_API_KEY env var).
        """
        self.api_url = (api_url or os.environ.get("POSTIZ_API_URL", "http://localhost:5000")).rstrip('/')
        self.api_key = api_key or os.environ.get("POSTIZ_API_KEY", "")
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # Self-hosted instance settings
        self.is_self_hosted = not self.api_url.startswith("https://api.postiz.com")
        self.request_timeout = int(os.environ.get("POSTIZ_TIMEOUT", "30"))
        self.max_retries = int(os.environ.get("POSTIZ_MAX_RETRIES", "3"))
        self.retry_delay = float(os.environ.get("POSTIZ_RETRY_DELAY", "2.0"))

        logger.info(
            f"PostizConnector initialized | URL: {self.api_url} | "
            f"Self-hosted: {self.is_self_hosted}"
        )
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Make HTTP request to Postiz API with retry support.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            data: Data to send (for POST/PUT)

        Returns:
            Response data as dictionary
        """
        url = f"{self.api_url}{endpoint}"
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if method.upper() == 'GET':
                    response = requests.get(
                        url, headers=self.headers, params=data,
                        timeout=self.request_timeout
                    )
                elif method.upper() == 'POST':
                    response = requests.post(
                        url, headers=self.headers, json=data,
                        timeout=self.request_timeout
                    )
                elif method.upper() == 'PUT':
                    response = requests.put(
                        url, headers=self.headers, json=data,
                        timeout=self.request_timeout
                    )
                elif method.upper() == 'DELETE':
                    response = requests.delete(
                        url, headers=self.headers,
                        timeout=self.request_timeout
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json() if response.content else {}

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait = self.retry_delay * (attempt + 1)
                    logger.warning(
                        f"Postiz connection error (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {wait}s: {e}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"Postiz API connection failed after {self.max_retries} attempts: {e}")

            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    logger.warning(f"Postiz API timeout (attempt {attempt + 1}), retrying...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Postiz API timeout after {self.max_retries} attempts")

            except requests.exceptions.RequestException as e:
                logger.error(f"Postiz API request failed: {e}")
                raise

        raise last_exception or requests.exceptions.ConnectionError("Max retries exceeded")
    
    def publish_content(self, content: str, media_ids: Optional[List[str]] = None, 
                       scheduled_time: Optional[datetime] = None,
                       platforms: Optional[List[str]] = None) -> Dict:
        """
        Publish content to social media platforms via Postiz
        
        Args:
            content: Text content to publish
            media_ids: List of media IDs to attach
            scheduled_time: When to publish (if None, publish immediately)
            platforms: List of platform identifiers (if None, use all connected)
            
        Returns:
            Response from Postiz API
        """
        payload = {
            'content': content,
        }
        
        if media_ids:
            payload['media_ids'] = media_ids
            
        if scheduled_time:
            payload['scheduled_at'] = scheduled_time.isoformat()
            
        if platforms:
            payload['platforms'] = platforms
        
        logger.info(f"Publishing content to Postiz: {content[:50]}...")
        return self._make_request('POST', '/posts', payload)
    
    def get_accounts(self) -> List[Dict]:
        """
        Retrieve connected social media accounts
        
        Returns:
            List of account dictionaries
        """
        logger.info("Fetching connected accounts from Postiz")
        return self._make_request('GET', '/accounts')
    
    def get_analytics(self, post_id: str) -> Dict:
        """
        Get analytics for a specific post
        
        Args:
            post_id: ID of the post to analyze
            
        Returns:
            Analytics data
        """
        logger.info(f"Fetching analytics for post {post_id}")
        return self._make_request('GET', f'/posts/{post_id}/analytics')
    
    def upload_media(self, file_path: str, file_type: str = 'image') -> Dict:
        """
        Upload media file to Postiz (supports self-hosted instances).

        Args:
            file_path: Path to media file
            file_type: Type of media (image, video, gif)

        Returns:
            Upload response containing media ID
        """
        logger.info(f"Uploading media file: {file_path} (type: {file_type})")

        url = f"{self.api_url}/media/upload"

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.split('/')[-1], f)}
                upload_headers = {
                    'Authorization': f'Bearer {self.api_key}',
                }
                response = requests.post(
                    url,
                    headers=upload_headers,
                    files=files,
                    data={'type': file_type},
                    timeout=self.request_timeout * 2,  # Double timeout for uploads
                )
            response.raise_for_status()
            result = response.json() if response.content else {}
            logger.info(f"Media uploaded successfully: {result.get('id', 'unknown')}")
            return result

        except FileNotFoundError:
            logger.error(f"Media file not found: {file_path}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Media upload failed: {e}")
            raise
    
    def schedule_content_calendar(self, content_list: List[Dict]) -> Dict:
        """
        Schedule multiple content items for future publishing
        
        Args:
            content_list: List of content dictionaries with 'content', 'scheduled_time', etc.
            
        Returns:
            Batch scheduling response
        """
        logger.info(f"Scheduling {len(content_list)} content items")
        
        payload = {
            'posts': content_list
        }
        
        return self._make_request('POST', '/posts/batch', payload)

    def get_post_status(self, post_id: str) -> Dict:
        """
        Get the current status of a post (useful for tracking scheduled posts).

        Args:
            post_id: ID of the post to check

        Returns:
            Post status data
        """
        logger.info(f"Checking status for post {post_id}")
        return self._make_request('GET', f'/posts/{post_id}')

    def get_scheduled_posts(self) -> List[Dict]:
        """
        Retrieve all currently scheduled (pending) posts.

        Returns:
            List of scheduled post dictionaries
        """
        logger.info("Fetching scheduled posts from Postiz")
        return self._make_request('GET', '/posts/scheduled')

    def delete_post(self, post_id: str) -> Dict:
        """
        Delete a post (removes scheduled or published post).

        Args:
            post_id: ID of the post to delete

        Returns:
            Deletion confirmation
        """
        logger.info(f"Deleting post {post_id}")
        return self._make_request('DELETE', f'/posts/{post_id}')

    def health_check(self) -> bool:
        """
        Check if the Postiz instance is reachable and healthy.

        Returns:
            True if the instance is responsive.
        """
        try:
            response = requests.get(
                f"{self.api_url}/health",
                headers=self.headers,
                timeout=5,
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


# Example usage
if __name__ == "__main__":
    # Initialize from environment variables (recommended for self-hosted)
    # Set POSTIZ_API_URL and POSTIZ_API_KEY in your .env file
    connector = PostizConnector()

    # Health check
    if connector.health_check():
        print(f"Postiz instance at {connector.api_url} is healthy")
    else:
        print(f"WARNING: Postiz instance at {connector.api_url} is not reachable")

    # Example: Publish a trading update
    try:
        result = connector.publish_content(
            content="BTC showing strong volume signals. #Bitcoin #Trading #Crypto",
            platforms=["twitter", "instagram"]
        )
        print(f"Published post: {result}")
    except Exception as e:
        print(f"Failed to publish: {e}")