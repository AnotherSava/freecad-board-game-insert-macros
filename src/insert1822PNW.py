import importlib

import FreeCAD

from common import freecad
from inserts.cubebox import CubeBox

importlib.reload(freecad)
from common.freecad import reloadProjectModules, clearLogs, closeAllDocuments

clearLogs()
closeAllDocuments()
reloadProjectModules()

from inserts.cardbox import CardBox
from common.magnets import MAGNET_3x3
from inserts.common.meshlid import MeshLidDimensions
from inserts import company, cardbox, cubebox, markerbox
from common.colours import MultiColourFuser
from common.export import ExportObject, Exporter
from common.smartbox import Side
from inserts.company import CylinderObjectSet, CompanyBox
from inserts.hex.condensed import CondensedBoard, GridDimensions
from inserts.hex.images import HexImageDimensions, Images
from inserts.common.lidbox import LidDimensions
from constants import nozzleSize, magnet3x3height, magnet2x3height, magnet3Diameter, magnet2Diameter

reloadProjectModules()

gridDimensions = GridDimensions(
    hexShortDiagonal=28,
    pinWidth=3.9,
    wallTipLengthCoefficient=0.357,
    wallTipWidthCoefficient=0.635,
    pinRadius=1,
    hexRadius=3,
    shallowEdgeAngle=60,
    shorterSideMultiplier=0.928,
    pinHeight=10,
    floorThickness=1.2,
    ceilingThickness=0.8,
    adjacentDistance=nozzleSize * 2,
    magnetDiameterFloor=magnet2Diameter + 0.15,
    magnetDiameter=magnet3Diameter + 0.05,
    # magnetDiameter=magnet2Diameter + 0.1,
    magnetHeightFloor=magnet2x3height,
    magnetHeightCeiling=magnet3x3height,
    magnetBaseWall=nozzleSize*2,
    maxRowsPerMagnet=2,
    lidHoleAngle=45,
    lidHoleMultiplier=0.85,
    lidInfillThickness=nozzleSize*1.1,
    lidExternalWallThickness=2,
    lidSideDelta=2.3
)

hexImageDimensions = HexImageDimensions(
    imageHeight=0.32,
    hexShortDiagonal=28,
    railWidth=2,
    townBarWidth=5,
    townBarLength=1.5,
    cityDiameter=10,
    townDiameter=4,
    scale=1,
    lineWidth=0.45,
    whiteLayerHeight=0.16,
    font="C:/Windows/Fonts/arialbd.ttf",
    fontSize=4,
)

companyBoxDimensions = company.Dimensions(
    lid=LidDimensions(
        lidSlideInDirection=Side.S,
        lidLength=62.8,
        lidWidth=40.8,
        lidHeight=3.2,
        lidGap=1,
        lidWidthWallThickness=0.8,
        lidLengthWallThickness=1.2,
        aboveLidHeight=1.2,
        lidEntranceSizeMultiplier=1.02,
        aboveLidSlideCoefficient=0.5,
        supportThickness=1.2,
        supportLengthMultiplier=11/30
    ),

    wallThickness=4,
    floorHeight=0.8,

    cylinderObjectSets=[
        CylinderObjectSet(name="markers", diameter=13.4, height=7, count=2),
        CylinderObjectSet(name="stations", diameter=10.95, height=10.3, count=5, separate=True)
    ]
)

cardBoxDimensions = cardbox.CardBoxDimensions(
    cardLength=64,
    cardWidth=42,
    cardCutSize=21,
    multiCutSize=32,
    majorCharterCutSize=15,

    scenarioTrainsHeight=5.4,
    playerOrderHeight=2.5,

    # privatesHeight=8.8,
    privatesHeight=11.5, # using the same height for recesses saves ~10% total cost on reducing filament changes to and from support interface
    # minorsHeight=9.7,
    minorsHeight=11.5,
    # ltrainsHeight=9,
    ltrainsHeight=11.5,
    # trainsHeight=10.9,
    trainsHeight=11.5,

    majorCharterLength = 193,
    majorCharterWidth = 129,
    majorChartersHeight=4.4,

    minorCharterLength = 153.5,
    minorCharterWidth = 77.7,
    minorChartersHeight=11.5,

    wallWidth=1.2,
    
    # LidBoxDimensions fields
    lid=LidDimensions(
        lidSlideInDirection=Side.E,
        lidLength=193,
        lidWidth=126.6,
        lidHeight=3.55,
        lidGap=0,
        lidWidthWallThickness=1.2,
        lidLengthWallThickness=1.2,
        aboveLidHeight=1.2,
        simplify=False,
        lidEntranceSizeMultiplier=1.02,
        aboveLidSlideCoefficient=0.5
    ),
    wallThickness=5.3,
    floorHeight=1.2
)

cubeSize = 8
cubeBoxHeight = 12.2

