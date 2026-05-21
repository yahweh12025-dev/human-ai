#!/usr/bin/env python3
"""
Implement real-time webhook system for external trading signal notifications
Provides a flexible webhook notification system for sending trading signals,
alerts, and updates to external services via HTTP webhooks
"""

import json
import logging
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hashlib
import hmac
from queue import Queue, Empty

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Types of trading notifications"""
    SIGNAL = "signal"
    ALERT = "alert"
    UPDATE = "update"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

class WebhookStatus(Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint"""
    url: str
    secret: Optional[str] = None  # For HMAC signature
    headers: Dict[str, str] = None
    timeout: float = 10.0
    retry_count: int = 3
    retry_backoff: float = 1.0
    enabled: bool = True
    rate_limit: float = 0.0  # Minimum seconds between requests (0 = no limit)

@dataclass
class Notification:
    """A trading notification to be sent via webhook"""
    id: str
    type: NotificationType
    title: str
    message: str
    data: Dict[str, Any] = None
    timestamp: float = None
    priority: int = 1  # 1=low, 2=medium, 3=high
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.data is None:
            self.data = {}

@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt"""
    notification_id: str
    webhook_url: str
    status: WebhookStatus
    attempt_count: int
    last_attempt: float
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None

class TradingWebhookNotifier:
    """
    Real-time webhook system for external trading signal notifications
    Manages delivery of trading notifications to external services via HTTP webhooks
    with retry mechanisms, rate limiting, and security features
    """
    
    def __init__(self):
        """Initialize the webhook notifier"""
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.notification_queue: Queue = Queue()
        self.delivery_history: List[WebhookDelivery] = []
        self._last_request_times: Dict[str, float] = {}
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        
        # Start the worker thread
        self._start_worker()
        
        logger.info("TradingWebhookNotifier initialized")
    
    def add_webhook(self, name: str, config: WebhookConfig):
        """
        Add a webhook endpoint
        
        Args:
            name: Identifier for the webhook
            config: Webhook configuration
        """
        with self._lock:
            self.webhooks[name] = config
            self._last_request_times[name] = 0.0
        logger.info(f"Added webhook '{name}' to {config.url}")
    
    def remove_webhook(self, name: str):
        """Remove a webhook endpoint"""
        with self._lock:
            if name in self.webhooks:
                del self.webhooks[name]
                del self._last_request_times[name]
                logger.info(f"Removed webhook '{name}'")
    
    def update_webhook(self, name: str, config: WebhookConfig):
        """Update an existing webhook configuration"""
        with self._lock:
            self.webhooks[name] = config
        logger.info(f"Updated webhook '{name}'")
    
    def send_notification(self, 
                         notification_type: NotificationType,
                         title: str,
                         message: str,
                         data: Optional[Dict[str, Any]] = None,
                         priority: int = 1,
                         webhook_names: Optional[List[str]] = None) -> str:
        """
        Send a trading notification
        
        Args:
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data payload
            priority: Notification priority (1-3)
            webhook_names: Specific webhooks to send to (None = all enabled)
            
        Returns:
            Notification ID
        """
        # Generate unique notification ID
        notification_id = hashlib.md5(
            f"{time.time()}{title}{message}".encode()
        ).hexdigest()[:12]
        
        notification = Notification(
            id=notification_id,
            type=notification_type,
            title=title,
            message=message,
            data=data or {},
            priority=priority
        )
        
        # Determine which webhooks to send to
        target_webhooks = webhook_names or [
            name for name, config in self.webhooks.items() 
            if config.enabled
        ]
        
        # Queue notification for each target webhook
        for webhook_name in target_webhooks:
            if webhook_name in self.webhooks:
                self.notification_queue.put((notification_id, webhook_name, notification))
                logger.debug(f"Queued notification {notification_id} for webhook {webhook_name}")
            else:
                logger.warning(f"Webhook '{webhook_name}' not found")
        
        logger.info(f"Sent notification {notification_id} ({notification_type.value}): {title}")
        return notification_id
    
    def send_signal(self, 
                   signal: str,
                   symbol: str,
                   price: float,
                   confidence: float,
                   strategy: str,
                   data: Optional[Dict[str, Any]] = None,
                   webhook_names: Optional[List[str]] = None) -> str:
        """
        Send a trading signal notification
        
        Args:
            signal: Signal type (BUY, SELL, HOLD)
            symbol: Trading symbol
            price: Current price
            confidence: Signal confidence (0-1)
            strategy: Strategy name
            data: Additional data
            webhook_names: Specific webhooks to notify
            
        Returns:
            Notification ID
        """
        signal_data = {
            'signal': signal,
            'symbol': symbol,
            'price': price,
            'confidence': confidence,
            'strategy': strategy,
            'timestamp': time.time()
        }
        if data:
            signal_data.update(data)
        
        return self.send_notification(
            NotificationType.SIGNAL,
            f"{signal} Signal: {symbol}",
            f"{signal} signal for {symbol} at ${price:.2f} "
            f"(confidence: {confidence:.2%}, strategy: {strategy})",
            signal_data,
            priority=3,  # High priority for signals
            webhook_names=webhook_names
        )
    
    def send_alert(self,
                  alert_type: str,
                  message: str,
                  severity: str = "medium",
                  data: Optional[Dict[str, Any]] = None,
                  webhook_names: Optional[List[str]] = None) -> str:
        """
        Send an alert notification
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (low, medium, high, critical)
            data: Additional data
            webhook_names: Specific webhooks to notify
            
        Returns:
            Notification ID
        """
        alert_data = {
            'alert_type': alert_type,
            'severity': severity,
            'timestamp': time.time()
        }
        if data:
            alert_data.update(data)
        
        priority_map = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 3
        }
        priority = priority_map.get(severity.lower(), 2)
        
        return self.send_notification(
            NotificationType.ALERT,
            f"[{severity.upper()}] {alert_type}",
            message,
            alert_data,
            priority=priority,
            webhook_names=webhook_names
        )
    
    def send_update(self,
                   update_type: str,
                   message: str,
                   data: Optional[Dict[str, Any]] = None,
                   webhook_names: Optional[List[str]] = None) -> str:
        """
        Send a status update notification
        
        Args:
            update_type: Type of update
            message: Update message
            data: Additional data
            webhook_names: Specific webhooks to notify
            
        Returns:
            Notification ID
        """
        update_data = {
            'update_type': update_type,
            'timestamp': time.time()
        }
        if data:
            update_data.update(data)
        
        return self.send_notification(
            NotificationType.UPDATE,
            f"Update: {update_type}",
            message,
            update_data,
            priority=1,  # Low priority for updates
            webhook_names=webhook_names
        )
    
    def _start_worker(self):
        """Start the background worker thread"""
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="WebhookWorker"
        )
        self._worker_thread.start()
        logger.debug("Webhook worker thread started")
    
    def _worker_loop(self):
        """Main worker loop for processing notifications"""
        logger.debug("Webhook worker loop started")
        
        while not self._stop_event.is_set():
            try:
                # Get notification from queue with timeout
                try:
                    notification_id, webhook_name, notification = \
                        self.notification_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Process the notification
                self._deliver_notification(notification_id, webhook_name, notification)
                
                # Mark task as done
                self.notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in webhook worker loop: {e}", exc_info=True)
        
        logger.debug("Webhook worker loop terminated")
    
    def _deliver_notification(self, 
                            notification_id: str,
                            webhook_name: str,
                            notification: Notification):
        """
        Deliver a notification to a specific webhook
        
        Args:
            notification_id: ID of the notification
            webhook_name: Name of the webhook to deliver to
            notification: Notification to deliver
        """
        webhook_config = self.webhooks.get(webhook_name)
        if not webhook_config or not webhook_config.enabled:
            logger.debug(f"Webhook '{webhook_name}' not found or disabled")
            return
        
        # Check rate limiting
        if not self._check_rate_limit(webhook_name, webhook_config):
            logger.debug(f"Rate limit exceeded for webhook '{webhook_name}', retrying later")
            # Re-queue for later delivery
            time.sleep(webhook_config.retry_backoff)
            self.notification_queue.put((notification_id, webhook_name, notification))
            return
        
        # Prepare the payload
        payload = {
            'id': notification.id,
            'type': notification.type.value,
            'title': notification.title,
            'message': notification.message,
            'data': notification.data,
            'timestamp': notification.timestamp,
            'priority': notification.priority
        }
        
        # Prepare headers
        headers = webhook_config.headers.copy() if webhook_config.headers else {}
        headers['Content-Type'] = 'application/json'
        headers['User-Agent'] = 'TradingWebhookNotifier/1.0'
        
        # Add signature if secret is configured
        if webhook_config.secret:
            signature = self._generate_signature(
                webhook_config.secret,
                json.dumps(payload, sort_keys=True)
            )
            headers['X-Signature'] = signature
            headers['X-Timestamp'] = str(int(notification.timestamp))
        
        # Attempt delivery with retries
        delivery = WebhookDelivery(
            notification_id=notification_id,
            webhook_url=webhook_config.url,
            status=WebhookStatus.PENDING,
            attempt_count=0,
            last_attempt=time.time()
        )
        
        max_attempts = webhook_config.retry_count + 1  # Initial attempt + retries
        
        for attempt in range(max_attempts):
            delivery.attempt_count = attempt + 1
            delivery.last_attempt = time.time()
            delivery.status = WebhookStatus.RETRYING if attempt > 0 else WebhookStatus.PENDING
            
            try:
                logger.debug(
                    f"Attempt {attempt + 1}/{max_attempts} to deliver notification "
                    f"{notification_id} to {webhook_config.url}"
                )
                
                response = requests.post(
                    webhook_config.url,
                    json=payload,
                    headers=headers,
                    timeout=webhook_config.timeout
                )
                
                delivery.response_code = response.status_code
                delivery.response_body = response.text[:500]  # Limit response body size
                
                if 200 <= response.status_code < 300:
                    delivery.status = WebhookStatus.SENT
                    logger.info(
                        f"Successfully delivered notification {notification_id} "
                        f"to {webhook_config.url} (status: {response.status_code})"
                    )
                    break
                else:
                    logger.warning(
                        f"Failed to deliver notification {notification_id} "
                        f"to {webhook_config.url} (status: {response.status_code})"
                    )
                    
                    # If this was the last attempt, mark as failed
                    if attempt == max_attempts - 1:
                        delivery.status = WebhookStatus.FAILED
                        delivery.error_message = f"HTTP {response.status_code}: {response.text[:100]}"
                    else:
                        # Wait before retry
                        wait_time = webhook_config.retry_backoff * (2 ** attempt)
                        logger.debug(f"Waiting {wait_time:.2f}s before retry")
                        time.sleep(wait_time)
                        
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Request exception delivering notification {notification_id} "
                    f"to {webhook_config.url}: {e}"
                )
                
                if attempt == max_attempts - 1:
                    delivery.status = WebhookStatus.FAILED
                    delivery.error_message = str(e)
                else:
                    # Wait before retry
                    wait_time = webhook_config.retry_backoff * (2 ** attempt)
                    logger.debug(f"Waiting {wait_time:.2f}s before retry")
                    time.sleep(wait_time)
            
            except Exception as e:
                logger.error(
                    f"Unexpected error delivering notification {notification_id} "
                    f"to {webhook_config.url}: {e}", exc_info=True
                )
                
                if attempt == max_attempts - 1:
                    delivery.status = WebhookStatus.FAILED
                    delivery.error_message = str(e)
                else:
                    # Wait before retry
                    wait_time = webhook_config.retry_backoff * (2 ** attempt)
                    logger.debug(f"Waiting {wait_time:.2f}s before retry")
                    time.sleep(wait_time)
        
        # Record delivery attempt
        with self._lock:
            self.delivery_history.append(delivery)
            # Keep only last 1000 deliveries
            if len(self.delivery_history) > 1000:
                self.delivery_history = self.delivery_history[-1000:]
        
        # Update last request time for rate limiting
        self._last_request_times[webhook_name] = time.time()
    
    def _check_rate_limit(self, webhook_name: str, config: WebhookConfig) -> bool:
        """Check if we're within rate limits for a webhook"""
        if config.rate_limit <= 0:
            return True
        
        last_request = self._last_request_times.get(webhook_name, 0)
        time_since_last = time.time() - last_request
        
        return time_since_last >= config.rate_limit
    
    def _generate_signature(self, secret: str, payload: str) -> str:
        """Generate HMAC signature for webhook security"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics"""
        with self._lock:
            total = len(self.delivery_history)
            if total == 0:
                return {
                    'total_deliveries': 0,
                    'sent': 0,
                    'failed': 0,
                    'success_rate': 0.0
                }
            
            sent = sum(1 for d in self.delivery_history if d.status == WebhookStatus.SENT)
            failed = sum(1 for d in self.delivery_history if d.status == WebhookStatus.FAILED)
            
            return {
                'total_deliveries': total,
                'sent': sent,
                'failed': failed,
                'success_rate': (sent / total) * 100 if total > 0 else 0.0,
                'webhooks_configured': len(self.webhooks),
                'webhooks_enabled': sum(1 for c in self.webhooks.values() if c.enabled),
                'queue_size': self.notification_queue.qsize()
            }
    
    def get_recent_deliveries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent delivery attempts"""
        with self._lock:
            recent = self.delivery_history[-limit:] if self.delivery_history else []
            return [
                {
                    'notification_id': d.notification_id,
                    'webhook_url': d.webhook_url,
                    'status': d.status.value,
                    'attempt_count': d.attempt_count,
                    'last_attempt': d.last_attempt,
                    'response_code': d.response_code,
                    'error_message': d.error_message
                }
                for d in reversed(recent)  # Most recent first
            ]
    
    def clear_history(self):
        """Clear delivery history"""
        with self._lock:
            self.delivery_history.clear()
        logger.info("Delivery history cleared")
    
    def stop(self):
        """Stop the webhook notifier"""
        logger.info("Stopping TradingWebhookNotifier...")
        self._stop_event.set()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        
        logger.info("TradingWebhookNotifier stopped")

# Global notifier instance
_notifier: Optional[TradingWebhookNotifier] = None

def get_webhook_notifier() -> TradingWebhookNotifier:
    """Get the global webhook notifier instance"""
    global _notifier
    if _notifier is None:
        _notifier = TradingWebhookNotifier()
    return _notifier

def send_trading_signal(signal: str, symbol: str, price: float, 
                       confidence: float, strategy: str,
                       data: Optional[Dict[str, Any]] = None) -> str:
    """
    Convenience function to send a trading signal
    
    Args:
        signal: Signal type (BUY, SELL, HOLD)
        symbol: Trading symbol
        price: Current price
        confidence: Signal confidence (0-1)
        strategy: Strategy name
        data: Additional data
        
    Returns:
        Notification ID
    """
    notifier = get_webhook_notifier()
    return notifier.send_signal(signal, symbol, price, confidence, strategy, data)

def send_trading_alert(alert_type: str, message: str, 
                      severity: str = "medium",
                      data: Optional[Dict[str, Any]] = None) -> str:
    """
    Convenience function to send a trading alert
    
    Args:
        alert_type: Type of alert
        message: Alert message
        severity: Alert severity
        data: Additional data
        
    Returns:
        Notification ID
    """
    notifier = get_webhook_notifier()
    return notifier.send_alert(alert_type, message, severity, data)

def add_trading_webhook(name: str, url: str, 
                       secret: Optional[str] = None,
                       headers: Optional[Dict[str, str]] = None,
                       **kwargs) -> None:
    """
    Convenience function to add a trading webhook
    
    Args:
        name: Webhook identifier
        url: Webhook URL
        secret: Optional secret for HMAC signing
        headers: Optional custom headers
        **kwargs: Additional WebhookConfig parameters
    """
    notifier = get_webhook_notifier()
    config = WebhookConfig(
        url=url,
        secret=secret,
        headers=headers or {},
        **kwargs
    )
    notifier.add_webhook(name, config)

# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def test_webhook_notifier():
        """Test the webhook notifier functionality"""
        print("Testing TradingWebhookNotifier...")
        
        # Create notifier
        notifier = TradingWebhookNotifier()
        
        # Add a test webhook (httpbin.org for testing)
        notifier.add_webhook(
            "test_webhook",
            WebhookConfig(
                url="https://httpbin.org/post",
                secret="test-secret-123",
                headers={"X-Custom-Header": "test-value"},
                timeout=5.0,
                retry_count=2,
                rate_limit=0.1  # 100ms between requests for testing
            )
        )
        
        # Test sending different types of notifications
        print("\\n--- Testing Signal Notification ---")
        signal_id = notifier.send_signal(
            signal="BUY",
            symbol="BTC/USD",
            price=45000.50,
            confidence=0.85,
            strategy="Moving Average Crossover",
            data={"timeframe": "1h", "indicators": {"MA_50": 44800, "MA_200": 44200}}
        )
        print(f"Sent signal notification: {signal_id}")
        
        print("\\n--- Testing Alert Notification ---")
        alert_id = notifier.send_alert(
            alert_type="PRICE_BREAKOUT",
            message="BTC/USD has broken above $46,000 resistance level",
            severity="high",
            data={"breakout_price": 46000, "volume_increase": 2.5}
        )
        print(f"Sent alert notification: {alert_id}")
        
        print("\\n--- Testing Update Notification ---")
        update_id = notifier.send_update(
            update_type="SYSTEM_STATUS",
            message="Trading system is operating normally",
            data={"uptime_hours": 24.5, "active_strategies": 3}
        )
        print(f"Sent update notification: {update_id}")
        
        # Wait a bit for deliveries to complete
        print("\\nWaiting for deliveries to complete...")
        time.sleep(3)
        
        # Show statistics
        print("\\n--- Delivery Statistics ---")
        stats = notifier.get_delivery_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\\n--- Recent Deliveries ---")
        recent = notifier.get_recent_deliveries(limit=5)
        for delivery in recent:
            print(f"  {delivery['notification_id']}: {delivery['status']} "
                  f"(attempts: {delivery['attempt_count']})")
        
        # Clean up
        notifier.stop()
        print("\\nTest completed successfully!")
    
    # Run the test
    test_webhook_notifier()
