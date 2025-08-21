from math import cos, radians

import Part
from FreeCAD import Vector

from Inserts.common.geometry import createVector
from dataclasses import dataclass


class Fuser:
    def __init__(self):
        self.result = None

    def fuse(self, nextPiece):
        self.result = nextPiece if self.result is None else self.result.fuse(nextPiece)

    def getResult(self):
        return self.result


def fuseAll(*args):
    fuser = Fuser()

    for arg in args:
        fuser.fuse(arg)

    return fuser.getResult()