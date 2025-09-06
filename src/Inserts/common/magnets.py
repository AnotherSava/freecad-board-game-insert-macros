import math
from math import tan

from Inserts.common.pencil import Pencil
from dataclasses import dataclass
from typing import Iterable

import Part
from FreeCAD import Vector

from Inserts.common.fuser import Fuser
from Inserts.common.geometry import Side

wideningCoefficient = 1.05

@dataclass
class MagnetDetails:
    centre: Vector
    rampDirection: Side = None
    rampCentreAdjustment: float = None # [-1..1] If ramp is facing up, -1 = leftmost point of the base diameter, 1 = rightmost point
    rampLengthMultiplier: float = None # times base radius
    wallThickness: float = None # thickness of the wall ramp is attached to

def getWidestRadius(magnetDiameter: float, delta: float):
    return magnetDiameter / 2 * wideningCoefficient + delta

def createMagnetBase(magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, baseHeight: float, delta: float) -> Part.Solid:
    baseRadius = magnetDiameter / 2 + delta
    wideBaseRadius = (magnetDiameter / 2) * wideningCoefficient + delta

    remainingBase = Part.makeCylinder(baseRadius, baseHeight - magnetHeight)
    remainingBase.translate(Vector(0, 0, magnetHeight))
    magnetBase = Part.makeCone(wideBaseRadius, baseRadius, magnetHeight)
    solid = magnetBase.fuse(remainingBase)
    if magnetOnTop:
        solid.rotate(Vector(0, 0, baseHeight / 2), Vector(0, 1, 0), 180)
    return solid

def createMagnetBaseWithRamp(magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, baseHeight: float, delta: float, details: MagnetDetails) -> Part.Solid:
    baseRadius = magnetDiameter / 2 + delta
    wideBaseRadius = (magnetDiameter / 2) * wideningCoefficient + delta

    remainingBase = Part.makeCylinder(baseRadius, baseHeight - magnetHeight)
    remainingBase.translate(Vector(0, 0, magnetHeight))
    magnetBase = Part.makeCone(wideBaseRadius, baseRadius, magnetHeight)

    solid = magnetBase.fuse(remainingBase)
    if magnetOnTop:
        solid.rotate(Vector(0, 0, baseHeight / 2), Vector(0, 1, 0), 180)

    if details.rampDirection is not None:
        ramp = createHalfCurve(baseRadius, details, wideBaseRadius, baseHeight)
        ramp.rotate(Vector(0, 0), Vector(0, 0, 1), details.rampDirection.value)
        # ramp.translate(details.centre)
        # Part.show(ramp)
        solid = solid.fuse(ramp)

    solid.translate(details.centre)
    return solid


def createHalfCurve(baseRadius: float, details: float, wideBaseRadius: float, baseHeight: float):
    fuser = Fuser()
    for side in [-1, 1]:
        rampLength = baseRadius * details.rampLengthMultiplier
        d = wideBaseRadius * math.sin(details.rampCentreAdjustment * math.pi / 2) - details.wallThickness * (details.rampCentreAdjustment - side) / 2
        pencil = Pencil(Vector(d, rampLength))
        if details.rampCentreAdjustment != side:
            r = (rampLength * rampLength + d * d - baseRadius * baseRadius) / (2 * baseRadius - 2 * d * side)
            rampAngle = math.asin(rampLength / (r + baseRadius))
            print(f"angle: {math.degrees(rampAngle)}")
            pencil.arcWithRadius(r, -90 * side, math.degrees(rampAngle) * side)
            pencil.jumpTo(Vector(d, 0))
            fuser.fuse(pencil.extrude(baseHeight))
    return fuser.getResult()


def createMagnetHole(magnetDiameter: float, magnetHeight: float, baseHeight: float, magnetOnTop: bool) -> Part.Solid:
    baseRadius = magnetDiameter / 2
    wideBaseRadius = (magnetDiameter / 2) * wideningCoefficient

    hole = Part.makeCone(wideBaseRadius, baseRadius, magnetHeight)

    if magnetOnTop:
        hole.rotate(Vector(0, 0, baseHeight / 2), Vector(0, 1, 0), 180)

    return hole

def createMagnetHolders(magnetDiameter: float, magnetHeight: float, magnetOnTop: bool, baseHeight: float, delta: float, magnetDetailsList: Iterable[MagnetDetails]) -> (Part.Solid, Part.Solid):
    holeFuser = Fuser()
    baseFuser = Fuser()
    for magnetDetails in magnetDetailsList:
        hole = createMagnetHole(magnetDiameter, magnetHeight, baseHeight, magnetOnTop)
        hole.translate(magnetDetails.centre)
        holeFuser.fuse(hole)

        baseFuser.fuse(createMagnetBaseWithRamp(magnetDiameter, magnetHeight, magnetOnTop, baseHeight, delta, magnetDetails))

    return baseFuser.getResult(), holeFuser.getResult()
