"""Validator modules (one per category). Importing this package registers them all."""
import importlib
import pkgutil

for _m in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_m.name}")
