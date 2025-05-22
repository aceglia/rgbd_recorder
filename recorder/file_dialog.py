from PyQt5.QtWidgets import QFileDialog

import os

kwargs = {}
if "SNAP" in os.environ:
    kwargs["options"] = QFileDialog.DontUseNativeDialog


class LoadDialog:
    def __init__(self, parent=None, caption="", filter="Any(*)", dir=None, load_method=None):
        if dir is not None:
            kwargs["directory"] = dir

        self.filename, _ = QFileDialog.getOpenFileName(parent=parent, caption=caption, filter=filter, **kwargs)

        if self.filename is None or self.filename == "":
            return

        kwargs["directory"] = os.path.dirname(self.filename)

        if load_method is not None:
            load_method(self.filename)


class LoadFolderDialog:
    def __init__(self, parent=None, caption="", dir=None):
        if dir is not None:
            kwargs["directory"] = dir

        dialog = QFileDialog(parent=parent, caption=caption, **kwargs)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setFileMode(QFileDialog.DirectoryOnly)

        self.filename = ""
        if not dialog.exec_():
            return

        self.filename = dialog.selectedFiles()[0]
        if self.filename is None or self.filename == "":
            self.filename = ""
            return

        kwargs["directory"] = os.path.dirname(self.filename)


class SaveDialog:
    def __init__(self, parent=None, caption="", filter="Any(*)", suffix="", dir=None, save_method=None):
        if dir is not None:
            kwargs["directory"] = dir

        dialog = QFileDialog(parent=parent, caption=caption, filter=filter, **kwargs)

        dialog.setDefaultSuffix(suffix)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setFileMode(QFileDialog.AnyFile)

        self.save_method = save_method

        ### Must pass via .exec_ method to apply the default suffix .json
        if not dialog.exec_():
            return

        self.filename = dialog.selectedFiles()[0]


        kwargs["directory"] = os.path.dirname(self.filename)

        self.save_file()

    def save_file(self):
        if self.save_method is not None or self.filename != "":
            return self.save_method(self.filename)
        else: 
            return False

        
