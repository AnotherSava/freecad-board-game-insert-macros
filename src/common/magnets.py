import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Tuple

import FreeCAD
import Part
from FreeCAD import Vector

from common.fuser import Fuser
from common.pencil import Pencil
from constants import nozzleSize, tolerance, magnet3Diameter, magnet3x3height, magnet2Diameter, magnet2x3height, magnet3x2height

wideningCoefficient = 1.1
wideningPartHeightCoefficient = 1 / 3


class CornerAngles(IntEnum):
    NW = 45
    SW = 135
    SE = -135
    NE = -45

    @classmethod
    def allBut(cls, excludedAngle: 'CornerAngles') -> list['CornerAngles']:
        return [angle for angle in cls if angle != excludedAngle]


@dataclass
class RampDetails:
    direction: int
    centreAdjustment: float # [-1..1] If ramp is facing up, -1 = leftmost point of the base diameter, 1 = rightmost point
    lengthMultiplier: float # times base radius
    wallThickness: float # thickness of the wall ramp is attached to


@dataclass
class MagnetDimensions:
    diameter: float
    height: float
    thinnestWall: float
    magnetCount: int = 1

    def withWallLoops(self, wallLoops: int):
        self.thinnestWall = nozzleSize * wallLoops
        return self

    def withDiameterDelta(self, diameterDelta: int):
        self.diameter += diameterDelta
        return self

    def withMagnetCount(self, count: int) -> 'MagnetDimensions':
        self.magnetCount = count
        return self

    def getBaseRadius(self):
        return self.getHoleRadius() + self.thinnestWall

    def getWiderBaseRadius(self):
        return self.getWiderHoleRadius() + self.thinnestWall

    def getHoleRadius(self):
        return self.diameter / 2

    def getWiderHoleRadius(self):
        return self.diameter / 2 * wideningCoefficient

    def getRadiusWideningAmount(self):
        return self.getWiderBaseRadius() - self.getBaseRadius()

    def getWideningHeight(self):
        return self.height * wideningPartHeightCoefficient


MAGNET_3x3 = MagnetDimensions(
    diameter=magnet3Diameter + tolerance,
    height=magnet3x3height,
    thinnestWall=nozzleSize
)

MAGNET_3x2 = MagnetDimensions(
    diameter=magnet3Diameter + tolerance,
    height=magnet3x2height,
    thinnestWall=nozzleSize
)

MAGNET_2x3 = MagnetDimensions(
    diameter=magnet2Diameter + tolerance,
    height=magnet2x3height,
    thinnestWall=nozzleSize
)


@dataclass
class MagnetDetails:
    centre: Vector
    cornerAngle: list[int] = None # base will have a corner at a specific direction (CCW from Y axis) rather than be round; if (0, 90, 180 or 270), will have two adjacent corners
    cornerAngleCut: list[int] = None # same as cornerAngle, but to cut from foundation and leave a rounded base
    cornerHeight: float = None
    ramp: RampDetails = None
    adjacentToWidening: bool = True
    holeVector: Vector = None


def getWidestRadius(magnetDiameter: float, delta: float = 0):
    return magnetDiameter / 2 * wideningCoefficient + delta

def createHalfCurve(dimensions: MagnetDimensions, details: MagnetDetails, baseHeight: float) -> Fuser:
    fuser = Fuser()
    for side in [-1, 1]:
        radius = dimensions.getWiderBaseRadius() if details.adjacentToWidening else dimensions.getBaseRadius()
        rampLength = radius * details.ramp.lengthMultiplier
        height = baseHeight if details.adjacentToWidening else baseHeight - dimensions.getWideningHeight()
        d = radius * math.sin(details.ramp.centreAdjustment * math.pi / 2) - details.ramp.wallThickness * (details.ramp.centreAdjustment - side) / 2
        pencil = Pencil(Vector(d, rampLength))
        if details.ramp.centreAdjustment != side:
            r = (rampLength * rampLength + d * d - dimensions.getBaseRadius() * dimensions.getBaseRadius()) / (2 * dimensions.getBaseRadius() - 2 * d * side)
            rampAngle = math.asin(rampLength / (r + dimensions.getBaseRadius()))
            pencil.arcWithRadius(r, -90 * side, math.degrees(rampAngle) * side)
            pencil.jumpTo(Vector(d, 0))
            fuser.fuse(pencil.extrude(height))

    return orient(fuser.rotateZ(details.ramp.direction), details)

