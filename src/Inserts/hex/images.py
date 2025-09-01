from math import tan, cos, sin, radians, pi
from typing import Callable

import Part
from FreeCAD import Vector

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuse
from Inserts.common.geometry import createWire
from Inserts.common.pencil import Pencil
from Inserts.hex.configuration import HexTileVertices, HexTileEdges
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

        pencil.right(self.dimensions.hexWidth / 2)
        pencil.down(self.dimensions.railWidth)
        pencil.left(self.dimensions.hexWidth / 2)

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

        return fuser.getResult()

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

    def createBase(self, depthStart: float, depthEnd: float) -> Part.Solid:
        height = depthEnd - depthStart
        hexSolid = self.createHex(height)
        hexSolid.translate(Vector(0, 0, -depthEnd))
        return hexSolid

    def createSample(self):
        black = self.baseFactory.createStraightTown(HexTileEdges.NE)
        blackFeature = Part.show(black, "black")
        blackFeature.ViewObject.ShapeColor = (0, 0, 0)

        hexSolid = self.createHex().cut(black).fuse(self.createBase(0, 0.32))
        yellowFeature = Part.show(hexSolid, "yellow")
        yellowFeature.ViewObject.ShapeColor = (1.0, 1.0, 0.0)

    def createCity(self, colour: Colour, *edges: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.BLACK, self.baseFactory.createCity(*edges))

        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createCity(*edges))
        multiFuser.fuse(Colour.WHITE, self.baseFactory.createCityInternals())

        multiFuser.fuseUnique(colour, self.createHex())

        return multiFuser.fuseAll(self.createTile())

    def createSimpleTile(self, colour: Colour, trackMethod: Callable, startEdge: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.BLACK, trackMethod(self.baseFactory, startEdge))
        multiFuser.fuseUnique(Colour.WHITE, trackMethod(self.outlineFactory, startEdge))
        multiFuser.fuseUnique(colour, self.createHex())

        return multiFuser.fuseAll(self.createTile())

    def createStraight(self, colour: Colour, startEdge: HexTileEdges) -> MultiColourFuser:
        return self.createSimpleTile(colour, BaseElementFactory.createStraight, startEdge)

    def createGentle(self, colour: Colour, startEdge: HexTileEdges) -> MultiColourFuser:
        return self.createSimpleTile(colour, BaseElementFactory.createGentle, startEdge)

    def createSharp(self, colour: Colour, startEdge: HexTileEdges) -> MultiColourFuser:
        return self.createSimpleTile(colour, BaseElementFactory.createSharp, startEdge)

    def createStraightTown(self, colour: Colour, startEdge: HexTileEdges) -> MultiColourFuser:
        return self.createSimpleTile(colour, BaseElementFactory.createStraightTown, startEdge)

    def createGentleTown(self, colour: Colour, startEdge: HexTileEdges) -> MultiColourFuser:
        return self.createSimpleTile(colour, BaseElementFactory.createGentleTown, startEdge)

    def createSharpTown(self, colour: Colour, startEdge: HexTileEdges) -> MultiColourFuser:
        return self.createSimpleTile(colour, BaseElementFactory.createSharpTown, startEdge)

    def createSharpCity(self, colour: Colour, side: HexTileEdges) -> MultiColourFuser:
        return self.createCity(colour, side, side.getNextCounterClockWise())

    def createGentleCity(self, colour: Colour, side: HexTileEdges) -> MultiColourFuser:
        return self.createCity(colour, side, side.getNextCounterClockWise(2))

    def createTile(self) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        # multiFuser.fuse(Colour.BLACK, self.createBase(0.16, 1.2 - self.dimensions.imageHeight))
        multiFuser.fuse(Colour.WHITE, self.createBase(0, self.dimensions.whiteLayerHeight))

        return multiFuser
