# Registry MUST be callable for the API's import site (it does REGISTRY())
# We expose REGISTRY() returning the mapping, plus helpers for convenience.

from .office import register as register_office

def REGISTRY():
    reg = {}
    reg.update(register_office())
    return reg

# Back-compat: some code may import get_registry()
get_registry = REGISTRY
