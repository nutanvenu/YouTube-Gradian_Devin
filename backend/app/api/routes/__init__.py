"""Compatibility exports for the API route registry."""

from ..handler_registry import app, notifier, parent_from_access, signer

__all__ = ["app", "notifier", "parent_from_access", "signer"]
