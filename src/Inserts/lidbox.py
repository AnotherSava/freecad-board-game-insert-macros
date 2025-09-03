import Part
from FreeCAD import Vector

from Inserts.common.fuser import Fuser
from Inserts.common.pencil import Pencil
from Inserts.common.smartbox import SmartBox
from Inserts.common.geometry import Side
from dataclasses import dataclass

@dataclass
class LidDimensions:
    lidSlideInDirection: Side
    lidLength: float
    lidWidth: float
    lidHeight: float
    lidGap: float
    lidWidthWallThickness: float
    lidLengthWallThickness: float
    aboveLidHeight: float
    lidEntranceSizeMultiplier: float
    aboveLidSlideCoefficient: float
    supportLengthMultiplier: float = 0
    simplify: bool = False
    supportThickness: float = None

    def __post_init__(self):
        self.lidWidthFront = self.lidWidth * self.lidEntranceSizeMultiplier
        self.aboveLidLength = self.lidLength * self.aboveLidSlideCoefficient + self.lidLengthWallThickness
        self.supportLength = self.lidLength * self.supportLengthMultiplier

    def getLidSlidingLength(self):
        return self.lidLength if self.lidSlideInDirection in [Side.E, Side.W] else self.lidWidth

    def getLidFrontSideLength(self):
        return self.lidWidth if self.lidSlideInDirection in [Side.E, Side.W] else self.lidLength

    def getLidBackSideLength(self):
         return self.getLidFrontSideLength() * self.lidEntranceSizeMultiplier

    def getFrontWallThickness(self):
        return self.lidLengthWallThickness if self.lidSlideInDirection in [Side.E, Side.W] else self.lidWidthWallThickness

    def getSideWallThickness(self):
        return self.lidWidthWallThickness if self.lidSlideInDirection in [Side.E, Side.W] else self.lidLengthWallThickness

    def getLidBackSideCenter(self):
        match self.lidSlideInDirection:
            case Side.S:
                return Vector(self.getSideWallThickness() + self.getLidBackSideLength() / 2, 0)
            case Side.N:
                return Vector(self.getSideWallThickness() + self.getLidBackSideLength() / 2, self.getFrontWallThickness() + self.getLidSlidingLength())
            case Side.W:
                return Vector(0, self.getSideWallThickness() + self.getLidBackSideLength() / 2)
            case Side.E:
                return Vector(self.getFrontWallThickness() + self.getLidSlidingLength(), self.getSideWallThickness() + self.getLidBackSideLength() / 2)

        raise ValueError(f"Unexpected side: ${self.lidSlideInDirection}")

@dataclass
class LidBoxDimensions:
    lid: LidDimensions

    wallThickness: float
    floorHeight: float

    def getBoxLength(self):
        if self.lid.lidSlideInDirection in [Side.E, Side.W]:
            return self.lid.lidLength + self.lid.lidLengthWallThickness
        else:
            return self.lid.lidLength * self.lid.lidEntranceSizeMultiplier + self.lid.lidLengthWallThickness * 2

    def getBoxWidth(self):
        if self.lid.lidSlideInDirection in [Side.S, Side.N]:
            return self.lid.lidWidth + self.lid.lidWidthWallThickness
        else:
            return self.lid.lidWidth * self.lid.lidEntranceSizeMultiplier + self.lid.lidWidthWallThickness * 2

    def getInnerWidth(self) -> float:
        if self.lid.lidSlideInDirection in [Side.S, Side.N]:
            return self.getBoxWidth()
        else:
            return self.getBoxWidth() - 2 * self.wallThickness

    def getInnerLength(self):
        if self.lid.lidSlideInDirection in [Side.E, Side.W]:
            return self.getBoxLength()
        else:
            return self.getBoxLength() - 2 * self.wallThickness

    def getInnerLocation(self) -> Vector:
        z = self.getBoxHeight() - self.getInnerHeight()

        if self.lid.lidSlideInDirection in [Side.E, Side.W]:
            return Vector(0, self.wallThickness, z)
        else:
            return Vector(self.wallThickness, 0, z)

    def getRecessDepth(self):
        return self.getMaxObjectsHeight() - self.getMinObjectsVisibleHeight()

    def getInnerHeight(self):
        return self.lid.aboveLidHeight + self.lid.lidHeight + self.lid.lidGap + self.getMinObjectsVisibleHeight()

    def getBoxHeight(self):
        return self.floorHeight + self.getRecessDepth() + self.getInnerHeight()

