from FreeCAD import Vector

from abc import ABC, abstractmethod


class Fusible(ABC):
    @abstractmethod
    def getSolid(self):
        pass

def fuse(*args):
    result = None

    for arg in args:
        element = fuseAll(list(arg)) if hasattr(arg, '__iter__') else getElement(arg)
        if element is not None:
            result = element.copy() if result is None else result.fuse(element)

    return result

def getElement(arg):
    return arg.solid if hasattr(arg, 'solid') else arg.getResult() if hasattr(arg, 'getResult') else arg

def fuseAll(args):
    result = None

    for arg in args:
        element = getElement(arg)
        if element is not None:
            result = element.copy() if result is None else result.fuse(element)

    return result

class Fuser:
    def __init__(self, *args):
        self.solid = fuse(*args)

    def fuse(self, *args) -> 'Fuser':
        self.solid = fuse(self.solid, *args)
        return self

    def cut(self, *args) -> 'Fuser':
        for arg in args:
            if arg is not None:
                self.solid = self.solid.cut(getElement(arg))
        return self

    def common(self, *args) -> 'Fuser':
        for arg in args:
            self.solid = self.solid.common(getElement(arg))
        return self

    def translate(self, vector: Vector) -> 'Fuser':
        if self.solid:
            self.solid.translate(vector)
        return self

    def rotate(self, centre: Vector, axis: Vector, angle: float) -> 'Fuser':
        if self.solid:
            self.solid.rotate(centre, axis, angle)
        return self

    def mirrorX(self):
        self.solid = self.solid.mirror(Vector(), Vector(1, 0, 0))  # invert X axis
        return self

    def mirrorY(self):
        self.solid = self.solid.mirror(Vector(), Vector(0, 1, 0))  # invert Y axis
        return self

    # wall = wall.mirror(Vector(), Vector(0, 1, 0)) # invert Y axis

    def mirrorZ(self):
        self.solid = self.solid.mirror(Vector(), Vector(0, 0, 1))  # invert Y axis
        return self
