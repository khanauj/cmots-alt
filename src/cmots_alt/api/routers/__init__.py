"""API routers, grouped by domain (system, admin, stocks, mutual-funds, scheduler)."""

from . import admin, mutual_funds, scheduler, stocks, system

__all__ = ["system", "admin", "stocks", "mutual_funds", "scheduler"]