# Box with a sliding lid
class SlidingLidBox(SmartBox):
    def __init__(self, dimensions: LidBoxDimensions):
        super().__init__(dimensions.getBoxLength(), dimensions.getBoxWidth(), dimensions.getBoxHeight())
        self.dimensions = dimensions
        self.box = self.createBox()

    def getLidZ(self) -> float:
        return self.dimensions.getBoxHeight() - self.dimensions.lid.lidHeight - self.dimensions.lid.aboveLidHeight

    def createBox(self) -> Part.Solid:
        outerBox = Part.makeBox(self.dimensions.getBoxLength(), self.dimensions.getBoxWidth(), self.dimensions.getBoxHeight())

        # Create inner cavity
        innerBox = SmartBox(self.dimensions.getInnerLength(), self.dimensions.getInnerWidth(), self.dimensions.getInnerHeight())
        innerBox.baseVector(self.dimensions.getInnerLocation())

        lid = self.createLid()
        lid.translate(Vector(0, 0, self.getLidZ()))

        box = outerBox.cut(innerBox.box).cut(lid)
        if self.dimensions.lid.supportThickness:
            box = box.fuse(self.createLidSupport())

        return box

    def createLidSupport(self) -> Part.Solid:
        supportHeight = self.dimensions.getInnerHeight() - self.dimensions.lid.lidHeight - self.dimensions.lid.aboveLidHeight

        pencil = Pencil(Vector(-self.dimensions.lid.supportThickness / 2, 0, self.dimensions.floorHeight + self.dimensions.getRecessDepth()))
        pencil.arcWithRadius(supportHeight, -90, -90)
        pencil.right(self.dimensions.lid.supportLength - supportHeight)
        pencil.down(supportHeight)

        return self.orientBasedOnLid(pencil.extrudeX(self.dimensions.lid.supportThickness))

    def orientBasedOnLid(self, solid: Part.Solid) -> Part.Solid:
        return solid.rotate(Vector(), Vector(0, 0, 1), self.dimensions.lid.lidSlideInDirection.value).translate(self.dimensions.lid.getLidBackSideCenter())

    def createLid(self):
        fuser = Fuser(self.createBottomLid())

        if not self.dimensions.lid.simplify:
            fuser.fuse(self.createTopLid()).fuse(self.createTopLidBevel())

        return self.orientBasedOnLid(fuser.getResult())

    def createBottomLid(self):
        pencil = Pencil(Vector(-self.dimensions.lid.getLidBackSideLength() / 2 - self.dimensions.lid.getSideWallThickness(), 0, 0))
        pencil.arcWithRadius(self.dimensions.lid.getSideWallThickness(), 0, 90)
        pencil.jumpFromStart(Vector(self.dimensions.lid.getSideWallThickness() + (self.dimensions.lid.getLidBackSideLength() - self.dimensions.lid.getLidFrontSideLength()) / 2, self.dimensions.lid.getLidSlidingLength(), 0))
        pencil.right(self.dimensions.lid.getLidFrontSideLength())
        pencil.jumpFromStart(Vector(self.dimensions.lid.getLidBackSideLength() + self.dimensions.lid.getSideWallThickness(), self.dimensions.lid.getSideWallThickness()))
        pencil.arcWithRadius(self.dimensions.lid.getSideWallThickness(), -90, 90)

        height = self.dimensions.lid.lidHeight
        if self.dimensions.lid.simplify:
            height += self.dimensions.lid.aboveLidHeight

        return pencil.extrude(height)

    def createTopLid(self):
        sideLength = self.dimensions.lid.getLidSlidingLength() * (1 - self.dimensions.lid.aboveLidSlideCoefficient)
        frontLength = (self.dimensions.getBoxWidth() if self.dimensions.lid.lidSlideInDirection in [Side.E, Side.W] else self.dimensions.getBoxLength()) - self.dimensions.wallThickness * 2

        pencil = Pencil(Vector(-frontLength / 2 - self.dimensions.wallThickness, 0, self.dimensions.lid.lidHeight))
        pencil.up(sideLength)
        pencil.arcWithRadius(self.dimensions.wallThickness, 0, 90)
        pencil.right(frontLength)
        pencil.arcWithRadius(self.dimensions.wallThickness, -90, 90)
        pencil.down(sideLength)

        return pencil.extrude(self.dimensions.lid.aboveLidHeight)

    def createTopLidBevel(self):
        # bevelBackSideLength = self.dimensions.lid.getLidBackSideLength()
        bevelBackSideLength = self.dimensions.lid.getLidFrontSideLength() * (1 - self.dimensions.lid.aboveLidSlideCoefficient) + self.dimensions.lid.getLidBackSideLength() * self.dimensions.lid.aboveLidSlideCoefficient

        sideLength = self.dimensions.lid.getLidSlidingLength() * (1 - self.dimensions.lid.aboveLidSlideCoefficient)
        pencil = Pencil(Vector(-bevelBackSideLength / 2, 0, self.dimensions.lid.lidHeight))
        pencil.up(self.dimensions.lid.aboveLidHeight)
        pencil.right(sideLength)
        pencil.arc(Vector(self.dimensions.wallThickness, -self.dimensions.lid.aboveLidHeight), 10)
        return pencil.extrudeX(bevelBackSideLength)