cubeBoxDimensions = cubebox.CubeBoxDimensions(
    lid=MeshLidDimensions(
        magnets=MAGNET_3x3.withWallLoops(2).withDiameterDelta(-0.05),
        handleRadius=2,
        wallThickness=2.4,
        gridThickness=nozzleSize * 1.2,
        height=cardBoxDimensions.getBoxHeight() - cubeBoxHeight,
        fillCorners=True,
        minimalMeshHeight=0.8,
        fillHandleSides=True,
        hexCountLength=28,
        # hexCountLength=16,
        recessLengthCoefficient = 1,
        recessWidthCoefficient = 1,
        slopeLengthCoefficient=0,
        slopeWidthCoefficient=0,
        wallHeight=4.8
        # recessLengthCoefficient = 0.25,
        # recessWidthCoefficient = 0.6,
        # slopeLengthCoefficient=0.3,
        # slopeWidthCoefficient=0.15

# maxGridShortDiagonal = 7
        # maxGridShortDiagonal = 20
    ),

    magnets=MAGNET_3x3.withWallLoops(2),
    wallThickness=nozzleSize * 2,
    length=cardBoxDimensions.getBoxLength(),
    width=240 - cardBoxDimensions.getBoxWidth() - companyBoxDimensions.getBoxLength(),
    gapHeight=cubeSize * 2 / 3,
    holderAngle=12.15,
    height=cubeBoxHeight,
)

markerBoxHeight = 7.2

markerBoxDimensions = markerbox.Dimensions(
    lid = MeshLidDimensions(
        magnets=MAGNET_3x3,
        handleRadius=2,
        wallThickness = nozzleSize * 3,
        gridThickness = nozzleSize * 1.2,
        height = cardBoxDimensions.getBoxHeight() - markerBoxHeight,
        fillCorners = True,
        minimalMeshHeight = nozzleSize * 4,
        hexCountLength = 14,
        # hexCountLength = 24,
        recessLengthCoefficient = 0.25,
        recessWidthCoefficient = 0.6,
        slopeLengthCoefficient=0.3,
        slopeWidthCoefficient=0.15
    ),

    magnets=MAGNET_3x3,
    length=174,
    width=92,
    height=markerBoxHeight,
    lidHeightDelta= 1.6,
    floorHeight=0.8,
    padding=2,

    markers=CylinderObjectSet(diameter=13.4, height=7),
    stations=CylinderObjectSet(diameter=10.95, height=10.3),

    fontHeight=0.4,
    numberFontSize=4,
    numberFont="C:/Windows/Fonts/arialbd.ttf",
)

document = FreeCAD.newDocument('1822PNW')

def createTileBoard(*tileNumbers) -> MultiColourFuser:
    imageFactory = Images(hexImageDimensions, document)
    condensedBoard = CondensedBoard(gridDimensions, int(len(tileNumbers) / 2))
    return condensedBoard.createTileBoard(imageFactory, *tileNumbers)

exportItems = [
    # ExportObject("tile-tray1-x2", lambda: createTileBoard(58, 3, 4, 4, 6, 5, 7, 57, 8, 8, 8, 8, 9, 9, 9, 9)),
    # ExportObject("tile-tray2", lambda: createTileBoard(144, 143, 142, 141, 15, 15, 619, 619, 80, 14, 81, 81, 82, 82, 83, 83)),
    # ExportObject("tile-tray3", lambda: createTileBoard("X5", "X10", 769, 767, 63, 768, 611, 611, 546, 545, 544, 544, 622, 405, 207, 208)),
    # ExportObject("tile-tray4", lambda: createTileBoard("X11", "X16", 895, 51, 169, 60, None, "X17", "PNW3", None, "PNW4", "PNW5", "PNW1", "PNW2", "P1", "P2")),
    # ExportObject("marker-box", lambda: MarkerBox(markerBoxDimensions, document).createBox()),
    # ExportObject("marker-lid", lambda: MarkerBox(markerBoxDimensions, document).createLid()),
    # ExportObject("card-box", lambda: CardBox(cardBoxDimensions).createBox()),
    ExportObject("cube-box", lambda: CubeBox(cubeBoxDimensions).createBox()),
    # ExportObject("cube-lid", lambda: CubeBox(cubeBoxDimensions).createLid()),
    # ExportObject("company-box-x7", lambda: CompanyBox(companyBoxDimensions).createBox()),
    # ExportObject("tile-lid-x5", lambda: CondensedBoard(gridDimensions, 8).createLid())
]



FreeCAD.Gui.activeDocument().activeView().viewIsometric()
# FreeCAD.Gui.activeDocument().activeView().viewLeft()
# FreeCAD.Gui.activeDocument().activeView().viewFront()
# FreeCAD.Gui.activeDocument().activeView().viewTop()
# FreeCAD.Gui.activeDocument().activeView().viewBottom()
# FreeCAD.Gui.runCommand('Std_DrawStyle', 6)


exporter = Exporter("D:\\projects\\3d\\FreeCAD\\models\\1822 PNW", *exportItems)

exporter.show(10)
# exporter.export(0)
# exporter.publish()
