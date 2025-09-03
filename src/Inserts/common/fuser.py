from FreeCAD import Vector

from abc import ABC, abstractmethod


class Fusible(ABC):
    @abstractmethod
    def getElement(self):
        pass

def fuse(*args):
    return fuseAll(args)

def getElement(arg):
    return arg.getElement() if isinstance(arg, Fusible) else arg

def fuseAll(args):
    result = None

    for arg in args:
        element = getElement(arg)
        result = element if result is None else result.fuse(element)

    return result

class Fuser:
    def __init__(self, *args):
        self.result = fuse(*args)

    def fuse(self, *args) -> 'Fuser':
        self.result = fuse(self.result, *args)
        return self

    def cut(self, *args) -> 'Fuser':
        for arg in args:
            self.result = self.result.cut(getElement(arg))
        return self

    def common(self, *args) -> 'Fuser':
        for arg in args:
            self.result = self.result.common(getElement(arg))
        return self

    def translate(self, vector: Vector) -> 'Fuser':
        self.result.translate(vector)
        return self

    def getResult(self):
        return self.result
