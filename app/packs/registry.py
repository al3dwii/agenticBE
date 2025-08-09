# Backward-compatible registry that supports both:
# - REGISTRY()                 (callable)
# - REGISTRY.get(...)/[...]    (dict-like)
# - get_registry()             (function returning the plain dict)

def _build_registry():
    reg = {}
    # Only keep the Office pack to avoid old doc2deck import issues
    from .office import register as register_office
    reg.update(register_office())
    return reg

class _RegistryProxy:
    def __init__(self):
        self._map = _build_registry()

    # allow REGISTRY() usage
    def __call__(self):
        return self._map

    # dict-like helpers
    def get(self, *args, **kwargs): return self._map.get(*args, **kwargs)
    def __getitem__(self, k): return self._map[k]
    def __iter__(self): return iter(self._map)
    def items(self): return self._map.items()
    def keys(self): return self._map.keys()
    def values(self): return self._map.values()
    def __contains__(self, k): return k in self._map
    def __len__(self): return len(self._map)

    # convenience for debug/inspection
    def list(self):
        return {pack: sorted(agents.keys()) for pack, agents in self._map.items()}

    def __repr__(self):
        return f"REGISTRY({self._map!r})"

REGISTRY = _RegistryProxy()

def get_registry():
    # return the plain dict mapping
    return REGISTRY()
