#!/usr/bin/env python3
"""
Optimize exchange API rate limiting handling for improved data throughput
Implements intelligent rate limiting strategies for exchange APIs to maximize
data throughput while respecting rate limits and avoiding bans
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
import random

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Different rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    ADAPTIVE = "adaptive"

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_second: float = 10.0
    burst_size: int = 20
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    adaptive_factor: float = 0.1  # How quickly to adapt to rate limit responses
    jitter_factor: float = 0.1    # Random jitter to prevent thundering herd
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier
    max_backoff: float = 60.0     # Maximum backoff time in seconds

@dataclass
class RateLimitState:
    """Current state of rate limiter"""
    tokens: float = field(default=20.0)
    last_update: float = field(default_factory=time.time)
    requests_made: int = 0
    window_start: float = field(default_factory=time.time)
    consecutive_429s: int = 0
    backoff_until: float = 0.0
    adaptive_rate: float = field(default=10.0)

class ExchangeAPIRateOptimizer:
    """
    Optimizes exchange API rate limiting for improved data throughput
    Implements multiple rate limiting algorithms with adaptive capabilities
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize the rate optimizer
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config or RateLimitConfig()
        self.state = RateLimitState(
            tokens=float(self.config.burst_size),
            adaptive_rate=self.config.requests_per_second
        )
        self.request_times: deque = deque(maxlen=1000)
        self._lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None
        
        logger.info(f"ExchangeAPIRateOptimizer initialized with {self.config}")
    
    async def acquire(self, endpoint: str = "default") -> bool:
        """
        Acquire permission to make a request
        
        Args:
            endpoint: API endpoint identifier
            
        Returns:
            True if request can proceed, False if should wait
        """
        # Handle backoff period
        if time.time() < self.state.backoff_until:
            wait_time = self.state.backoff_until - time.time()
            logger.debug(f"In backoff period, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        # Apply rate limiting strategy
        if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._token_bucket_acquire()
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._sliding_window_acquire()
        elif self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._fixed_window_acquire()
        elif self.config.strategy == RateLimitStrategy.ADAPTIVE:
            return await self._adaptive_acquire()
        else:
            # Default to token bucket
            return await self._token_bucket_acquire()
    
    async def _token_bucket_acquire(self) -> bool:
        """Token bucket algorithm"""
        now = time.time()
        
        # Add tokens based on time passed
        time_passed = now - self.state.last_update
        new_tokens = time_passed * self.state.adaptive_rate
        self.state.tokens = min(
            self.state.tokens + new_tokens,
            float(self.config.burst_size)
        )
        self.state.last_update = now
        
        # Check if we have enough tokens
        if self.state.tokens >= 1.0:
            # Consume token with jitter
            jitter = random.uniform(-self.config.jitter_factor, self.config.jitter_factor)
            actual_cost = max(0.1, 1.0 + jitter)
            self.state.tokens -= actual_cost
            self.state.requests_made += 1
            self.request_times.append(now)
            return True
        else:
            # Not enough tokens, calculate wait time
            tokens_needed = 1.0 - self.state.tokens
            wait_time = tokens_needed / self.state.adaptive_rate
            logger.debug(f"Token bucket empty, waiting {wait_time:.3f}s")
            await asyncio.sleep(wait_time)
            return await self._token_bucket_acquire()  # Retry after wait
    
    async def _sliding_window_acquire(self) -> bool:
        """Sliding window algorithm"""
        now = time.time()
        window_size = 1.0  # 1 second window
        
        # Remove old requests outside window
        while self.request_times and self.request_times[0] <= now - window_size:
            self.request_times.popleft()
        
        # Check if we're under the limit
        if len(self.request_times) < self.config.requests_per_second:
            self.request_times.append(now)
            self.state.requests_made += 1
            return True
        else:
            # Calculate wait time until oldest request expires
            oldest_request = self.request_times[0]
            wait_time = (oldest_request + window_size) - now
            if wait_time > 0:
                logger.debug(f"Sliding window full, waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)
            return await self._sliding_window_acquire()
    
    async def _fixed_window_acquire(self) -> bool:
        """Fixed window algorithm"""
        now = time.time()
        
        # Reset window if needed
        if now - self.state.window_start >= 1.0:
            self.state.requests_made = 0
            self.state.window_start = now
        
        # Check if we can make request
        if self.state.requests_made < self.config.requests_per_second:
            self.state.requests_made += 1
            self.request_times.append(now)
            return True
        else:
            # Wait for window to reset
            wait_time = 1.0 - (now - self.state.window_start)
            if wait_time > 0:
                logger.debug(f"Fixed window exhausted, waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)
            return await self._fixed_window_acquire()
    
    async def _adaptive_acquire(self) -> bool:
        """Adaptive algorithm that learns from responses"""
        # Start with token bucket approach
        result = await self._token_bucket_acquire()
        
        # Adaptive rate adjustment happens in record_response
        return result
    
    def record_response(self, status_code: int, headers: Optional[Dict[str, str]] = None):
        """
        Record API response to adapt rate limiting behavior
        
        Args:
            status_code: HTTP status code from response
            headers: Response headers (may contain rate limit info)
        """
        # Handle rate limit responses (429 Too Many Requests)
        if status_code == 429:
            self.state.consecutive_429s += 1
            
            # Increase backoff exponentially
            backoff_time = min(
                self.config.backoff_multiplier ** self.state.consecutive_429s,
                self.config.max_backoff
            )
            # Add jitter to prevent synchronized retries
            jitter = random.uniform(0, backoff_time * 0.1)
            self.state.backoff_until = time.time() + backoff_time + jitter
            
            # Reduce adaptive rate
            self.state.adaptive_rate *= (1.0 - self.config.adaptive_factor)
            self.state.adaptive_rate = max(
                self.state.adaptive_rate,
                self.config.requests_per_second * 0.1  # Don't go below 10% of configured rate
            )
            
            logger.warning(
                f"Rate limit hit (429), backing off for {backoff_time:.2f}s, "
                f"adaptive rate reduced to {self.state.adaptive_rate:.2f} req/s"
            )
        
        # Handle successful responses - gradually increase rate
        elif 200 <= status_code < 300:
            if self.state.consecutive_429s > 0:
                self.state.consecutive_429s = max(0, self.state.consecutive_429s - 1)
            
            # Gradually increase rate after successful requests
            if self.state.adaptive_rate < self.config.requests_per_second:
                increase = self.config.adaptive_factor * 0.5  # Slower increase than decrease
                self.state.adaptive_rate = min(
                    self.state.adaptive_rate + increase,
                    self.config.requests_per_second
                )
                
                # Reduce backoff if we're doing well
                if self.state.backoff_until > time.time():
                    # Move backoff time closer if we're getting success
                    time_until_backoff = self.state.backoff_until - time.time()
                    if time_until_backoff > 1.0:  # Only if more than 1 second left
                        self.state.backoff_until = time.time() + max(1.0, time_until_backoff * 0.8)
        
        # Parse rate limit headers if available
        if headers:
            self._parse_rate_limit_headers(headers)
    
    def _parse_rate_limit_headers(self, headers: Dict[str, str]):
        """Parse rate limit information from response headers"""
        # Common rate limit header formats
        limit_headers = {
            'X-RateLimit-Limit': 'limit',
            'X-RateLimit-Remaining': 'remaining',
            'X-RateLimit-Reset': 'reset',
            'RateLimit-Limit': 'limit',
            'RateLimit-Remaining': 'remaining',
            'RateLimit-Reset': 'reset'
        }
        
        for header, key in limit_headers.items():
            if header in headers:
                try:
                    value = int(headers[header])
                    if key == 'limit':
                        # Update our configured limit if provided by API
                        self.config.requests_per_second = value
                    elif key == 'remaining':
                        # Could use this for more precise token bucket adjustment
                        pass
                    elif key == 'reset':
                        # Reset timestamp - could synchronize our window
                        reset_time = value
                        now = time.time()
                        if reset_time > now:
                            # Header provides epoch timestamp
                            pass
                except ValueError:
                    logger.debug(f"Could not parse rate limit header {header}: {headers[header]}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics"""
        now = time.time()
        window_requests = sum(1 for t in self.request_times if t > now - 1.0)
        
        return {
            'strategy': self.config.strategy.value,
            'requests_per_second': self.config.requests_per_second,
            'adaptive_rate': self.state.adaptive_rate,
            'burst_size': self.config.burst_size,
            'tokens_available': self.state.tokens,
            'requests_last_second': window_requests,
            'total_requests': self.state.requests_made,
            'consecutive_429s': self.state.consecutive_429s,
            'in_backoff': time.time() < self.state.backoff_until,
            'backoff_remaining': max(0, self.state.backoff_until - time.time())
        }
    
    def reset(self):
        """Reset the rate limiter to initial state"""
        self.state = RateLimitState(
            tokens=float(self.config.burst_size),
            adaptive_rate=self.config.requests_per_second
        )
        self.request_times.clear()
        logger.info("Rate limiter reset")

# Global optimizer instances for different exchanges
_optimizers: Dict[str, ExchangeAPIRateOptimizer] = {}

def get_rate_optimizer(exchange: str = "default", 
                      config: Optional[RateLimitConfig] = None) -> ExchangeAPIRateOptimizer:
    """
    Get or create a rate optimizer for a specific exchange
    
    Args:
        exchange: Exchange identifier
        config: Configuration for the optimizer
        
    Returns:
        ExchangeAPIRateOptimizer instance
    """
    if exchange not in _optimizers:
        _optimizers[exchange] = ExchangeAPIRateOptimizer(config)
    return _optimizers[exchange]

def reset_all_optimizers():
    """Reset all rate optimizers"""
    global _optimizers
    for optimizer in _optimizers.values():
        optimizer.reset()
    logger.info("All rate optimizers reset")

# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_rate_limiter():
        """Test the rate limiter functionality"""
        print("Testing ExchangeAPIRateOptimizer...")
        
        # Create optimizer with modest rate limit
        optimizer = ExchangeAPIRateOptimizer(
            RateLimitConfig(
                requests_per_second=5.0,
                burst_size=10,
                strategy=RateLimitStrategy.TOKEN_BUCKET
            )
        )
        
        # Test acquiring permissions
        print("\\nTesting token acquisition:")
        start_time = time.time()
        acquired_count = 0
        
        for i in range(20):
            if await optimizer.acquire():
                acquired_count += 1
                print(f"  Request {i+1}: ACQUIRED")
            else:
                print(f"  Request {i+1}: DENIED")
            
            # Small delay to see the effect
            await asyncio.sleep(0.1)
        
        elapsed = time.time() - start_time
        print(f"\\nAcquired {acquired_count}/20 requests in {elapsed:.2f}s")
        print(f"Effective rate: {acquired_count/elapsed:.2f} req/s")
        
        # Show stats
        stats = optimizer.get_stats()
        print(f"\\nStats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Simulate rate limit responses
        print("\\nSimulating rate limit responses:")
        for i in range(5):
            optimizer.record_response(429, {
                'X-RateLimit-Limit': '5',
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int(time.time()) + 10)
            })
            print(f"  After 429 response {i+1}:")
            stats = optimizer.get_stats()
            print(f"    Adaptive rate: {stats['adaptive_rate']:.2f}")
            print(f"    Backoff remaining: {stats['backoff_remaining']:.2f}s")
        
        # Simulate successful responses
        print("\\nSimulating successful responses:")
        for i in range(5):
            optimizer.record_response(200, {
                'X-RateLimit-Limit': '5',
                'X-RateLimit-Remaining': str(5-i-1),
                'X-RateLimit-Reset': str(int(time.time()) + 10)
            })
            print(f"  After 200 response {i+1}:")
            stats = optimizer.get_stats()
            print(f"    Adaptive rate: {stats['adaptive_rate']:.2f}")
            print(f"    Backoff remaining: {stats['backoff_remaining']:.2f}s")
    
    # Run the test
    asyncio.run(test_rate_limiter())
    print("\\nTest completed successfully!")
