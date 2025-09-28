import sys

import importlib
import FreeCAD
from PySide2 import QtWidgets


def reloadProjectModules():
    reloadedModules = []

    for moduleName in [name for name in sys.modules.keys() if (name.startswith('Inserts') or name.startswith('common') or name.startswith('constants')) and sys.modules[name] is not None]:
        importlib.reload(sys.modules[moduleName])
        reloadedModules.append(moduleName.removeprefix("Inserts."))

    if reloadedModules:
        print(f"Reloaded modules: {', '.join(reloadedModules)}")

def clearLogs():
    mw = FreeCAD.Gui.getMainWindow()
    report_view = mw.findChild(QtWidgets.QTextEdit, "Report view")

    if report_view:
        report_view.clear()
    else:
        print("Report view not found")

def closeAllDocuments():
    for doc_name in list(FreeCAD.listDocuments().keys()):
        FreeCAD.closeDocument(doc_name)