"""Typed, immutable views over the catalog manifest.

Parsing is deliberately lenient: unknown fields are ignored so an older app can
read a slightly newer (same schema_version) manifest. Hard validation lives in
``tools/validate_catalog.py`` and the JSON Schema.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Runtime(str, Enum):
    RUFFLE = "ruffle"
    FLASH = "flash"
    WEB = "web"
    CLIENT = "client"


class Status(str, Enum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    UNSTABLE = "unstable"
    OFFLINE = "offline"


def classify_status(http_status: int) -> Status:
    """Map an HTTP status code (0 = no response) to a badge state."""
    if http_status == 0:
        return Status.OFFLINE
    if 200 <= http_status < 400:
        return Status.ONLINE
    if http_status in (408, 429, 502, 503, 504):
        return Status.UNSTABLE
    # 4xx that isn't rate-limiting: reachable but the endpoint is unhappy.
    return Status.UNSTABLE if http_status < 500 else Status.OFFLINE


@dataclass(frozen=True)
class Server:
    name: str
    url: str
    status_url: str
    default: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Server":
        url = d["url"]
        return cls(
            name=d["name"],
            url=url,
            status_url=d.get("status_url", url),
            default=bool(d.get("default", False)),
        )


@dataclass(frozen=True)
class Category:
    id: str
    name: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Category":
        return cls(id=d["id"], name=d["name"])


@dataclass(frozen=True)
class Title:
    id: str
    name: str
    category: str
    runtime: Runtime
    art: str
    servers: tuple[Server, ...]
    description: str = ""
    ruffle: dict[str, Any] = field(default_factory=dict)
    client: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    notes: str = ""
    homepage: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Title":
        return cls(
            id=d["id"],
            name=d["name"],
            category=d["category"],
            runtime=Runtime(d["runtime"]),
            art=d["art"],
            servers=tuple(Server.from_dict(s) for s in d["servers"]),
            description=d.get("description", ""),
            ruffle=dict(d.get("ruffle", {})),
            client=dict(d.get("client", {})),
            tags=tuple(d.get("tags", [])),
            notes=d.get("notes", ""),
            homepage=d.get("homepage", ""),
        )

    @property
    def default_server(self) -> Server:
        for s in self.servers:
            if s.default:
                return s
        return self.servers[0]

    def matches(self, query: str) -> bool:
        q = query.casefold().strip()
        if not q:
            return True
        haystack = " ".join((self.name, self.description, " ".join(self.tags))).casefold()
        return q in haystack


@dataclass(frozen=True)
class Catalog:
    schema_version: int
    updated: str
    categories: tuple[Category, ...]
    titles: tuple[Title, ...]

    SUPPORTED_SCHEMA = 1

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Catalog":
        version = int(d["schema_version"])
        if version != cls.SUPPORTED_SCHEMA:
            raise UnsupportedSchema(version)
        return cls(
            schema_version=version,
            updated=d.get("updated", ""),
            categories=tuple(Category.from_dict(c) for c in d["categories"]),
            titles=tuple(Title.from_dict(t) for t in d["titles"]),
        )

    def category(self, cid: str) -> Optional[Category]:
        return next((c for c in self.categories if c.id == cid), None)

    def titles_in(self, category_id: str) -> list[Title]:
        return [t for t in self.titles if t.category == category_id]

    def title(self, tid: str) -> Optional[Title]:
        return next((t for t in self.titles if t.id == tid), None)


class UnsupportedSchema(Exception):
    def __init__(self, version: int) -> None:
        super().__init__(f"Unsupported catalog schema_version {version}")
        self.version = version
