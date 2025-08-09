# Auto-generated registry for agenticBE (doc2deck + office only)
from .doc2deck import register as register_doc2deck
from .office import register as register_office

REGISTRY = {}
REGISTRY.update(register_doc2deck())
REGISTRY.update(register_office())

def get_registry():
    return REGISTRY
