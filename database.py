"""Compatibility bridge for DatabaseManager.

This file re-exports the primary implementation from `database_manager.py`.
Only a small bridge is kept to maintain older import paths (`from database import DatabaseManager`).
"""

from database_manager import DatabaseManager  # re-export for backward compatibility

__all__ = ["DatabaseManager"]
