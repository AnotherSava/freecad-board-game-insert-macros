import sys

import importlib


def reloadProjectModules():
    reloadedModules = []

    for moduleName in [name for name in sys.modules.keys() if (name.startswith('Inserts') or name.startswith('common')) and sys.modules[name] is not None]:
        importlib.reload(sys.modules[moduleName])
        reloadedModules.append(moduleName.removeprefix("Inserts."))

    if reloadedModules:
        print(f"Reloaded modules: {', '.join(reloadedModules)}")
