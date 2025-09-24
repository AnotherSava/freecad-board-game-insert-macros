import FreeCAD

import subprocess
import os
import glob
from Inserts.common.colours import Colour
from dataclasses import dataclass


@dataclass
class ExportObject:
    prefix: str
    generator: callable

class Exporter:
    def __init__(self, folder: str, *exportItems: ExportObject):
        self.folder = folder
        self.exportItems = exportItems

    def createFileName(self, exportObject: ExportObject, colour: Colour, githubCommit: str) -> str:
        return f"{self.folder}\\script\\{exportObject.prefix}-{colour.getName()}-{githubCommit}.stl"

    def deleteAllStlFilesWithPrefix(self, prefix: str):
        scriptDirectory = os.path.join(self.folder, "script")
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

    def export(self):

        githubCommit = self.getLastGithubCommitId()

        for exportObject in self.exportItems:
            print(f"Deleting old files {exportObject.prefix}...")
            self.deleteAllStlFilesWithPrefix(exportObject.prefix)

            print(f"Creating {exportObject.prefix}...")
            multiColouredFuser = exportObject.generator()

            for (colour, f) in multiColouredFuser.fuserByColour.items():
                filename = self.createFileName(exportObject, colour, githubCommit)
                f.solid.exportStl(filename)
                print(f"Exported {exportObject.prefix} to {filename}")

    def show(self):
        for item in self.exportItems:
            item.generator().show()

        FreeCAD.Gui.SendMsgToActiveView('ViewFit')
