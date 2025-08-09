from __future__ import annotations

from typing import Callable, Dict, Tuple, Any
import threading

class AgentRegistry:
    """
    Minimal thread-safe registry of agent builders.

    Builder signature is flexible: usually `builder(redis, tenant_id)` or
    whatever your `build_loop(...)` returns.
    """
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._map: Dict[Tuple[str, str], Callable[..., Any]] = {}

    def register(self, pack: str, agent: str, builder: Callable[..., Any]) -> None:
        key = (pack.strip(), agent.strip())
        with self._lock:
            if key in self._map:
                raise ValueError(f"Agent already registered: {pack}/{agent}")
            self._map[key] = builder

    def set(self, pack: str, agent: str, builder: Callable[..., Any]) -> None:
        """Overwrite existing registration (useful during dev reload)."""
        key = (pack.strip(), agent.strip())
        with self._lock:
            self._map[key] = builder

    def get(self, pack: str, agent: str) -> Callable[..., Any]:
        key = (pack.strip(), agent.strip())
        with self._lock:
            try:
                return self._map[key]
            except KeyError:
                raise KeyError(f"Unknown agent: {pack}/{agent}. Registered: {self.list()}")

    def list(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        with self._lock:
            for (p, a) in self._map.keys():
                out.setdefault(p, []).append(a)
        for p in out:
            out[p].sort()
        return out

# Singleton
REGISTRY = AgentRegistry()

# ---- Built-in registrations (wire packs here) -------------------------------

# Doc2Deck pack
try:
    # Your Converter class must expose a .build(...) classmethod
    from app.packs.doc2deck.agents import Converter as Doc2DeckConverter
    REGISTRY.set("doc2deck", "converter", Doc2DeckConverter.build)
except Exception:
    # Keep startup resilient even if optional packs are missing
    pass

# Example: existing SEO pack (if present in your repo)
try:
    from app.packs.seo_factory.agents import KeywordResearcher
    REGISTRY.set("seo_factory", "keyword_researcher", KeywordResearcher.build)
except Exception:
    pass