def createMagnetBaseCorners(dimensions: MagnetDimensions, baseHeight: float, angles: list[int] | None, details: MagnetDetails) -> Fuser:
    fuser = Fuser()

    height = details.cornerHeight or baseHeight if details.adjacentToWidening else baseHeight - dimensions.getWideningHeight()
    for angle in angles or []:
        fuser.fuse(Part.makeBox(dimensions.getBaseRadius(), dimensions.getBaseRadius(), height).rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle + 45))

    return orient(fuser.translate(Vector(0, 0, baseHeight - height)), details)

def createMagnetBase(dimensions: MagnetDimensions, baseHeight: float, details: MagnetDetails) -> Fuser:
    fuser = orient(createWideningCylinder(dimensions, True, baseHeight), details)

    if details.ramp:
        fuser.fuse(createHalfCurve(dimensions, details, baseHeight))

    baseCorners = createMagnetBaseCorners(dimensions, baseHeight, details.cornerAngle, details)

    return fuser.fuse(baseCorners)

def createWideningCylinder(dimensions: MagnetDimensions, base: bool, fixedHeight: float = None) -> Fuser:
    radius = dimensions.getBaseRadius() if base else dimensions.getHoleRadius()
    widerRadius = dimensions.getWiderBaseRadius() if base else dimensions.getWiderHoleRadius()

    narrowPartHeight = (fixedHeight or dimensions.height * dimensions.magnetCount) - dimensions.getWideningHeight()
    assert narrowPartHeight > 0, f"fixedHeight: {fixedHeight}, magnetHeight: {dimensions.height}, count: {dimensions.magnetCount}, widePartHeight: {dimensions.getWideningHeight()}"

    widePart = Part.makeCone(widerRadius, radius, dimensions.getWideningHeight())

    narrowPart = Part.makeCylinder(radius, narrowPartHeight)
    narrowPart.translate(Vector(0, 0, dimensions.getWideningHeight()))

    return Fuser(narrowPart, widePart)

def orient(fuser: Fuser, details: MagnetDetails) -> Fuser:
    if details.holeVector and details.holeVector.normalize().isEqual(Vector(0, 0, -1), 1e-6):
        fuser.mirrorZ()
    elif details.holeVector:
        rotation = FreeCAD.Rotation(Vector(0, 0, 1), details.holeVector)
        fuser.rotate(Vector(), rotation.Axis, math.degrees(rotation.Angle))

    return fuser.translate(details.centre)

def adjust(height: float, mirrorZ: bool = False, *args: Fuser) -> Tuple[Fuser, Fuser, Fuser]:
    for element in args:
        if element is not None:
            if mirrorZ:
                element.mirrorZ()
            element.translate(Vector(0, 0, height))

    return args

def createMagnetHolders(dimensions: MagnetDimensions, baseHeight: float, magnetDetails: Iterable[MagnetDetails]) -> Tuple[Fuser, Fuser, Fuser]:
    magnetDetailsList = list(magnetDetails)
    holes = createMagnetHoles(dimensions, magnetDetailsList)
    bases, cornersToCut = createMagnetBases(dimensions, baseHeight, magnetDetailsList)

    return bases, holes, cornersToCut

def createMagnetBases(dimensions: MagnetDimensions, baseHeight: float, magnetDetailsList: Iterable[MagnetDetails]) -> Tuple[Fuser, Fuser]:
    bases = Fuser(createMagnetBase(dimensions, baseHeight, magnetDetails) for magnetDetails in magnetDetailsList)
    cornersToCut = Fuser(createMagnetBaseCorners(dimensions, baseHeight, magnetDetails.cornerAngleCut, magnetDetails) for magnetDetails in magnetDetailsList)
    return bases, cornersToCut

def createMagnetHole(dimensions: MagnetDimensions, base: bool, details: MagnetDetails) -> Fuser:
    return orient(createWideningCylinder(dimensions, base), details)

def createMagnetHoles(dimensions: MagnetDimensions, magnetDetailsList: Iterable[MagnetDetails]) -> Fuser:
    return Fuser(createMagnetHole(dimensions, False, magnetDetails) for magnetDetails in magnetDetailsList)
