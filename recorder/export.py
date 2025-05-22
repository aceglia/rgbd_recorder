import os
from PyQt5.QtWidgets import QWidget, QPushButton, QDesktopWidget, QPlainTextEdit, QGridLayout, QMessageBox, QCheckBox, QLabel, QLineEdit, QComboBox, QFileDialog
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
import numpy as np
from enums import ImageResolution
import pyrealsense2 as rs
from utils import log
from threading import Thread
import time 

class ExportConfig(QWidget):
    def __init__(self, log_box):
        super(ExportConfig, self).__init__()
        self.save_directory = None
        self.save_directory_base = os.getcwd()
        
        self.label = QLabel(self)
        self.log_box = log_box

        self._create_layout_objects()
        self.trial_num = 0

    def _create_layout_objects(self):
        self.save_dir_label = QLabel("Saving folder:")
        self.save_dir_input = QLineEdit(self.save_directory_base)
        self.save_dir_button = QPushButton("Browse")
        self.save_dir_button.clicked.connect(self.browse_folder)
    
        self.save_trial_label = QLabel("Trial name:")
        self.save_trial_input = QLineEdit('001')

        self.increment_label = QLabel("Increment trial number:")
        self.increment_checkbox = QCheckBox()
        self.increment_checkbox.setChecked(True)

        layout = QGridLayout()
        layout.addWidget(self.save_dir_label, 0, 0, 1, 1)
        layout.addWidget(self.save_dir_input, 0, 1, 1, 1)
        layout.addWidget(self.save_dir_button, 0, 2, 1, 1)

        layout.addWidget(self.save_trial_label, 1, 0, 1, 1)
        layout.addWidget(self.save_trial_input, 1, 1, 1, 1)

        layout.addWidget(self.increment_label, 2, 0, 1, 1)
        layout.addWidget(self.increment_checkbox, 2, 1, 1, 1)

        self.setLayout(layout)

    def browse_folder(self):
        save_directory = QFileDialog.getExistingDirectory(self, "Select directory")
        if not save_directory:
            return
        self.save_directory_base = save_directory
        self.save_dir_input.setText(self.save_directory_base)
    
    def get_next_save_directory(self):
        if self.increment_checkbox.isChecked():
            self.save_directory = os.path.join(self.save_directory_base, self.return_incremented_trial_name())
        else:
            self.save_directory = os.path.join(self.save_directory_base, self.save_trial_input.text())
        return self.save_directory

    def return_incremented_trial_name(self):
        folder_list = self._get_folders_in_directory(self.save_directory_base)
        last_number = folder_list[-1] if len(folder_list) > 0 else 0
        if self.get_num(self.save_trial_input.text()):
            trial_name = self.save_trial_input.text()[:-3] + str(last_number + 1).zfill(3)
        else:
            trial_name = self.save_trial_input.text() + str(last_number + 1).zfill(3)
        return trial_name

    def _get_folders_in_directory(self, directory_path):
        if not os.path.exists(directory_path):
            return []
        folder_list = [folder for folder in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, folder))]
        folder_list = sorted([int(x[-3:]) for x in folder_list if self.get_num(x)])
        if len(folder_list) > 0:
            self.log_box.log(f"Found {len(folder_list)} trial folders in {directory_path}. "
                            f"Your trial number will start from {folder_list[-1] + 1}.")
        return folder_list

    @staticmethod
    def get_num(name):
        try:
            num = int(name[-3:])
            return True
        except ValueError:
            return  False

    def get_dict(self):
        return {
            "save_directory_base": self.save_directory_base,
            "save_trial_input": self.save_trial_input.text(),
            "increment_checkbox": self.increment_checkbox.isChecked(),
        }

    def from_dict(self, data):
        self.save_directory_base = data["save_directory_base"]
        self.increment_checkbox.setChecked(data["increment_checkbox"])
        self.save_trial_input.setText(data["save_trial_input"])
        self.save_dir_input.setText(self.save_directory_base)

    def check_overwriting(self):
        if not os.path.exists(self.get_next_save_directory()):
            return self.get_next_save_directory()

        wind = QMessageBox()
        wind.setText(f"The directoy {self.save_directory} is not empty. Do you want to overwrite it?")
        wind.setWindowTitle("Select directory")
        wind.setIcon(QMessageBox.Question)
        wind.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        wind.setDefaultButton(QMessageBox.Yes) 
        wind.buttonClicked.connect(self.popup_button)
        wind.exec_()

    def popup_button(self, button):
        if button.text() == "Yes":
            return self.get_next_save_directory()
        elif button.text() == "Cancel":
            return None



        