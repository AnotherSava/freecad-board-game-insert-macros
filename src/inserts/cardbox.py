import Draft

from common.colours import MultiColourFuser, Colour
from common.fuser import Fuser
from common.geometry import Side, alignSeveralWithin
from common.smartbox import SmartBox
from inserts.common.lidbox import SlidingLidBox, LidBoxDimensions
from dataclasses import dataclass


@dataclass
class CardBoxDimensions(LidBoxDimensions):
    cardLength: float
    cardWidth: float
    cardCutSize: float
    majorCharterCutSize: float
    multiCutSize: float

    majorCharterLength: float
    majorCharterWidth: float

    minorCharterLength: float
    minorCharterWidth: float

    scenarioTrainsHeight: float
    privatesHeight: float
    minorsHeight: float
    ltrainsHeight: float
    trainsHeight: float
    minorChartersHeight: float
    majorChartersHeight: float
    playerOrderHeight: float

    wallWidth: float

    def __post_init__(self):
        self.length = max(self.cardLength * 3 + self.wallWidth * 4, self.minorCharterLength + self.cardWidth + self.wallWidth * 3)
        self.width = self.majorCharterWidth + self.wallWidth * 2
        self.firstLevelHeight = max(self.scenarioTrainsHeight, self.playerOrderHeight)
        self.secondLevelHeight = max(self.ltrainsHeight, self.minorChartersHeight, self.privatesHeight)
        self.height = self.wallWidth + self.firstLevelHeight + self.minorsHeight + self.majorChartersHeight + self.wallWidth

        self.lid.lidLengthWallThickness = max(self.lid.lidLengthWallThickness, self.cardLength * 3 + self.wallWidth * 4 - self.lid.lidLength, self.cardWidth + self.minorCharterLength + self.wallWidth * 3 - self.lid.lidLength)

    def getMaxObjectsHeight(self):
        return self.firstLevelHeight + self.minorChartersHeight

    def getMinObjectsVisibleHeight(self):
        return 0

class CardBox:
    def __init__(self, dimensions: CardBoxDimensions):
        self.dimensions = dimensions

    def createBox(self) -> MultiColourFuser:
        box = SlidingLidBox(self.dimensions)

        fuser = Fuser()

        minorCharters = SmartBox(self.dimensions.minorCharterLength, self.dimensions.minorCharterWidth, self.dimensions.minorChartersHeight)
        minorCharters.base(self.dimensions.wallWidth, box.yTo - self.dimensions.wallThickness - minorCharters.width, box.zTo - minorCharters.height)
        minorCharters.addLedge(Side.S, self.dimensions.minorChartersHeight)
        fuser.fuse(minorCharters)

        # bottom row
        playerOrder = SmartBox(self.dimensions.cardLength, self.dimensions.cardWidth, self.dimensions.playerOrderHeight)
        playerOrder.base(minorCharters.x, minorCharters.yTo - playerOrder.width, minorCharters.z - playerOrder.height)
        playerOrder.addCut(Side.W, self.dimensions.cardCutSize, self.dimensions.wallWidth, box.height)
        fuser.fuse(playerOrder)

        scenarioTrains = SmartBox(self.dimensions.cardLength, self.dimensions.cardWidth, self.dimensions.scenarioTrainsHeight)
        scenarioTrains.base(minorCharters.xTo - scenarioTrains.length, minorCharters.yTo - playerOrder.width, minorCharters.z - scenarioTrains.height)
        shift = (scenarioTrains.length + self.dimensions.wallWidth) / 2
        scenarioTrains.addCut(Side.N, self.dimensions.multiCutSize, self.dimensions.wallThickness, box.height, -shift)
        fuser.fuse(scenarioTrains)

        # on the front
        ltrains = SmartBox(self.dimensions.cardLength, self.dimensions.cardWidth, self.dimensions.ltrainsHeight)
        ltrains.base(alignSeveralWithin(ltrains.length, box.x, box.xTo, 0, 3, self.dimensions.wallWidth), self.dimensions.wallThickness, box.getLidZ() - ltrains.height)
        ltrains.addCut(Side.W, self.dimensions.cardCutSize, self.dimensions.wallWidth, box.height)
        ltrains.addLedge(Side.N, self.dimensions.ltrainsHeight)
        fuser.fuse(ltrains)

        minors = SmartBox(self.dimensions.cardLength, self.dimensions.cardWidth, self.dimensions.minorsHeight)
        minors.base(alignSeveralWithin(minors.length, box.x, box.xTo, 1, 3, self.dimensions.wallWidth), self.dimensions.wallThickness, box.getLidZ() - minors.height)
        minors.addLedge(Side.N, self.dimensions.minorsHeight)
        fuser.fuse(minors)

        privates = SmartBox(self.dimensions.cardLength, self.dimensions.cardWidth, self.dimensions.privatesHeight)
        privates.base(alignSeveralWithin(privates.length, box.x, box.xTo, 2, 3, self.dimensions.wallWidth), self.dimensions.wallThickness, box.getLidZ() - privates.height)
        shift = (privates.x - minors.x) / 2
        privates.addCut(Side.S, self.dimensions.multiCutSize, self.dimensions.wallThickness, box.height, -shift)
        privates.addLedge(Side.N, self.dimensions.privatesHeight)
        fuser.fuse(privates)

        # on the side
        trains = SmartBox(self.dimensions.cardWidth, self.dimensions.cardLength, self.dimensions.trainsHeight)
        trains.base(minorCharters.xTo + self.dimensions.wallWidth, box.yTo - self.dimensions.wallThickness - trains.width, box.getLidZ() - trains.height)
        shift = (self.dimensions.cardWidth - self.dimensions.getInnerWidth()) / 2
        trains.addCut(Side.E, self.dimensions.majorCharterCutSize, self.dimensions.wallWidth, box.height, shift)
        trains.addLedge(Side.S, self.dimensions.trainsHeight)
        fuser.fuse(trains)

        return MultiColourFuser(Colour.BASE, box.box).cut(fuser.solid)
