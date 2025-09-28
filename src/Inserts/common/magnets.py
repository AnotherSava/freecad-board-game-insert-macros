import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable

import Part
from FreeCAD import Vector

from Inserts.common.fuser import Fuser, fuse
from Inserts.common.pencil import Pencil
from constants import nozzleSize, tolerance, magnet3Diameter, magnet3x3height, magnet2Diameter, magnet2x3height

wideningCoefficient = 1.1
wideningPartHeightCoefficient = 1 / 3


class CornerAngles(IntEnum):
    NW = 45
    SW = 135
    SE = -135
    NE = -45


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

    def withWallLoops(self, wallLoops: int):
        self.thinnestWall = nozzleSize * wallLoops
        return self

    def withDiameterDelta(self, diameterDelta: int):
        self.diameter += diameterDelta
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

MAGNET_2x3 = MagnetDimensions(
    diameter=magnet2Diameter + tolerance,
    height=magnet2x3height,
    thinnestWall=nozzleSize
)


@dataclass
class MagnetDetails:
    centre: Vector
    count: int = 1
    cornerAngle: list[int] = None # base will have a corner at a specific direction (CCW from Y axis) rather than be round; if (0, 90, 180 or 270), will have two adjacent corners
    cornerAngleCut: list[int] = None # same as cornerAngle, but to cut from foundation and leave rounded base
    cornerHeight: float = None
    ramp: RampDetails = None
    adjacentToWidening: bool = True


def getWidestRadius(magnetDiameter: float, delta: float = 0):
    return magnetDiameter / 2 * wideningCoefficient + delta

def createHalfCurve(dimensions: MagnetDimensions, details: MagnetDetails, baseHeight: float):
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
    return fuser.solid

def createMagnetBaseCorners(dimensions: MagnetDimensions, magnetOnTop: bool, baseHeight: float, angles: list[int], details: MagnetDetails) -> Fuser:
    fuser = Fuser()
    if angles is not None:
        height = details.cornerHeight or baseHeight if details.adjacentToWidening else baseHeight - dimensions.getWideningHeight()
        fuser.fuse(Part.makeBox(dimensions.getBaseRadius(), dimensions.getBaseRadius(), height).rotate(Vector(0, 0, 0), Vector(0, 0, 1), angle + 45) for angle in angles)

    if magnetOnTop:
        fuser.translate(Vector(0, 0, -baseHeight))

    return fuser.translate(details.centre)

def createMagnetBase(dimensions: MagnetDimensions, magnetOnTop: bool, baseHeight: float, details: MagnetDetails) -> Fuser:
    fuser = Fuser()

    if details.ramp is not None:
        ramp = createHalfCurve(dimensions, details, baseHeight)
        ramp.rotate(Vector(0, 0), Vector(0, 0, 1), details.ramp.direction)
        fuser.fuse(ramp)

    if magnetOnTop:
        fuser.translate(Vector(0, 0, -baseHeight))

    base = createWideningCylinder(dimensions, True, magnetOnTop, details, baseHeight)
    baseCorners = createMagnetBaseCorners(dimensions, magnetOnTop, baseHeight, details.cornerAngle, details)

    return fuser.translate(details.centre).fuse(baseCorners, base)

def createWideningCylinder(dimensions: MagnetDimensions, base: bool, wideningOnTop: bool, details: MagnetDetails, fixedHeight: float = None) -> Part.Solid:
    radius = dimensions.getBaseRadius() if base else dimensions.getHoleRadius()
    widerRadius = dimensions.getWiderBaseRadius() if base else dimensions.getWiderHoleRadius()

    narrowPartHeight = (fixedHeight or dimensions.height * details.count) - dimensions.getWideningHeight()
    assert narrowPartHeight > 0, f"fixedHeight: {fixedHeight}, magnetHeight: {dimensions.height}, count: {details.count}, widePartHeight: {dimensions.getWideningHeight()}"

    widePart = Part.makeCone(widerRadius, radius, dimensions.getWideningHeight())
    narrowPart = Part.makeCylinder(radius, narrowPartHeight)
    narrowPart.translate(Vector(0, 0, dimensions.getWideningHeight()))

    wideningCylinder = narrowPart.fuse(widePart)

    if wideningOnTop:
        wideningCylinder.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 180)

    wideningCylinder.translate(details.centre)

    return wideningCylinder

def adjust(height: float, mirrorZ: bool = False, *args: Fuser) -> (Fuser, Fuser, Fuser):
    for element in args:
        if mirrorZ:
            element.mirrorZ()
        element.translate(Vector(0, 0, height))

    return args

def createMagnetHolders(dimensions: MagnetDimensions, magnetOnTop: bool, baseHeight: float, magnetDetails: Iterable[MagnetDetails]) -> (Fuser, Fuser, Fuser):
    magnetDetailsList = list(magnetDetails)
    holes = createMagnetHoles(dimensions, magnetOnTop, magnetDetailsList)
    bases, corners = createMagnetBases(dimensions, magnetOnTop, baseHeight, magnetDetailsList)

    for element in [holes, bases, corners]:
        if element is not None:
            element.translate(Vector(0, 0, baseHeight if magnetOnTop else 0))

    return bases, holes, corners

def createMagnetBases(dimensions: MagnetDimensions, magnetOnTop: bool, baseHeight: float, magnetDetailsList: Iterable[MagnetDetails]) -> (Fuser, Fuser):
    bases = Fuser(createMagnetBase(dimensions, magnetOnTop, baseHeight, magnetDetails) for magnetDetails in magnetDetailsList)
    corners = Fuser(createMagnetBaseCorners(dimensions, magnetOnTop, baseHeight, magnetDetails.cornerAngleCut, magnetDetails) for magnetDetails in magnetDetailsList)
    return bases, corners

def createMagnetHoles(dimensions: MagnetDimensions, magnetOnTop: bool, magnetDetailsList: Iterable[MagnetDetails]) -> Fuser:
    return Fuser(createWideningCylinder(dimensions, False, magnetOnTop, magnetDetails) for magnetDetails in magnetDetailsList)
