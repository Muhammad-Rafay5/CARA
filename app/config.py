"""
Backward-compatible configuration entry point.
Delegates configuration management to app.config.settings.
"""

from app.config.settings import AppSettings, settings

__all__ = ["AppSettings", "settings"]
