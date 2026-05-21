#!/usr/bin/env python3
"""
Automated Rotating Proxy Manager for Camoufox
Manages proxy rotation to prevent IP bans during web scraping operations
"""

import time
import random
import logging
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import threading
from collections import deque

logger = logging.getLogger(__name__)

class ProxyType(Enum):
    """Types of proxies supported"""
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"

class ProxyStatus(Enum):
    """Proxy health status"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BANNED = "banned"
    FAILED = "failed"

@dataclass
class Proxy:
    """Proxy configuration and metadata"""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: ProxyType = ProxyType.HTTP
    status: ProxyStatus = ProxyStatus.UNKNOWN
    response_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_used: float = 0.0
    ban_until: float = 0.0
    
    @property
    def url(self) -> str:
        """Get proxy URL for requests library"""
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"
    
    @property
    def is_banned(self) -> bool:
        """Check if proxy is currently banned"""
        return time.time() < self.ban_until
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Neutral rating for untested proxies
        return self.success_count / total

class RotatingProxyManager:
    """
    Manages a pool of rotating proxies to prevent IP bans
    Features automatic health checking, ban detection, and intelligent rotation
    """
    
    def __init__(self, 
                 proxy_list: List[Dict],
                 health_check_url: str = "http://httpbin.org/ip",
                 health_check_interval: int = 300,  # 5 minutes
                 ban_duration: int = 3600,  # 1 hour
                 max_failures_before_ban: int = 3):
        """
        Initialize the proxy manager
        
        Args:
            proxy_list: List of proxy configuration dictionaries
            health_check_url: URL to use for health checks
            health_check_interval: Seconds between health checks
            ban_duration: Seconds to ban a proxy after detection
            max_failures_before_ban: Number of failures before temporary ban
        """
        self.proxies: List[Proxy] = []
        self.health_check_url = health_check_url
        self.health_check_interval = health_check_interval
        self.ban_duration = ban_duration
        self.max_failures_before_ban = max_failures_before_ban
        
        # Convert dictionary proxies to Proxy objects
        for proxy_dict in proxy_list:
            proxy = Proxy(
                host=proxy_dict['host'],
                port=proxy_dict['port'],
                username=proxy_dict.get('username'),
                password=proxy_dict.get('password'),
                proxy_type=ProxyType(proxy_dict.get('type', 'http').lower())
            )
            self.proxies.append(proxy)
        
        # Initialize tracking
        self.last_health_check = 0
        self.health_check_thread = None
        self.is_monitoring = False
        self.lock = threading.Lock()
        
        logger.info(f"RotatingProxyManager initialized with {len(self.proxies)} proxies")
        
        # Perform initial health check
        self._perform_health_checks()
    
    def _perform_health_checks(self):
        """Perform health checks on all proxies"""
        logger.info("Starting proxy health checks...")
        
        for proxy in self.proxies:
            if proxy.is_banned:
                continue
                
            start_time = time.time()
            try:
                proxies_dict = {
                    'http': proxy.url,
                    'https': proxy.url
                }
                
                response = requests.get(
                    self.health_check_url,
                    proxies=proxies_dict,
                    timeout=10
                )
                
                response_time = time.time() - start_time
                proxy.response_time = response_time
                
                if response.status_code == 200:
                    proxy.status = ProxyStatus.HEALTHY
                    proxy.success_count += 1
                    logger.debug(f"Proxy {proxy.host}:{proxy.port} healthy ({response_time:.2f}s)")
                else:
                    proxy.status = ProxyStatus.DEGRADED
                    proxy.failure_count += 1
                    logger.warning(f"Proxy {proxy.host}:{proxy.port} returned status {response.status_code}")
                    
            except Exception as e:
                proxy.failure_count += 1
                proxy.status = ProxyStatus.FAILED
                logger.debug(f"Proxy {proxy.host}:{proxy.port} failed: {str(e)}")
            
            # Check if we should ban this proxy
            if proxy.failure_count >= self.max_failures_before_ban:
                self._ban_proxy(proxy, "Too many consecutive failures")
        
        self.last_health_check = time.time()
        logger.info("Proxy health checks completed")
    
    def _ban_proxy(self, proxy: Proxy, reason: str):
        """Temporarily ban a proxy"""
        proxy.status = ProxyStatus.BANNED
        proxy.ban_until = time.time() + self.ban_duration
        logger.warning(f"Proxy {proxy.host}:{proxy.port} banned for {self.ban_duration}s: {reason}")
    
    def _unban_expired_proxies(self):
        """Unban proxies whose ban period has expired"""
        current_time = time.time()
        for proxy in self.proxies:
            if proxy.status == ProxyStatus.BANNED and current_time >= proxy.ban_until:
                proxy.status = ProxyStatus.UNKNOWN
                proxy.ban_until = 0
                logger.info(f"Proxy {proxy.host}:{proxy.port} unbanned")
    
    def get_best_proxy(self) -> Optional[Proxy]:
        """
        Get the best available proxy based on health and performance
        
        Returns:
            Best available Proxy object or None if no healthy proxies available
        """
        with self.lock:
            # Unban expired proxies
            self._unban_expired_proxies()
            
            # Perform health check if needed
            if time.time() - self.last_health_check > self.health_check_interval:
                # Run health check in background to avoid blocking
                if not self.is_monitoring:
                    self.is_monitoring = True
                    threading.Thread(target=self._perform_health_checks, daemon=True).start()
            
            # Filter available proxies (not banned and not failed)
            available_proxies = [
                p for p in self.proxies 
                if not p.is_banned and p.status != ProxyStatus.FAILED
            ]
            
            if not available_proxies:
                logger.warning("No healthy proxies available")
                return None
            
            # Sort by success rate (descending) and response time (ascending)
            available_proxies.sort(
                key=lambda p: (-p.success_rate, p.response_time)
            )
            
            # Return the best proxy
            best_proxy = available_proxies[0]
            best_proxy.last_used = time.time()
            
            logger.debug(f"Selected proxy: {best_proxy.host}:{best_proxy.port}")
            return best_proxy
    
    def get_random_proxy(self) -> Optional[Proxy]:
        """
        Get a random healthy proxy (useful for distributing load)
        
        Returns:
            Random Proxy object or None if no healthy proxies available
        """
        with self.lock:
            self._unban_expired_proxies()
            
            healthy_proxies = [
                p for p in self.proxies 
                if not p.is_banned and p.status == ProxyStatus.HEALTHY
            ]
            
            if not healthy_proxies:
                return self.get_best_proxy()  # Fallback to best available
            
            proxy = random.choice(healthy_proxies)
            proxy.last_used = time.time()
            return proxy
    
    def report_success(self, proxy: Proxy):
        """Report a successful request through a proxy"""
        with self.lock:
            proxy.success_count += 1
            # Reduce failure count on success (recovery)
            if proxy.failure_count > 0:
                proxy.failure_count = max(0, proxy.failure_count - 1)
    
    def report_failure(self, proxy: Proxy, is_ban_suspected: bool = False):
        """Report a failed request through a proxy"""
        with self.lock:
            proxy.failure_count += 1
            
            if is_ban_suspected:
                self._ban_proxy(proxy, "Suspected IP ban detected")
            elif proxy.failure_count >= self.max_failures_before_ban:
                self._ban_proxy(proxy, "Failure threshold reached")
    
    def get_proxy_stats(self) -> Dict:
        """Get statistics about the proxy pool"""
        with self.lock:
            total = len(self.proxies)
            healthy = len([p for p in self.proxies if p.status == ProxyStatus.HEALTHY])
            banned = len([p for p in self.proxies if p.status == ProxyStatus.BANNED])
            failed = len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
            degraded = len([p for p in self.proxies if p.status == ProxyStatus.DEGRADED])
            unknown = len([p for p in self.proxies if p.status == ProxyStatus.UNKNOWN])
            
            return {
                'total_proxies': total,
                'healthy': healthy,
                'banned': banned,
                'failed': failed,
                'degraded': degraded,
                'unknown': unknown,
                'availability_percentage': (healthy / total * 100) if total > 0 else 0
            }

# Example usage and testing
if __name__ == "__main__":
    # Example proxy list (in practice, load from secure config/secrets)
    proxy_list = [
        {
            'host': 'proxy1.example.com',
            'port': 8080,
            'username': 'user1',
            'password': 'pass1',
            'type': 'http'
        },
        {
            'host': 'proxy2.example.com',
            'port': 3128,
            'username': 'user2',
            'password': 'pass2',
            'type': 'http'
        },
        {
            'host': 'proxy3.example.com',
            'port': 8080,
            'type': 'http'
            # No auth for this one
        }
    ]
    
    # Initialize proxy manager
    proxy_manager = RotatingProxyManager(
        proxy_list=proxy_list,
        health_check_url="http://httpbin.org/ip",
        health_check_interval=60,  # Check every minute for demo
        ban_duration=300,  # Ban for 5 minutes
        max_failures_before_ban=2
    )
    
    # Test getting a proxy
    proxy = proxy_manager.get_best_proxy()
    if proxy:
        print(f"Selected proxy: {proxy.host}:{proxy.port}")
        print(f"Proxy URL: {proxy.url}")
        
        # Simulate a successful request
        proxy_manager.report_success(proxy)
        print("Reported success")
        
        # Show stats
        stats = proxy_manager.get_proxy_stats()
        print(f"Proxy stats: {stats}")
    else:
        print("No healthy proxies available")