import math
from math import tan, cos, sin, radians, pi

from Inserts.common import geometry
from Inserts.common.hexes import getHexSide
from Inserts.common.labels import Labels
from Inserts.common.smartbox import SmartBox
from typing import Callable

import Part
from FreeCAD import Vector, Document

from Inserts.common.colours import MultiColourFuser, Colour
from Inserts.common.fuser import Fuser, fuseAll
from Inserts.common.geometry import createWire, createVector
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
    hexShortDiagonal: float
    railWidth: float
    townBarWidth: float
    townBarLength: float
    cityDiameter: float
    townDiameter: float
    lineWidth: float
    whiteLayerHeight: float
    scale: float
    fontSize: float
    font: str

    def __init__(self, imageHeight: float, hexShortDiagonal: float, railWidth: float,
                 townBarWidth: float, townBarLength: float, cityDiameter: float,
                 townDiameter: float, scale: float, lineWidth: float, whiteLayerHeight: float, font: str, fontSize: float):
        self.imageHeight = imageHeight
        self.whiteLayerHeight = whiteLayerHeight
        self.font = font
        self.scale = scale

        self.hexShortDiagonal = hexShortDiagonal * scale
        self.railWidth = railWidth * scale
        self.townBarWidth = townBarWidth * scale
        self.townBarLength = townBarLength * scale
        self.cityDiameter = cityDiameter * scale
        self.townDiameter = townDiameter * scale
        self.lineWidth = lineWidth * scale
        self.fontSize = fontSize * scale

        self.hex = Hex(self.hexShortDiagonal, Vector(0, 0))

    def getTotalHeight(self):
        return self.imageHeight + self.whiteLayerHeight

    def createOutline(self) -> 'HexImageDimensions':
        return HexImageDimensions(
            imageHeight = self.imageHeight,
            hexShortDiagonal= self.hexShortDiagonal,
            railWidth = self.railWidth + self.lineWidth * 2,
            townBarWidth = self.townBarWidth + self.lineWidth * 2,
            townBarLength = self.townBarLength + self.lineWidth * 2,
            cityDiameter = self.cityDiameter + self.lineWidth * 2,
            townDiameter = self.townDiameter + self.lineWidth * 2,
            scale = self.scale,
            lineWidth = self.lineWidth,
            whiteLayerHeight = self.whiteLayerHeight,
            font = self.font,
            fontSize = self.fontSize
        )

