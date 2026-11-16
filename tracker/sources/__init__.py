"""Importing this package registers all built-in source types."""
from . import apis, html, json_api, manual, rss  # noqa: F401
from .base import REGISTRY, Source, register  # noqa: F401
