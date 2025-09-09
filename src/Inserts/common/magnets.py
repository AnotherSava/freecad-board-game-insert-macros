import math

import Part
from FreeCAD import Vector

from Inserts.common.fuser import Fuser, fuseAll
from Inserts.common.geometry import Side
from Inserts.common.pencil import Pencil
from dataclasses import dataclass
from typing import Iterable

wideningCoefficient = 1.05
wideningPartHeightCoefficient = 1 / 3

@dataclass
class MagnetDetails:
    centre: Vector
    count: int = 1
    cornerAngle: int = None # base will have a corner at a specific direction (CCW from Y axis) rather than be round
    rampDirection: Side = None
    rampCentreAdjustment: float = None # [-1..1] If ramp is facing up, -1 = leftmost point of the base diameter, 1 = rightmost point
    rampLengthMultiplier: float = None # times base radius
    wallThickness: float = None # thickness of the wall ramp is attached to


def getBaseRadius(magnetDiameter: float, delta: float = 0):
    return magnetDiameter / 2 + delta

def getWidestRadius(magnetDiameter: float, delta: float = 0):
    return magnetDiameter / 2 * wideningCoefficient + delta

def createHalfCurve(baseRadius: float, details: MagnetDetails, wideBaseRadius: float, baseHeight: float):
    fuser = Fuser()
    for side in [-1, 1]:
        rampLength = baseRadius * details.rampLengthMultiplier
        d = wideBaseRadius * math.sin(details.rampCentreAdjustment * math.pi / 2) - details.wallThickness * (details.rampCentreAdjustment - side) / 2
        pencil = Pencil(Vector(d, rampLength))
        if details.rampCentreAdjustment != side:
            r = (rampLength * rampLength + d * d - baseRadius * baseRadius) / (2 * baseRadius - 2 * d * side)
            rampAngle = math.asin(rampLength / (r + baseRadius))
            pencil.arcWithRadius(r, -90 * side, math.degrees(rampAngle) * side)
            pencil.jumpTo(Vector(d, 0))
            fuser.fuse(pencil.extrude(baseHeight))
    return fuser.solid


def createMagnetHole(magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, details: MagnetDetails) -> Part.Solid:
    return createWideningCylinder(magnetDiameter, magnetHeight, magnetOnTop, details)

def createMagnetBase(magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, baseHeight: float, delta: float, details: MagnetDetails) -> Part.Solid:

    baseRadius = getBaseRadius(magnetDiameter, delta)
    wideBaseRadius = getWidestRadius(magnetDiameter, delta)

    fuser = Fuser()

    if details.cornerAngle is not None:
        cornerBase = Part.makeBox(wideBaseRadius, wideBaseRadius, baseHeight).rotate(Vector(0, 0, 0), Vector(0, 0, 1), details.cornerAngle + 45)
        fuser.fuse(cornerBase)

    if details.rampDirection is not None:
        ramp = createHalfCurve(baseRadius, details, wideBaseRadius, baseHeight)
        ramp.rotate(Vector(0, 0), Vector(0, 0, 1), details.rampDirection.value)
        fuser.fuse(ramp)

    fuser.translate(details.centre)

    fuser.fuse(createWideningCylinder(magnetDiameter, magnetHeight, magnetOnTop, details, baseHeight, delta))

    return fuser.solid


def createWideningCylinder(magnetDiameter: float, magnetHeight: float, wideningOnTop: bool, details: MagnetDetails, fixedHeight: float = None, delta: float = 0) -> Part.Solid:
    baseRadius = getBaseRadius(magnetDiameter, delta)
    wideBaseRadius = getWidestRadius(magnetDiameter, delta)

    widePartHeight = magnetHeight * wideningPartHeightCoefficient
    narrowPartHeight = (fixedHeight or magnetHeight * details.count) - widePartHeight

    widePart = Part.makeCone(wideBaseRadius, baseRadius, widePartHeight)
    narrowPart = Part.makeCylinder(baseRadius, narrowPartHeight)
    narrowPart.translate(Vector(0, 0, widePartHeight))

    wideningCylinder = narrowPart.fuse(widePart)

    if wideningOnTop:
        wideningCylinder.rotate(Vector(0, 0, 0), Vector(0, 1, 0), 180)

    wideningCylinder.translate(details.centre)

    return wideningCylinder

def createMagnetHolders(magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, baseHeight: float, delta: float, magnetDetails: Iterable[MagnetDetails]) -> (Part.Solid, Part.Solid):
    magnetDetailsList = list(magnetDetails)
    holes = createMagnetHoles(magnetDiameter, magnetHeight, magnetOnTop, magnetDetailsList)
    bases = createMagnetBases(magnetDiameter, magnetHeight, magnetOnTop, baseHeight, delta, magnetDetailsList)

    return bases, holes

def createMagnetBases(magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, baseHeight: float, delta: float, magnetDetailsList: Iterable[MagnetDetails]) -> Part.Solid:
    return fuseAll(createMagnetBase(magnetDiameter, magnetHeight, magnetOnTop, baseHeight, delta, magnetDetails) for magnetDetails in magnetDetailsList)

def createMagnetHoles(magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, magnetDetailsList: Iterable[MagnetDetails]) -> Part.Solid:
    return fuseAll(createMagnetHole(magnetDiameter, magnetHeight, magnetOnTop, magnetDetails) for magnetDetails in magnetDetailsList)


def createCornerLocations(length: float, width: float, z: float, magnetDiameter: float, delta: float, count = 1) -> list[MagnetDetails]:
    widerDiameter = getWidestRadius(magnetDiameter, delta)
    return [
        MagnetDetails(Vector(widerDiameter, widerDiameter, z), count, 135),
        MagnetDetails(Vector(length - widerDiameter, widerDiameter, z), count, -135),
        MagnetDetails(Vector(widerDiameter, width - widerDiameter, z), count, 45),
        MagnetDetails(Vector(length - widerDiameter, width - widerDiameter, z), count, -45)
    ]
