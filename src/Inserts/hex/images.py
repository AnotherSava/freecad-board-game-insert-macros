from math import tan, cos, sin, radians, pi

from Inserts.common.smartbox import SmartBox
from typing import Callable

import Part
from FreeCAD import Vector

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuseAll
from Inserts.common.geometry import createWire
from Inserts.common.pencil import Pencil
from Inserts.hex.configuration import HexTileVertices, HexTileEdges, HexTileManifestEdges
from dataclasses import dataclass


@dataclass
class Hex:
    width: float
    centre: Vector

    def getSide(self):
        return self.width * tan(radians(30))

    def getRadius(self):
        return self.width / 2 / cos(radians(30))

    def getVector(self, vertex: HexTileVertices) -> Vector:
        return vertex.getVector(self.width) + self.centre


@dataclass
class HexImageDimensions:
    imageHeight: float
    hexWidth: float
    railWidth: float
    townBarWidth: float
    townBarLength: float
    cityDiameter: float
    townDiameter: float
    lineWidth: float
    whiteLayerHeight: float
    scale: float

    def __init__(self, imageHeight: float, hexWidth: float, railWidth: float,
                 townBarWidth: float, townBarLength: float, cityDiameter: float,
                 townDiameter: float, scale: float, lineWidth: float, whiteLayerHeight: float):
        self.imageHeight = imageHeight
        self.whiteLayerHeight = whiteLayerHeight
        self.scale = scale

        self.hexWidth = hexWidth * scale
        self.railWidth = railWidth * scale
        self.townBarWidth = townBarWidth * scale
        self.townBarLength = townBarLength * scale
        self.cityDiameter = cityDiameter * scale
        self.townDiameter = townDiameter * scale
        self.lineWidth = lineWidth * scale

        self.hex = Hex(self.hexWidth, Vector(0, 0))

    def getTotalHeight(self):
        return self.imageHeight + self.whiteLayerHeight

    def createOutline(self) -> 'HexImageDimensions':
        return HexImageDimensions(
            imageHeight = self.imageHeight,
            hexWidth = self.hexWidth,
            railWidth = self.railWidth + self.lineWidth * 2,
            townBarWidth = self.townBarWidth + self.lineWidth * 2,
            townBarLength = self.townBarLength + self.lineWidth * 2,
            cityDiameter = self.cityDiameter + self.lineWidth * 2,
            townDiameter = self.townDiameter + self.lineWidth * 2,
            scale = self.scale,
            lineWidth = self.lineWidth,
            whiteLayerHeight = self.whiteLayerHeight
        )

