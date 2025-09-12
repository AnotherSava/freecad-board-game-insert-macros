import math

import FreeCAD
import Part
from FreeCAD import Vector

from Inserts import company, cardbox, cubebox, markerbox
from Inserts.cardbox import CardBox
from Inserts.common import magnets
from Inserts.common.colours import Colour, MultiColourFuser
from Inserts.common.magnets import MagnetDetails
from Inserts.common.smartbox import Side, SmartBox
from Inserts.company import CompanyBox, CylinderObjectSet
from Inserts.cubebox import CubeBox
from Inserts.hex.condensed import CondensedBoard, GridDimensions
from Inserts.hex.images import HexImageDimensions, Images
from Inserts.lidbox import LidDimensions
from Inserts.markerbox import MarkerBox

nozzleSize = 0.42
magnet3Height = 2.8
magnet2Height = 1.8

gridDimensions = GridDimensions(
    hexWidth=28,
    pinWidth=3.5,
    pinLength=6,
    pinRadius=1,
    pinHeight=10,
    floorThickness=1.6,
    ceilingThickness=0.8,
    adjacentDistance=1.2,
    magnetDiameter=3,
    magnetHeightFloor=magnet3Height,
    magnetHeightCeiling=magnet3Height,
    thinnestWall=nozzleSize * 2,
    maxRowsPerMagnet=2,
    lidHoleAngle=45,
    lidHoleMultiplier=0.8
)

hexImageDimensions = HexImageDimensions(
    imageHeight=0.32,
    hexWidth=28,
    railWidth=2,
    townBarWidth=5,
    townBarLength=1.5,
    cityDiameter=10,
    townDiameter=4,
    scale=1,
    lineWidth=0.45,
    whiteLayerHeight=0.16
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
    wallThickness=1.2,
    length=cardBoxDimensions.getBoxLength(),
    width=240 - cardBoxDimensions.getBoxWidth() - companyBoxDimensions.getBoxLength(),
    lidHeight=cardBoxDimensions.getBoxHeight() - cubeBoxHeight,
    lidHandleHeight=cardBoxDimensions.getBoxHeight() - cubeBoxHeight - 2.4,
    gapHeight=cubeSize * 2 / 3,
    holderAngle=15,
    height=cubeBoxHeight,
    playerCubeSpaceWidth=19.5,
    magnetDiameter=3.0,
    magnetHeightBox=magnet3Height,
    magnetHeightLid=magnet3Height,
    cubeSize=8,
    thinnestWall=nozzleSize * 2
)

markerBoxHeight = 7.2

markerBoxDimensions = markerbox.Dimensions(
    length=174,
    width=92,
    height=markerBoxHeight,
    lidHeight = cardBoxDimensions.getBoxHeight() - markerBoxHeight,
    ligHeightDelta = 1.6,
    lidRecessWallThickness = 0.4,
    floorHeight=0.8,
    padding=2,
    delta=nozzleSize * 2,
    magnetDiameter=3.05,
    magnetHeightBox=magnet3Height,
    magnetCountBox=2,
    magnetHeightLid=magnet3Height,
    magnetCountLid=2,
    wallThickness=1.2,
    handleRadius=2,

    markers=CylinderObjectSet(diameter=13.4, height=7),
    stations=CylinderObjectSet(diameter=10.95, height=10.3),

    fontHeight=0.4,
    numberFontSize=4,
    numberFont="C:/Windows/Fonts/arialbd.ttf",
    # numberFont="C:/Windows/Fonts/osifont-lgpl3fe.ttf"
)

def createYellowTileBoard() -> MultiColourFuser:
    return createTileBoard(58, 3, 4, 4, 6, 5, 7, 57, 8, 8, 8, 8, 9, 9, 9, 9)

def createGreenTileBoard() -> MultiColourFuser:
    return createTileBoard(144, 143, 142, 141, 15, 15, 619, 619, 80, 14, 81, 81, 82, 82, 83, 83)

def createTileBoard(*tileNumbers) -> MultiColourFuser:
    assert len(tileNumbers) % 2 == 0

    condensedBoard = CondensedBoard(gridDimensions, int(len(tileNumbers) / 2))
    imageFactory = Images(hexImageDimensions)
    boardFuser = condensedBoard.createBoard().translate(Vector(0, 0, hexImageDimensions.imageHeight - gridDimensions.floorThickness))

    multiFuser = MultiColourFuser()

    for index, number in enumerate(tileNumbers):
        multiFuser.fuseAll(imageFactory.createTile(number).translate(gridDimensions.getHexCentre(math.floor(index / 2), index % 2)))

    multiFuser.common(boardFuser.getResult())
    boardFuser.cut(multiFuser.getResult())
    multiFuser.fuseAll(boardFuser)
    return multiFuser

def createCompanyBox() -> MultiColourFuser:
    companyBox = CompanyBox(companyBoxDimensions)
    return companyBox.createBox()

def createMarkerBox(document: FreeCAD.Document) -> MultiColourFuser:
    markerBox = MarkerBox(markerBoxDimensions, document)
    return markerBox.createBox()

def createMarkerBoxLid(document: FreeCAD.Document) -> MultiColourFuser:
    markerBox = MarkerBox(markerBoxDimensions, document)
    return markerBox.createLid()

def createCardBox() -> MultiColourFuser:
    cardBox = CardBox(cardBoxDimensions)
    return cardBox.createBox()

def createCubedBox() -> MultiColourFuser:
    cubeBox = CubeBox(cubeBoxDimensions)
    return cubeBox.createBox()

def createCubedBoxLid() -> MultiColourFuser:
    cubeBox = CubeBox(cubeBoxDimensions)
    return cubeBox.createLid()

def createTileBoardLid() -> MultiColourFuser:
    condensedBoard = CondensedBoard(gridDimensions, 8)
    return condensedBoard.createLid()

# ------------------ TESTING STUFF -----------------

def createTest():
    box = SmartBox(10, 10, 7)
    box = Part.makeBox(1, 1, 1)
    bases, holes = magnets.createMagnetHolders(3.05, 3, True, 7, 1, [MagnetDetails(Vector(0, 0, 0), 2, 45)])
    base = magnets.createMagnetBase(3.05, 3, True, 7, 1, MagnetDetails(Vector(0, 0, 0), 2, 180))

    return MultiColourFuser(Colour.BASE, bases.cut(holes))
    # return MultiColourFuser(Colour.BASE, base)
    # return MultiColourFuser(Colour.BASE, box)

def createImage():
    imageFactory = Images(hexImageDimensions)
    return imageFactory.createTile(619).rotate(Vector(), Vector(0, 0, 1), 30)