class BaseElementFactory:
    def __init__(self, dimensions: HexImageDimensions, document: Document):
        self.dimensions = dimensions
        self.labels = Labels(document, dimensions.font, dimensions.fontSize)

    def alignToEdge(self, solid: Part.Solid, startEdge: HexTileEdges):
        solid.translate(Vector(-self.dimensions.hexShortDiagonal / 2, self.dimensions.railWidth / 2, 0))
        solid.rotate(Vector(0, 0), Vector(0, 0, 1), 180 + startEdge.value)
        return solid

    def createStraight(self, startEdge: HexTileEdges) -> Part.Solid:
        pencil = Pencil()
        pencil.right(self.dimensions.hexShortDiagonal)
        pencil.down(self.dimensions.railWidth)
        pencil.left(self.dimensions.hexShortDiagonal)

        return self.alignToEdge(pencil.extrude(self.dimensions.imageHeight), startEdge)

    def createStraightTown(self, startEdge: HexTileEdges) -> Part.Solid:
        pencil = Pencil()

        pencil.right((self.dimensions.hexShortDiagonal - self.dimensions.townBarLength) / 2)
        pencil.up((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2)
        pencil.right(self.dimensions.townBarLength)
        pencil.down((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2)
        pencil.right((self.dimensions.hexShortDiagonal - self.dimensions.townBarLength) / 2)

        pencil.down(self.dimensions.railWidth)

        pencil.left((self.dimensions.hexShortDiagonal - self.dimensions.townBarLength) / 2)
        pencil.down((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2)
        pencil.left(self.dimensions.townBarLength)
        pencil.up((self.dimensions.townBarWidth - self.dimensions.railWidth) / 2)
        pencil.left((self.dimensions.hexShortDiagonal - self.dimensions.townBarLength) / 2)

        return self.alignToEdge(pencil.extrude(self.dimensions.imageHeight), startEdge)

    def createCircle(self, radius: float) -> Part.Solid:
        return Part.makeCylinder(radius, self.dimensions.imageHeight)

    def createCityCircle(self, centre: Vector = Vector(), delta: float = 0) -> Part.Solid:
        return self.createCircle(self.dimensions.cityDiameter / 2 + delta).translate(centre)

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

    def createHalfRing(self, delta: float) -> Fuser:
        outer = self.createCircle(self.dimensions.hexShortDiagonal / 3 + self.dimensions.railWidth / 2 + delta)
        inner = self.createCircle(self.dimensions.hexShortDiagonal / 3 - self.dimensions.railWidth / 2 - delta)
        box = SmartBox(self.dimensions.hexShortDiagonal, self.dimensions.hexShortDiagonal * 2, self.dimensions.imageHeight).translate(-self.dimensions.railWidth / 2, -self.dimensions.hexShortDiagonal)
        return self.rotate30(Fuser(outer.cut(inner).cut(box.solid)))

    def createGentle(self, startEdge: HexTileEdges) -> Part.Solid:
        return self.createCurve(startEdge, self.dimensions.hex.getSide() / 2 / sin(radians(30)), 60)

    def createGentleTown(self, startEdge: HexTileEdges) -> Part.Solid:
        return self.createTownCurve(startEdge, self.dimensions.hex.getSide() / 2 / sin(radians(30)), 60)

    def createSharp(self, startEdge: HexTileEdges) -> Part.Solid:
        return self.createCurve(startEdge, 0, 120)

    def createSharpTown(self, startEdge: HexTileEdges) -> Part.Solid:
        return self.createTownCurve(startEdge, 0, 120)

    def createSingleCity(self, delta: float = 0) -> Part.Solid:
        return self.createCityCircle(delta=delta)

    def createOuterDoubleCity(self, delta: float = 0) -> Part.Solid:
        fuser = Fuser()

        box = SmartBox(self.dimensions.cityDiameter + delta * 2, self.dimensions.cityDiameter + delta * 2, self.dimensions.imageHeight)
        self.rotate30(fuser.fuse(box.translate(-box.length / 2, -box.width / 2)))
        fuser.fuse(self.createInnerDoubleCity(delta))

        return fuser.solid

    def createInnerDoubleCity(self, delta: float = 0) -> Part.Solid:
        fuser = Fuser()

        fuser.fuse(self.createCityCircle(Vector(-self.dimensions.cityDiameter / 2 - self.dimensions.lineWidth / 2), delta))
        fuser.fuse(self.createCityCircle(Vector(self.dimensions.cityDiameter / 2 + self.dimensions.lineWidth / 2), delta))

        return self.rotate30(fuser).solid

    def createOuterTripleCity(self, delta: float = 0) -> Part.Solid:
        d = (self.dimensions.cityDiameter + self.dimensions.lineWidth * 2) / math.sqrt(3)
        r = self.dimensions.cityDiameter / 2 + delta
        l = self.dimensions.cityDiameter + self.dimensions.lineWidth * 2

        pencil = Pencil()
        pencil.draw(d, 60)
        pencil.up(r)
        pencil.right(l)
        pencil.down(r)
        pencil.draw(r, -120)
        pencil.draw(l, 150)
        pencil.draw(r, 60)
        pencil.draw(r, 120)
        pencil.draw(l, 30)
        pencil.draw(r, -60)

        fuser = self.rotate30(Fuser(pencil.extrude(self.dimensions.imageHeight)))
        fuser.fuse(self.createInnerTripleCity(delta))

        return fuser.solid

    def createInnerTripleCity(self, delta: float = 0) -> Part.Solid:
        fuser = Fuser()

        d = (self.dimensions.cityDiameter + self.dimensions.lineWidth * 2) / math.sqrt(3)
        for i in range(3):
            fuser.fuse(self.createCityCircle(geometry.createVector(d, i * 120 - 60), delta))

        return self.rotate30(fuser).solid

    def createTown(self) -> Part.Solid:
        return self.createCircle(self.dimensions.townDiameter / 2)

    def createSpikes(self, delta: float, *edges: HexTileEdges) -> Part.Solid:
        spikeLength = self.dimensions.hexShortDiagonal / 3.8

        pencil = Pencil(Vector(0, delta))
        pencil.jump(Vector(spikeLength * (1 + 2 * delta / self.dimensions.railWidth), -self.dimensions.railWidth / 2 - delta))
        pencil.jumpFromStart(Vector(0, -self.dimensions.railWidth - delta * 2))
        solidSpike = pencil.extrude(self.dimensions.imageHeight)

        return fuseAll(self.alignToEdge(solidSpike.copy(), edge) for edge in edges)

    def createRays(self, *edges: HexTileEdges) -> Part.Solid:
        rayLength = self.dimensions.hexShortDiagonal / 2 + self.dimensions.railWidth / 2 * tan(radians(30))

        pencil = Pencil()
        pencil.right(rayLength)
        pencil.down(self.dimensions.railWidth)
        pencil.left(rayLength)
        solidRay = pencil.extrude(self.dimensions.imageHeight)

        return fuseAll(self.alignToEdge(solidRay.copy(), edge) for edge in edges)

    def createValueBox(self, offsetMultiplier: float, delta: float) -> SmartBox:
        length = getHexSide(self.dimensions.hexShortDiagonal) * 0.45
        width = getHexSide(self.dimensions.hexShortDiagonal) * 0.3
        offset = (length - self.dimensions.lineWidth) * offsetMultiplier
        return SmartBox(length - delta * 2, width - delta * 2, self.dimensions.imageHeight).translate(delta + offset - self.dimensions.lineWidth / 2, delta - width / 2)

    def createValueBoxes(self, count: int) -> MultiColourFuser:
        fuser = MultiColourFuser()
        for i in range(count):
            outerBox = self.createValueBox(i - count / 2, 0)
            innerBox = self.createValueBox(i - count / 2, self.dimensions.lineWidth)
            fuser.fuse(Colour.GRAY, innerBox)
            fuser.fuseUnique(Colour.BLACK, outerBox)

        return self.rotate30(fuser)

    def rotate30(self, fuser):
        return fuser.rotate(Vector(), Vector(0, 0, 1), -30)

    def createLabel(self, label: str, angle: float) -> Fuser:
        length = self.dimensions.hexShortDiagonal / 6
        width = self.dimensions.hexShortDiagonal / 6
        text = Fuser(self.labels.createText(label, length, width, self.dimensions.imageHeight).translate(Vector(-length / 2, -width / 2)))

        return self.rotate30(text.translate(createVector(self.dimensions.hexShortDiagonal * 0.435, angle)))

class Images:
    def __init__(self, dimensions: HexImageDimensions, document: Document):
        self.dimensions = dimensions
        self.baseFactory = BaseElementFactory(dimensions, document)
        self.outlineFactory = BaseElementFactory(dimensions.createOutline(), document)

    def createHex(self, height: float = None) -> Part.Solid:
        wire = createWire(*(self.dimensions.hex.getVector(x) for x in HexTileVertices.iterate()))
        face = Part.Face(wire)
        solid = face.extrude(Vector(0, 0, height or self.dimensions.imageHeight))
        return solid

    def createMine(self, upgraded) -> MultiColourFuser:
        fuser = self.createGenericCity(Colour.GRAY, Colour.GRAY, BaseElementFactory.createSingleCity, BaseElementFactory.createSingleCity, None, None, HexTileManifestEdges.S, HexTileManifestEdges.N)
        if upgraded:
            fuser.replace(Colour.WHITE, self.baseFactory.createHalfRing(self.dimensions.lineWidth))
            fuser.replace(Colour.BLACK, self.baseFactory.createHalfRing(0))
        return fuser

    def createSingleCity(self, colour: Colour, letter: str | None, angle: float | None, *edges: HexTileEdges) -> MultiColourFuser:
        return self.createGenericCity(colour, Colour.WHITE, BaseElementFactory.createSingleCity, BaseElementFactory.createSingleCity, letter, angle, *edges)

    def createDoubleCity(self, colour: Colour, letter: str | None, angle: float | None, *edges: HexTileEdges) -> MultiColourFuser:
        return self.createGenericCity(colour, Colour.WHITE, BaseElementFactory.createInnerDoubleCity, BaseElementFactory.createOuterDoubleCity, letter, angle, *edges)

    def createTripleCity(self, colour: Colour, letter: str | None, angle: float | None, *edges: HexTileEdges) -> MultiColourFuser:
        return self.createGenericCity(colour, Colour.WHITE, BaseElementFactory.createInnerTripleCity, BaseElementFactory.createOuterTripleCity, letter, angle, *edges)

    def createGenericCity(self, colour: Colour, cityColour: Colour, innerCityMethod: Callable, outerCityMethod: Callable, letter: str | None, angle: float | None, *edges: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(cityColour, innerCityMethod(self.baseFactory))
        multiFuser.fuseUnique(Colour.BLACK, innerCityMethod(self.baseFactory, self.dimensions.lineWidth))

        multiFuser.fuseUnique(Colour.WHITE, outerCityMethod(self.baseFactory))
        multiFuser.fuseUnique(Colour.BLACK, outerCityMethod(self.baseFactory, self.dimensions.lineWidth))

        multiFuser.fuseUnique(Colour.BLACK, self.baseFactory.createRays(*edges))
        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createRays(*edges))

        multiFuser.fuseUnique(Colour.WHITE, outerCityMethod(self.baseFactory, self.dimensions.lineWidth * 2))

        if letter is not None:
            multiFuser.fuse(Colour.BLACK, self.baseFactory.createLabel(letter, angle))

        return self.putOnHex(multiFuser, colour)

    def createLabeledTown(self, colour: Colour, letter: str | None, angle: float | None, *edges: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.BLACK, self.baseFactory.createTown())
        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createTown())
        multiFuser.fuseUnique(Colour.BLACK, self.baseFactory.createRays(*edges))
        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createRays(*edges))

        if letter is not None:
            multiFuser.fuse(Colour.BLACK, self.baseFactory.createLabel(letter, angle))

        return self.putOnHex(multiFuser, colour)

    def createPort(self, valueBoxCount: int) -> MultiColourFuser:
        multiFuser = self.baseFactory.createValueBoxes(valueBoxCount)
        multiFuser.fuse(Colour.BLACK, self.baseFactory.createSpikes(0, HexTileManifestEdges.S))
        multiFuser.fuseUnique(Colour.WHITE, self.baseFactory.createSpikes(self.dimensions.lineWidth, HexTileManifestEdges.S))

        return self.putOnHex(multiFuser, Colour.BLUE)

    def createTown(self, colour: Colour, *edges: HexTileEdges) -> MultiColourFuser:
        return self.createLabeledTown(colour, None, None, *edges)

    def createRays(self, colour: Colour, *edges: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(Colour.BLACK, self.baseFactory.createRays(*edges))
        multiFuser.fuseUnique(Colour.WHITE, self.outlineFactory.createRays(*edges))

        return self.putOnHex(multiFuser, colour)

    def createSimpleTile(self, colour: Colour, trackMethod: Callable, startEdge: HexTileEdges) -> MultiColourFuser:
        return self.createCustomTile(colour, Colour.WHITE, Colour.BLACK, trackMethod, startEdge)

    def createCustomTile(self, tileColour: Colour, outlineColour: Colour, trackColour: Colour, trackMethod: Callable, startEdge: HexTileEdges) -> MultiColourFuser:
        multiFuser = MultiColourFuser()

        multiFuser.fuse(trackColour, trackMethod(self.baseFactory, startEdge))
        multiFuser.fuseUnique(outlineColour, trackMethod(self.outlineFactory, startEdge))

        return self.putOnHex(multiFuser, tileColour)

    def createEmpty(self, tileColour: Colour) -> MultiColourFuser:
        return self.putOnHex(MultiColourFuser(), tileColour)

    def putOnHex(self, fuser: MultiColourFuser, colour: Colour) -> MultiColourFuser:
        fuser.fuseUnique(colour, self.createHex())

        hexSolid = self.createHex(self.dimensions.whiteLayerHeight)
        hexSolid.translate(Vector(0, 0, -self.dimensions.whiteLayerHeight))
        fuser.fuse(Colour.WHITE, hexSolid)

        return fuser

    def createTile(self, number) -> MultiColourFuser:
        match number:
            case None: return self.createEmpty(Colour.BASE)
            case 3: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createSharpTown, HexTileManifestEdges.S)
            case 4: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createStraightTown, HexTileManifestEdges.S)
            case 5: return self.createSingleCity(Colour.YELLOW, None, None, HexTileManifestEdges.S, HexTileManifestEdges.SE)
            case 6: return self.createSingleCity(Colour.YELLOW, None, None, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 7: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createSharp, HexTileManifestEdges.S)
            case 8: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createGentle, HexTileManifestEdges.S)
            case 9: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createStraight, HexTileManifestEdges.S)
            case 58: return self.createSimpleTile(Colour.YELLOW, BaseElementFactory.createGentleTown, HexTileManifestEdges.S)
            case 57: return self.createSingleCity(Colour.YELLOW, None, None, HexTileManifestEdges.S, HexTileManifestEdges.N)

            case 14: return self.createDoubleCity(Colour.GREEN, None, None, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.SE)
            case 15: return self.createDoubleCity(Colour.GREEN, None, None, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 80: return self.createRays(Colour.GREEN, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 143: return self.createTown(Colour.GREEN, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 81: return self.createRays(Colour.GREEN, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 144: return self.createTown(Colour.GREEN, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 82: return self.createRays(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 141: return self.createTown(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 83: return self.createRays(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.S, HexTileManifestEdges.NW)
            case 142: return self.createTown(Colour.GREEN, HexTileManifestEdges.N, HexTileManifestEdges.S, HexTileManifestEdges.NW)
            case 619: return self.createDoubleCity(Colour.GREEN, None, None, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.NE, HexTileManifestEdges.S)
            case 207: return self.createDoubleCity(Colour.GREEN, 'Y', -20, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 208: return self.createDoubleCity(Colour.GREEN, 'Y', -20, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.SE)
            case 405: return self.createDoubleCity(Colour.GREEN, 'T', 160, HexTileManifestEdges.S, HexTileManifestEdges.SW, HexTileManifestEdges.SE)
            case 622: return self.createDoubleCity(Colour.GREEN, 'Y', 20, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.NE)

            case 63: return self.createDoubleCity(Colour.BROWN, None, None, *list(HexTileManifestEdges))
            case 544: return self.createRays(Colour.BROWN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.SE)
            case 545: return self.createRays(Colour.BROWN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 546: return self.createRays(Colour.BROWN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case 611: return self.createDoubleCity(Colour.BROWN, None, None, HexTileManifestEdges.S, HexTileManifestEdges.SW, HexTileManifestEdges.NW, HexTileManifestEdges.N, HexTileManifestEdges.NE)
            case 768: return self.createTown(Colour.BROWN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.SE)
            case 767: return self.createTown(Colour.BROWN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.SW, HexTileManifestEdges.S)
            case 769: return self.createTown(Colour.BROWN, HexTileManifestEdges.N, HexTileManifestEdges.NW, HexTileManifestEdges.S, HexTileManifestEdges.NE)
            case "X5": return self.createTripleCity(Colour.BROWN, 'Y', 20, HexTileManifestEdges.S, HexTileManifestEdges.SW, HexTileManifestEdges.NW, HexTileManifestEdges.N, HexTileManifestEdges.NE)
            case "X10": return self.createDoubleCity(Colour.BROWN, 'T', 160, HexTileManifestEdges.S, HexTileManifestEdges.SW, HexTileManifestEdges.SE)

            case 60: return self.createRays(Colour.GRAY, *list(HexTileManifestEdges))
            case 169: return self.createRays(Colour.GRAY, HexTileManifestEdges.S, HexTileManifestEdges.NW, HexTileManifestEdges.N, HexTileManifestEdges.NE, HexTileManifestEdges.SE)
            case 895: return self.createDoubleCity(Colour.GRAY, None, None,*list(HexTileManifestEdges))
            case "X11": return self.createTripleCity(Colour.GRAY, 'Y', 20, HexTileManifestEdges.S, HexTileManifestEdges.SW, HexTileManifestEdges.NW, HexTileManifestEdges.N, HexTileManifestEdges.NE)
            case "X16": return self.createTripleCity(Colour.GRAY, 'T', 20, HexTileManifestEdges.S, HexTileManifestEdges.SW, HexTileManifestEdges.SE)
            case "X17": return self.createTown(Colour.GRAY, *list(HexTileManifestEdges))
            case 51: return self.createDoubleCity(Colour.GRAY, None, None, HexTileManifestEdges.S, HexTileManifestEdges.SW, HexTileManifestEdges.NW, HexTileManifestEdges.N, HexTileManifestEdges.NE)

            case "PNW1": return self.createCustomTile(Colour.BLUE, Colour.BLACK, Colour.WHITE, BaseElementFactory.createStraight, HexTileManifestEdges.S)
            case "PNW2": return self.createCustomTile(Colour.BLUE, Colour.BLACK, Colour.WHITE, BaseElementFactory.createGentle, HexTileManifestEdges.S)
            case "PNW3": return self.createLabeledTown(Colour.GRAY, "30", 25, *list(HexTileManifestEdges))
            case "PNW4": return self.createMine(False)
            case "PNW5": return self.createMine(True)
            case "P1": return self.createPort(2)
            case "P2": return self.createPort(3)



        raise(f"Invalid tile number: {number}")
