import glob
import os
import subprocess
from dataclasses import dataclass

import FreeCAD

from common.colours import Colour, show


@dataclass
class ExportObject:
    prefix: str
    generator: callable

class Exporter:
    def __init__(self, folder: str, *exportItems: ExportObject):
        self.folder = folder
        self.exportItems = exportItems
        self.bound = None

    def withBound(self, bound):
        self.bound = bound
        return self

    def createFileName(self, exportObject: ExportObject, colour: Colour, githubCommit: str, subFolder: str) -> str:
        absPath = f"{self.folder}\\{subFolder}\\{exportObject.prefix}-{colour.getName()}-{githubCommit}.stl"
        os.makedirs(os.path.dirname(absPath), exist_ok=True) # create a folder if needed
        return absPath

    def deleteAllStlFilesWithPrefix(self, subFolder: str, prefix: str):
        scriptDirectory = os.path.join(self.folder, subFolder)
        pattern = os.path.join(scriptDirectory, f"{prefix}-*.stl")
        deletedFiles = glob.glob(pattern)
        
        for filePath in deletedFiles:
            try:
                os.remove(filePath)
                print(f"Deleted {filePath}")
            except OSError as e:
                print(f"Error deleting {filePath}: {e}")

    def getLastGithubCommitId(self):
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.folder).decode('utf-8').strip()[:7]

    def publish(self):
        self.saveAndShow("published")

    def export(self, showTransparency: int = None):
        self.saveAndShow("script", showTransparency)

    def saveAndShow(self, subFolder: str, showTransparency: int = None):
        githubCommit = self.getLastGithubCommitId()

        for exportObject in self.exportItems:
            print(f"Deleting old files {exportObject.prefix}...")
            self.deleteAllStlFilesWithPrefix(subFolder, exportObject.prefix)

            print(f"Creating {exportObject.prefix}...")
            multiColouredFuser = exportObject.generator()
            if self.bound:
                multiColouredFuser.common(self.bound)

            for (colour, f) in multiColouredFuser.fuserByColour.items():
                filename = self.createFileName(exportObject, colour, githubCommit, subFolder)
                solid = f.solid.removeSplitter()
                solid.exportStl(filename)
                print(f"Exported {exportObject.prefix} to {filename}")

                if showTransparency is not None:
                    show(solid, colour, showTransparency)

        if showTransparency is not None:
            FreeCAD.Gui.SendMsgToActiveView('ViewFit')

    def show(self, transparency: int = 0):
        for item in self.exportItems:
            fuser = item.generator()
            if self.bound:
                fuser.common(self.bound)
            fuser.show(transparency)

        FreeCAD.Gui.SendMsgToActiveView('ViewFit')
