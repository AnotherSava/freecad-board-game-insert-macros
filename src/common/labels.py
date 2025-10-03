import Draft
import Part
from FreeCAD import Vector, Document


class Labels:
    def __init__(self, document: Document, font: str, fontSize: float):
        self.font = font
        self.fontSize = fontSize
        self.document = document

    # text is aligned in the middle of a square width a side equals space
    def createText(self, text: str, length: float, width: float, height: float) -> Part.Solid:
        string = Draft.makeShapeString(String=text, FontFile=self.font, Size=self.fontSize)

        solid = string.Shape.extrude(Vector(0, 0, height))
        solid.translate(Vector((length - string.Shape.BoundBox.XLength) / 2, (width - string.Shape.BoundBox.YLength) / 2))

        self.document.removeObject(string.Name)

        return solid
