from math import cos, radians

import Part
from FreeCAD import Vector

from Inserts.common.geometry import createVector
from dataclasses import dataclass


class Fuser:
    def __init__(self, *args):
        self.result = fuse(*args)

    def fuse(self, *args) -> 'Fuser':
        self.result = fuse(self.result, *args)
        return self

    def cut(self, *args) -> 'Fuser':
        for arg in args:
            self.result = self.result.cut(arg)
        return self

    def common(self, *args) -> 'Fuser':
        for arg in args:
            self.result = self.result.common(arg)
        return self

    def translate(self, vector: Vector) -> 'Fuser':
        self.result.translate(vector)
        return self

    def getResult(self):
        return self.result


def fuse(*args):
    return fuseAll(args)

def fuseAll(args):
    result = None

    for arg in args:
        result = arg if result is None else result.fuse(arg)

    return result
