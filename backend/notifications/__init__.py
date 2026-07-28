"""
Notification subsystem — multi-channel alert delivery.
"""

from backend.notifications.notifier import NotificationManager, NotificationChannel

__all__ = [
    "NotificationManager",
    "NotificationChannel",
]
