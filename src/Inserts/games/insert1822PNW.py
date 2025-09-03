import FreeCAD
from FreeCAD import Vector

from Inserts import company, charters, cardbox
from Inserts.cardbox import CardBox
from Inserts.charters import CharterBox
from Inserts.common.colours import Colour, MultiColourFuser
from Inserts.common.smartbox import Side
from Inserts.company import CompanyBox, CylinderObjectSet
from Inserts.hex.condensed import CondensedBoard
from Inserts.hex.configuration import GridDimensions, HexTileEdges
from Inserts.hex.images import HexImageDimensions, Images
from Inserts.lidbox import LidDimensions

gridDimensions = GridDimensions(
    hexWidth=28,
    pinWidth=3.5,
    pinLength=6,
    pinRadius=1,
    pinHeight=8.5,
    floorThickness=1.6,
    ceilingThickness=0.8,
    ceilingLedgeThickness=1.2,
    ceilingLedgeDelta=0.4,
    adjacentDistance=1.2,
    magnetDiameter=3,
    magnetHeightFloor=3,
    magnetHeightCeiling=2,
    extruderWidth=0.42,
    maxRowsPerMagnet=4
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

charterBoxDimensions = charters.Dimensions(
    lid=LidDimensions(
        lidSlideInDirection=Side.S,
        lidLength=127,
        lidWidth=190.8,
        lidHeight=3.5,
        lidGap=0,
        lidWidthWallThickness=1.2,
        lidLengthWallThickness=0.8,
        aboveLidHeight=1.2,
        simplify=True,
        lidEntranceSizeMultiplier=1.02,
        aboveLidSlideCoefficient=0.5,
        supportLengthMultiplier=0.3
    ),

    wallThickness=6,
    floorHeight=0.8,

    markers=CylinderObjectSet(diameter=13.4, height=7),
    stations=CylinderObjectSet(diameter=10.95, height=10.3),

    fontHeight=1.2,
    numberSpace=7,
    numberFontSize=4,
    cylinderDistanceY=4,
    numberFont="C:/Windows/Fonts/arialbd.ttf",
    # numberFont="C:/Windows/Fonts/osifont-lgpl3fe.ttf"

    playerCubeSpaceWidth=9,
    timberCubeSpaceWidth=55,
    playerCubeSpaceDistanceSides=8,
    playerCubeSpaceLength=49,
    cubeSpaceAngle=30,
    cubeSpaceDepth=4
)

cardBoxDimensions = cardbox.CardBoxDimensions(
    # length=210,
    # width=125,
    # height=30,
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

def createYellowTileBoard() -> MultiColourFuser:
    condensedBoard = CondensedBoard(gridDimensions, 8)
    imageFactory = Images(hexImageDimensions)
    boardFuser = condensedBoard.createBoard().translate(Vector(0, 0, hexImageDimensions.imageHeight - gridDimensions.floorThickness))

    multiFuser = MultiColourFuser()

    multiFuser.fuseAll(imageFactory.createGentleTown(Colour.YELLOW, HexTileEdges.SW).translate(gridDimensions.getHexCentre(0, 0)))
    multiFuser.fuseAll(imageFactory.createSharpTown(Colour.YELLOW, HexTileEdges.SW).translate(gridDimensions.getHexCentre(0, 1)))

    for column in range(2):
        multiFuser.fuseAll(imageFactory.createStraightTown(Colour.YELLOW, HexTileEdges.SW).translate(gridDimensions.getHexCentre(1, column)))

    multiFuser.fuseAll(imageFactory.createCity(Colour.YELLOW, HexTileEdges.SW, HexTileEdges.E).translate(gridDimensions.getHexCentre(2, 0)))
    multiFuser.fuseAll(imageFactory.createCity(Colour.YELLOW, HexTileEdges.SW, HexTileEdges.SE).translate(gridDimensions.getHexCentre(2, 1)))

    multiFuser.fuseAll(imageFactory.createSharp(Colour.YELLOW, HexTileEdges.SW).translate(gridDimensions.getHexCentre(3, 0)))
    multiFuser.fuseAll(imageFactory.createCity(Colour.YELLOW, HexTileEdges.SW, HexTileEdges.NE).translate(gridDimensions.getHexCentre(3, 1)))

    for row in [4, 5]:
        for column in range(2):
            multiFuser.fuseAll(imageFactory.createGentle(Colour.YELLOW, HexTileEdges.SW).translate(gridDimensions.getHexCentre(row, column)))

    for row in [6, 7]:
        for column in range(2):
            multiFuser.fuseAll(imageFactory.createStraight(Colour.YELLOW, HexTileEdges.SW).translate(gridDimensions.getHexCentre(row, column)))

    multiFuser.common(boardFuser.getResult())
    boardFuser.cut(multiFuser.getResult())
    multiFuser.fuseAll(boardFuser)
    return multiFuser

def createCompanyBox() -> MultiColourFuser:
    companyBox = CompanyBox(companyBoxDimensions)
    return companyBox.createBox()

def createCharterBox(document: FreeCAD.Document) -> MultiColourFuser:
    charterBox = CharterBox(charterBoxDimensions, document)
    return charterBox.createBox()

def createCardBox() -> MultiColourFuser:
    cardBox = CardBox(cardBoxDimensions)
    return cardBox.createBox()

# ------------------ TESTING STUFF -----------------

def createImage():
    imageFactory = Images(hexImageDimensions)
    sample = imageFactory.createGentleTown(Colour.YELLOW,HexTileEdges.NE)
    sample.show()

def createBoard():
    condensedBoard = CondensedBoard(gridDimensions, 8)
    # condensedBoard.createBoard().show()
    condensedBoard.createLid()