class BaseElementFactory:
    def __init__(self, dimensions: HexImageDimensions):
        self.dimensions = dimensions

    def alignToEdge(self, solid: Part.Solid, startEdge: HexTileEdges):
        solid.translate(Vector(-self.dimensions.hexWidth / 2, self.dimensions.railWidth / 2, 0))
        solid.rotate(Vector(0, 0), Vector(0, 0, 1), 180 + startEdge.value)
        return solid

    def createStraight(self, startEdge: HexTileEdges) -> Part.Solid:
        pencil = Pencil()
        pencil.right(self.dimensions.hexWidth)
        pencil.down(self.dimensions.railWidth)
        pencil.left(self.dimensions.hexWidth)

        return self.alignToEdge(pencil.extrude(self.dimensions.imageHeight), startEdge)

    def createStraightTown(self, startEdge: HexTileEdges) -> Part.Solid:
        pencil = Pencil()

        pencil.right((self.dimensions.hexWidth - self.dimensions.townBarLength) / 2)
        pencil.up((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2)
        pencil.right(self.dimensions.townBarLength)
        pencil.down((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2)
        pencil.right((self.dimensions.hexWidth - self.dimensions.townBarLength) / 2)

        pencil.down(self.dimensions.railWidth)

        pencil.left((self.dimensions.hexWidth - self.dimensions.townBarLength) / 2)
        pencil.down((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2)
        pencil.left(self.dimensions.townBarLength)
        pencil.up((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2)
        pencil.left((self.dimensions.hexWidth - self.dimensions.townBarLength) / 2)

        return self.alignToEdge(pencil.extrude(self.dimensions.imageHeight), startEdge)

    def createRay(self, edge: HexTileEdges) -> Part.Solid:
        pencil = Pencil()

        rayLength = self.dimensions.hexWidth / 2 + self.dimensions.railWidth / 2 * tan(radians(30))

        pencil.right(rayLength)
        pencil.down(self.dimensions.railWidth)
        pencil.left(rayLength)

        return self.alignToEdge(pencil.extrude(self.dimensions.imageHeight), edge)

    def createCircle(self, radius: float) -> Part.Solid:
        return Part.makeCylinder(radius, self.dimensions.imageHeight)

    def createCurve(self, startEdge: HexTileEdges, outsideRadius: float, angle: float) -> Part.Solid:
        pencil = Pencil()
        internalRadius = (self.dimensions.hex.getSide() - self.dimensions.railWidth) / 2 + outsideRadius
        externalRadius = (self.dimensions.hex.getSide() + self.dimensions.railWidth) / 2 + outsideRadius

        pencil.arcWithRadius(externalRadius, 180, -angle)
        pencil.draw(self.dimensions.railWidth, 180 - angle)
        pencil.arcWithRadius(internalRadius, 180 - angle, angle)

        return self.alignToEdge(pencil.extrude(self.dimensions.imageHeight), startEdge)

    def createTownCurve(self, startEdge: HexTileEdges, outsideRadius: float, angle: float) -> Part.Solid:
        pencil = Pencil()
        internalRadius = (self.dimensions.hex.getSide() - self.dimensions.railWidth) / 2 + outsideRadius
        externalRadius = (self.dimensions.hex.getSide() + self.dimensions.railWidth) / 2 + outsideRadius

        townBarExternalAngle = 180 * self.dimensions.townBarLength / externalRadius / pi
        townBarInternalAngle = 180 * self.dimensions.townBarLength / internalRadius / pi

        pencil.arcWithRadius(externalRadius, 180, -(angle - townBarExternalAngle) / 2)
        pencil.draw((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2, -angle / 2)
        pencil.draw(self.dimensions.townBarLength, -angle / 2 - 90)
        pencil.draw((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2, 180 - angle / 2)
        pencil.arcWithRadius(externalRadius, 180 - (angle + townBarExternalAngle) / 2, -(angle - townBarExternalAngle) / 2)

        pencil.draw(self.dimensions.railWidth, 180 - angle)

        pencil.arcWithRadius(internalRadius, 180 - angle, (angle - townBarInternalAngle) / 2)
        pencil.draw((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2, 180 - angle / 2)
        pencil.draw(self.dimensions.townBarLength, -angle / 2 + 90)
        pencil.draw((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2, -angle / 2)
        pencil.arcWithRadius(internalRadius, 180 - (angle - townBarExternalAngle) / 2, (angle - townBarInternalAngle) / 2)

        return self.alignToEdge(pencil.extrude(self.dimensions.imageHeight), startEdge)

    def createGentle(self, startEdge: HexTileEdges) -> Part.Solid:
        return self.createCurve(startEdge, self.dimensions.hex.getSide() / 2 / sin(radians(30)), 60)

    def createGentleTown(self, startEdge: HexTileEdges) -> Part.Solid:
        return self.createTownCurve(startEdge, self.dimensions.hex.getSide() / 2 / sin(radians(30)), 60)

    def createSharp(self, startEdge: HexTileEdges) -> Part.Solid:
        return self.createCurve(startEdge, 0, 120)

    def createSharpTown(self, startEdge: HexTileEdges) -> Part.Solid:
        return self.createTownCurve(startEdge, 0, 120)

    def createCityInternals(self):
        return self.createCircle(self.dimensions.cityDiameter / 2 - self.dimensions.lineWidth)

    def createCity(self, *edges: HexTileEdges) -> Part.Solid:
        outerCity = self.createCircle(self.dimensions.cityDiameter / 2)
        innerCity = self.createCircle(self.dimensions.cityDiameter / 2 - self.dimensions.lineWidth)

        fuser = Fuser()

        for edge in edges:
            fuser.fuse(self.createRay(edge))
        
        fuser.cut(outerCity)
        fuser.fuse(outerCity)
        fuser.cut(innerCity)

        return fuser.solid

    def createOuterDoubleCity(self, delta: float = 0) -> Part.Solid:
        fuser = Fuser()

        box = SmartBox(self.dimensions.cityDiameter + delta * 2, self.dimensions.cityDiameter + delta * 2, self.dimensions.imageHeight)
        fuser.fuse(box.translate(-box.length / 2, -box.width / 2)).rotate(Vector(), Vector(0, 0, 1), -30)
        fuser.fuse(self.createInnerDoubleCity(delta))

        return fuser.solid

    def createInnerDoubleCity(self, delta: float = 0) -> Part.Solid:
        fuser = Fuser()

        fuser.fuse(self.createCircle(self.dimensions.cityDiameter / 2 + delta).translate(Vector(-self.dimensions.cityDiameter / 2 - self.dimensions.lineWidth / 2)))
        fuser.fuse(self.createCircle(self.dimensions.cityDiameter / 2 + delta).translate(Vector(self.dimensions.cityDiameter / 2 + self.dimensions.lineWidth / 2)))

        return fuser.rotate(Vector(), Vector(0, 0, 1), -30).solid

    def createTown(self) -> Part.Solid:
        return self.createCircle(self.dimensions.townDiameter / 2)

    def createRays(self, *edges: HexTileEdges) -> Part.Solid:
        return fuseAll(self.createRay(edge) for edge in edges)

class Images:
    def __init__(self, dimensions: HexImageDimensions):
        self.dimensions = dimensions
        self.baseFactory = BaseElementFactory(dimensions)
        self.outlineFactory = BaseElementFactory(dimensions.createOutline())

    def createHex(self, height: float = None) -> Part.Solid:
        wire = createWire([self.dimensions.hex.getVector(x) for x in HexTileVertices.iterate()])
        face = Part.Face(wire)
        solid = face.extrude(Vector(0, 0, height or self.dimensions.imageHeight))
        return solid

    def createCity(self, colour: Colour, *edges: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.BLACK, self.baseFactory.createCity(*edges))

        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createCity(*edges))
        multiFuser.fuse(Colour.WHITE, self.baseFactory.createCityInternals())

        return self.putOnHex(multiFuser, colour)

    def createDoubleCity(self, colour: Colour, *edges: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.WHITE, self.baseFactory.createInnerDoubleCity())
        multiFuser.fuseUnique(Colour.BLACK, self.baseFactory.createInnerDoubleCity(self.dimensions.lineWidth))

        multiFuser.fuseUnique(Colour.WHITE, self.baseFactory.createOuterDoubleCity())
        multiFuser.fuseUnique(Colour.BLACK, self.baseFactory.createOuterDoubleCity(self.dimensions.lineWidth))

        multiFuser.fuseUnique(Colour.BLACK, self.baseFactory.createRays(*edges))
        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createRays(*edges))

        multiFuser.fuseUnique(Colour.WHITE, self.baseFactory.createOuterDoubleCity(self.dimensions.lineWidth * 2))

        return self.putOnHex(multiFuser, colour)

    def createTown(self, colour: Colour, *edges: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.BLACK, self.baseFactory.createTown())
        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createTown())
        multiFuser.fuseUnique(Colour.BLACK, self.baseFactory.createRays(*edges))
        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createRays(*edges))

        return self.putOnHex(multiFuser, colour)

    def createRays(self, colour: Colour, *edges: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.BLACK, self.baseFactory.createRays(*edges))
        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createRays(*edges))

        return self.putOnHex(multiFuser, colour)

    def createSimpleTile(self, colour: Colour, trackMethod: Callable, startEdge: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.BLACK, trackMethod(self.baseFactory, startEdge))
        multiFuser.fuseUnique(Colour.WHITE, trackMethod(self.outlineFactory, startEdge))

        return self.putOnHex(multiFuser, colour)

    def putOnHex(self, fuser: MultiColourFuser, colour: Colour) -> MultiColourFuser:
        fuser.fuseUnique(colour, self.createHex())

        hexSolid = self.createHex(self.dimensions.whiteLayerHeight)
        hexSolid.translate(Vector(0, 0, -self.dimensions.whiteLayerHeight))
        fuser.fuse(Colour.WHITE, hexSolid)

        return fuser

    def createTile(self, number: int) -> MultiColourFuser:
        match number:
            case 3: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createSharpTown, HexTileManifestEdges.S)
            case 4: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createStraightTown, HexTileManifestEdges.S)
            case 5: return self.createCity(Colour.YELLOW, HexTileManifestEdges.S, HexTileManifestEdges.SE)
            case 6: return self.createCity(Colour.YELLOW, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 7: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createSharp, HexTileManifestEdges.S)
            case 8: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createGentle, HexTileManifestEdges.S)
            case 9: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createStraight, HexTileManifestEdges.S)
            case 58: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createGentleTown, HexTileManifestEdges.S)
            case 57: return self.createCity(Colour.YELLOW, HexTileManifestEdges.S, HexTileManifestEdges.N)

            case 14: return self.createDoubleCity(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.SE)
            case 15: return self.createDoubleCity(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 80: return self.createRays(Colour.GREEN, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 143: return self.createTown(Colour.GREEN, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 81: return self.createRays(Colour.GREEN, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 144: return self.createTown(Colour.GREEN, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 82: return self.createRays(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 141: return self.createTown(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 83: return self.createRays(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.S, HexTileManifestEdges.NW)
            case 142: return self.createTown(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.S, HexTileManifestEdges.NW)
            case 619: return self.createDoubleCity(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.NE, HexTileManifestEdges.S)

        raise(f"Invalid tile number: {number}")
