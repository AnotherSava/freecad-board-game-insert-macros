import importlib

import FreeCAD

from common import freecad

importlib.reload(freecad)
freecad.reloadProjectModules()

from common.freecad import reloadProjectModules, clearLogs, closeAllDocuments

clearLogs()
closeAllDocuments()
reloadProjectModules()

from constants import nozzleSize
from common.magnets import MAGNET_3x2
from other.bitholder import BitHolderDimensions, BitHolder
from common.export import ExportObject, Exporter

reloadProjectModules()

bitHolderDimensions = BitHolderDimensions(
    shortDiagonal = 6.3 + 0.1,
    shortDiagonalDelta = 0.15,
    gap = 3,
    padding=1.2,
    height = 9.2,
    holeHeight = 8,
    magnetDimensions = MAGNET_3x2,
    magnetCount = 2,
    roundedLength = 1,
    innerWallThickness = nozzleSize * 2,
    innerWallDelta = 0.4,
    outerWallThickness = 1.2,
    rowLengths = [4, 5, 6, 9, 9, 12],
    outerWallRoundedLength = 4,
    circularHoleDiameter = 10
)

document = FreeCAD.newDocument('BitHolder')




exportItems = [
    # *[ExportObject(f"bit-holder-{length}", lambda r=row, l=length: BitHolder(bitHolderDimensions).createRow(r, l)) for row, length in enumerate(bitHolderDimensions.rowLengths[:1])],
    # *[ExportObject(f"bit-holder-{length}", lambda r=row, l=length: BitHolder(bitHolderDimensions).createRow(r, l)) for row, length in enumerate(bitHolderDimensions.rowLengths)],
    ExportObject(f"bit-holder-special", lambda: BitHolder(bitHolderDimensions).createSpecial()),
    # ExportObject(f"bit-holder-box", lambda: BitHolder(bitHolderDimensions).createHolder())
]



# FreeCAD.Gui.activeDocument().activeView().viewIsometric()
# FreeCAD.Gui.activeDocument().activeView().viewLeft()
# FreeCAD.Gui.activeDocument().activeView().viewFront()
FreeCAD.Gui.activeDocument().activeView().viewTop()
# FreeCAD.Gui.activeDocument().activeView().viewBottom()
# FreeCAD.Gui.runCommand('Std_DrawStyle', 6)


exporter = Exporter("D:\\projects\\3d\\FreeCAD\\models\\Bit Holder", *exportItems)
# exporter.withBound(SmartBox(10.5, 100, 100).translate(1.5))
# exporter.show(10)
exporter.export(10)
# exporter.publish()
