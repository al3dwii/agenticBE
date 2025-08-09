"""
Backward-compatible registry:

- REGISTRY           -> dict-like AND callable; returns {pack_name: register_fn}
- REGISTRY.get(name) -> register function (callable) expected by existing code
- get_registry()     -> materialized mapping { pack: { agent_name: callable } }
"""

def _register_map():
    # Keep only the Office pack to avoid doc2deck import issues
    from .office import register as register_office
    return {
        "office": register_office,  # callable returning {"office": {...agents...}}
    }

class _RegistryProxy:
    def __init__(self):
        self._map = _register_map()  # { pack: register_fn }

    # allow REGISTRY() usage to get the {pack: register_fn} mapping
    def __call__(self):
        return self._map

    # dict-like
    def get(self, *args, **kwargs): return self._map.get(*args, **kwargs)
    def __getitem__(self, k): return self._map[k]
    def __iter__(self): return iter(self._map)
    def items(self): return self._map.items()
    def keys(self): return self._map.keys()
    def values(self): return self._map.values()
    def __contains__(self, k): return k in self._map
    def __len__(self): return len(self._map)
    def __repr__(self): return f"REGISTRY(registers={list(self._map.keys())})"

REGISTRY = _RegistryProxy()

def get_registry():
    """
    Build the final { pack: { agent_name: callable } } by invoking each register().
    """
    out = {}
    for reg_fn in REGISTRY.values():
        out.update(reg_fn())
    return out
