from math import cos, radians

import Part
from FreeCAD import Vector

from Inserts.common.geometry import createVector
from dataclasses import dataclass


class Fuser:
    def __init__(self, *args):
        self.result = fuse(*args)

    def fuse(self, *args):
        self.result = fuse(self.result, *args)

    def getResult(self):
        return self.result


def fuse(*args):
    return fuseAll(args)

def fuseAll(args):
    result = None

    for arg in args:
        result = arg if result is None else result.fuse(arg)

    return result
