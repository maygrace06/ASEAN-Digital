"""Base class + registry for source fetchers.

To add a brand-new *type* of source, create a module in this folder with a
class decorated by @register("my_type") that implements fetch() and returns
a list of Opportunity objects. Then use `type: my_type` in sources.yaml.
"""
from __future__ import annotations

import re
from typing import Callable

from ..models import Opportunity

REGISTRY: dict[str, type["Source"]] = {}


def register(type_name: str) -> Callable:
    def deco(cls):
        REGISTRY[type_name] = cls
        cls.type_name = type_name
        return cls
    return deco


class Source:
    type_name = "base"

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.id = cfg["id"]
        self.kind = cfg.get("kind", "grant")
        self.funder = cfg.get("funder", "")
        self.include = re.compile(cfg["include"], re.I) if cfg.get("include") else None
        self.exclude = re.compile(cfg["exclude"], re.I) if cfg.get("exclude") else None
        self.errors: list[str] = []   # non-fatal errors (one keyword / one URL failed)

    def warn(self, where: str, err: Exception) -> None:
        from ..utils import log
        msg = f"{where}: {type(err).__name__}: {err}"[:200]
        self.errors.append(msg)
        log.warning("  %s", msg)

    def fetch(self) -> list[Opportunity]:  # pragma: no cover
        raise NotImplementedError

    # helper used by subclasses
    def make(self, **kw) -> Opportunity:
        kw.setdefault("source", self.id)
        kw.setdefault("kind", self.kind)
        if not kw.get("funder"):
            kw["funder"] = self.funder
        return Opportunity(**kw)

    def keep(self, opp: Opportunity) -> bool:
        text = f"{opp.title} {opp.summary}"
        if self.include and not self.include.search(text):
            return False
        if self.exclude and self.exclude.search(text):
            return False
        return True
