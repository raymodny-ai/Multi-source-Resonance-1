"""
Multi-channel notification manager.

Supports:
- Email (SMTP via smtplib)
- Webhook (generic HTTP POST via httpx)
- Telegram (Bot API via httpx)

Integrates with EventBus to auto-send on SIGNAL_ALERT events.

Usage:
    manager = NotificationManager()
    await manager.send(level="LEVEL_3", message={...}, channel="telegram")
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    TELEGRAM = "telegram"


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# Map signal alert levels to notification severity
_LEVEL_MAP = {
    "LEVEL_0": NotificationLevel.INFO,
    "LEVEL_1": NotificationLevel.INFO,
    "LEVEL_2": NotificationLevel.WARNING,
    "LEVEL_3": NotificationLevel.CRITICAL,
}


class NotificationManager:
    """Multi-channel notification delivery manager.

    Reads configuration from backend.config.settings and supports
    runtime configuration updates via update_config().

    Integrates with EventBus: subscribe to SIGNAL_ALERT events
    to automatically dispatch notifications.
    """

    def __init__(self, config: Optional[dict] = None) -> None:
        self._config = config or self._default_config()
        self._enabled_channels: list[NotificationChannel] = []
        self._send_history: list[dict] = []
        self._max_history = 100

        # Determine enabled channels
        if self._config.get("email", {}).get("enabled"):
            self._enabled_channels.append(NotificationChannel.EMAIL)
        if self._config.get("webhook", {}).get("enabled"):
            self._enabled_channels.append(NotificationChannel.WEBHOOK)
        if self._config.get("telegram", {}).get("enabled"):
            self._enabled_channels.append(NotificationChannel.TELEGRAM)

        logger.info(
            f"NotificationManager initialized: "
            f"channels={[c.value for c in self._enabled_channels]}"
        )

    async def send(
        self,
        level: str,
        message: dict,
        channel: Optional[str] = None,
    ) -> dict[str, bool]:
        """Send a notification through specified channel(s).

        Args:
            level: Alert level (LEVEL_0..LEVEL_3) or severity (info/warning/critical).
            message: Notification payload dict with keys:
                - title: str
                - body: str
                - score: float (optional)
                - dimensions: dict (optional)
                - timestamp: str (optional)
            channel: Specific channel name, or None for all enabled channels.

        Returns:
            dict mapping channel names to success status.
        """
        results: dict[str, bool] = {}
        severity = self._resolve_severity(level)

        # Determine target channels
        if channel:
            try:
                target_channels = [NotificationChannel(channel)]
            except ValueError:
                logger.error(f"Unknown channel: {channel}")
                return {channel: False}
        else:
            target_channels = self._enabled_channels

        # Build notification content
        content = self._build_content(severity, message)

        # Dispatch to all target channels concurrently
        tasks = []
        for ch in target_channels:
            if ch == NotificationChannel.EMAIL:
                tasks.append(self._send_email(content, severity))
            elif ch == NotificationChannel.WEBHOOK:
                tasks.append(self._send_webhook(content, severity))
            elif ch == NotificationChannel.TELEGRAM:
                tasks.append(self._send_telegram(content, severity))

        if tasks:
            send_results = await asyncio.gather(*tasks, return_exceptions=True)

            for ch, result in zip(target_channels, send_results):
                if isinstance(result, Exception):
                    logger.error(f"Notification failed for {ch.value}: {result}")
                    results[ch.value] = False
                else:
                    results[ch.value] = result

        # Record in history
        self._record_send(level, message, results)

        return results

    async def send_test(self, channel: str) -> bool:
        """Send a test notification to verify channel configuration.

        Args:
            channel: Channel name to test.

        Returns:
            True if test notification was sent successfully.
        """
        test_message = {
            "title": "Test Notification",
            "body": "This is a test notification from Multi-source Resonance Monitor.",
            "score": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        results = await self.send("LEVEL_1", test_message, channel=channel)
        return results.get(channel, False)

    def update_config(self, config: dict) -> None:
        """Update notification configuration at runtime.

        Args:
            config: New configuration dict.
        """
        self._config = config
        self._enabled_channels.clear()

        if config.get("email", {}).get("enabled"):
            self._enabled_channels.append(NotificationChannel.EMAIL)
        if config.get("webhook", {}).get("enabled"):
            self._enabled_channels.append(NotificationChannel.WEBHOOK)
        if config.get("telegram", {}).get("enabled"):
            self._enabled_channels.append(NotificationChannel.TELEGRAM)

        logger.info(f"Notification config updated: channels={[c.value for c in self._enabled_channels]}")

    def get_config(self) -> dict:
        """Get current notification configuration (with secrets masked)."""
        config = dict(self._config)
        # Mask sensitive values
        for ch_config in config.values():
            if isinstance(ch_config, dict):
                for key in ["password", "token", "api_key"]:
                    if key in ch_config:
                        ch_config[key] = "***masked***"
        return config

    def get_status(self) -> dict:
        """Get notification system status."""
        return {
            "enabled_channels": [c.value for c in self._enabled_channels],
            "total_sent": len(self._send_history),
            "last_sent_at": self._send_history[-1]["timestamp"] if self._send_history else None,
            "config": self.get_config(),
        }

    async def register_eventbus_handler(self, event_bus: Any) -> None:
        """Register as EventBus handler for SIGNAL_ALERT events.

        Args:
            event_bus: EventBus instance.
        """
        from backend.eventbus.events import EventType

        async def _on_signal_alert(event_type: str, data: dict) -> None:
            """Handle SIGNAL_ALERT event by sending notifications."""
            level = data.get("alert_level", "LEVEL_0")
            message = {
                "title": f"Resonance Signal: {level}",
                "body": f"Score: {data.get('total_score', 0):.2f}",
                "score": data.get("total_score", 0),
                "dimensions": {
                    "gex": data.get("gex_score"),
                    "vix": data.get("vix_score"),
                    "crypto": data.get("crypto_score"),
                    "darkpool": data.get("darkpool_score"),
                },
                "timestamp": data.get("trigger_time"),
            }
            await self.send(level, message)

        await event_bus.subscribe(EventType.SIGNAL_ALERT, _on_signal_alert)
        logger.info("NotificationManager registered as SIGNAL_ALERT handler")

    # ── Channel Implementations ──────────────────────────────────────────────

    async def _send_email(self, content: dict, severity: NotificationLevel) -> bool:
        """Send notification via SMTP email."""
        email_config = self._config.get("email", {})
        if not email_config.get("enabled"):
            return False

        try:
            smtp_host = email_config.get("smtp_host", "localhost")
            smtp_port = email_config.get("smtp_port", 587)
            smtp_user = email_config.get("smtp_user", "")
            smtp_password = email_config.get("smtp_password", "")
            from_addr = email_config.get("from_addr", smtp_user)
            to_addrs = email_config.get("to_addrs", [])

            if not to_addrs:
                logger.warning("No email recipients configured")
                return False

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{severity.value.upper()}] {content['title']}"
            msg["From"] = from_addr
            msg["To"] = ", ".join(to_addrs)

            # Plain text body
            msg.attach(MIMEText(content["plain_text"], "plain"))
            # HTML body
            msg.attach(MIMEText(content["html"], "html"))

            # Send email
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._send_smtp_sync(smtp_host, smtp_port, smtp_user, smtp_password, from_addr, to_addrs, msg),
            )

            logger.info(f"Email sent to {to_addrs}")
            return True

        except Exception as e:
            logger.error(f"Email notification failed: {e}", exc_info=True)
            return False

    def _send_smtp_sync(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
        msg: MIMEMultipart,
    ) -> None:
        """Synchronous SMTP send (runs in executor)."""
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())

    async def _send_webhook(self, content: dict, severity: NotificationLevel) -> bool:
        """Send notification via generic HTTP webhook."""
        webhook_config = self._config.get("webhook", {})
        if not webhook_config.get("enabled"):
            return False

        url = webhook_config.get("url")
        if not url:
            logger.warning("Webhook URL not configured")
            return False

        try:
            payload = {
                "level": severity.value,
                "title": content["title"],
                "body": content["plain_text"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "multi-source-resonance",
            }

            # Add custom headers if configured
            headers = {"Content-Type": "application/json"}
            custom_headers = webhook_config.get("headers", {})
            headers.update(custom_headers)

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()

            logger.info(f"Webhook notification sent to {url}")
            return True

        except Exception as e:
            logger.error(f"Webhook notification failed: {e}", exc_info=True)
            return False

    async def _send_telegram(self, content: dict, severity: NotificationLevel) -> bool:
        """Send notification via Telegram Bot API."""
        telegram_config = self._config.get("telegram", {})
        if not telegram_config.get("enabled"):
            return False

        bot_token = telegram_config.get("bot_token")
        chat_id = telegram_config.get("chat_id")

        if not bot_token or not chat_id:
            logger.warning("Telegram bot_token or chat_id not configured")
            return False

        try:
            # Format message with emoji based on severity
            emoji_map = {
                NotificationLevel.INFO: "ℹ️",
                NotificationLevel.WARNING: "⚠️",
                NotificationLevel.CRITICAL: "🚨",
            }
            emoji = emoji_map.get(severity, "📢")

            text = f"{emoji} <b>{content['title']}</b>\n\n{content['plain_text']}"

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()

            logger.info(f"Telegram notification sent to chat {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Telegram notification failed: {e}", exc_info=True)
            return False

    # ── Content Building ─────────────────────────────────────────────────────

    def _build_content(self, severity: NotificationLevel, message: dict) -> dict:
        """Build notification content in multiple formats."""
        title = message.get("title", "Signal Alert")
        body = message.get("body", "")
        score = message.get("score", 0)
        dimensions = message.get("dimensions", {})
        timestamp = message.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Plain text
        lines = [
            f"Signal: {title}",
            f"Severity: {severity.value}",
            f"Score: {score:.2f}",
        ]
        if dimensions:
            lines.append("Dimensions:")
            for dim, val in dimensions.items():
                if val is not None:
                    lines.append(f"  {dim}: {val:.2f}")
        lines.append(f"Time: {timestamp}")
        if body:
            lines.append(f"\n{body}")

        plain_text = "\n".join(lines)

        # HTML
        html_parts = [
            f"<h3>{title}</h3>",
            f"<p><b>Severity:</b> {severity.value}</p>",
            f"<p><b>Score:</b> {score:.2f}</p>",
        ]
        if dimensions:
            html_parts.append("<table>")
            for dim, val in dimensions.items():
                if val is not None:
                    html_parts.append(f"<tr><td>{dim}</td><td>{val:.2f}</td></tr>")
            html_parts.append("</table>")
        html_parts.append(f"<p><i>{timestamp}</i></p>")
        if body:
            html_parts.append(f"<p>{body}</p>")

        html = "\n".join(html_parts)

        return {
            "title": title,
            "plain_text": plain_text,
            "html": html,
        }

    def _resolve_severity(self, level: str) -> NotificationLevel:
        """Resolve alert level to notification severity."""
        if level in _LEVEL_MAP:
            return _LEVEL_MAP[level]
        # Try direct severity mapping
        try:
            return NotificationLevel(level)
        except ValueError:
            return NotificationLevel.WARNING

    def _record_send(self, level: str, message: dict, results: dict[str, bool]) -> None:
        """Record notification send in history."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "title": message.get("title", ""),
            "results": results,
        }
        self._send_history.append(record)
        # Trim history
        if len(self._send_history) > self._max_history:
            self._send_history = self._send_history[-self._max_history:]

    def _default_config(self) -> dict:
        """Build default config from settings."""
        return {
            "email": {
                "enabled": False,
                "smtp_host": "localhost",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_password": "",
                "from_addr": "",
                "to_addrs": [],
            },
            "webhook": {
                "enabled": False,
                "url": "",
                "headers": {},
            },
            "telegram": {
                "enabled": False,
                "bot_token": "",
                "chat_id": "",
            },
        }
