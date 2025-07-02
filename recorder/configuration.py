import os
import sys
import numpy as np
import multiprocessing as mp
from multiprocessing.sharedctypes import RawArray

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout,
QWidget, QTextEdit, QGridLayout, QFileDialog, QCheckBox, QMessageBox, QTabBar, QComboBox, QPlainTextEdit, QTabWidget, QGroupBox)
from export import ExportConfig
from trigger import TriggerWindow
from delsys import DelsysConfiguration
from rgbd import RgbdWindow
from utils import log, CustomTabWidget
import json
from file_dialog import SaveDialog, LoadDialog, LoadFolderDialog


class ConfigurationWindow(QWidget):
    def __init__(self, log_box=None, parent=None):
        super().__init__()
        # self.setFixedSize(800, 200)
        self.parent = parent
        self.config_path = None
        self.configuration_dict = {}
        self.log_box = log_box

        self.is_initialized = False

        self.tab_widget = CustomTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.tab_widget.removeTab)

        self._init_tabs()

    
    def _init_tabs(self):
        self.trig_tab = None
        self.delsys_tab = None
        self.rgbd_tab = None
        self.export_tab = None
        self.tabs = []
        self.tab_widget.clear()

    def init_config(self):
        self.setWindowTitle("Configuration")
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.parent.save_close_config)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.parent.close_config)
        main_layout = QGridLayout()
        main_layout.addWidget(self.tab_widget, 0, 0, 1, 2)
        main_layout.addWidget(self.ok_button, 1, 0)
        main_layout.addWidget(self.cancel_button, 1, 1)
        self.is_initialized = True
        self.create_rgbd_tab()
        self.create_export_tab()
        self.setLayout(main_layout)
    
    def show_config(self):
        if not self.is_initialized:
            self.init_config()
        self.show()

    def load_config_file(self, file_path):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            self._init_tabs()
            self.config_path = file_path
            self.configuration_dict = data
            self.create_rgbd_tab()
            self.create_export_tab()
            if 'Export' in data:
                self.export_tab.from_dict(data['Export'])
            if 'RGBD' in data:
                self.rgbd_tab.from_dict(data['RGBD'])
            if 'Trigger' in data:
                self.create_trigger_tab()
                self.trig_tab.from_dict(data['Trigger'])
            if 'Delsys' in data:
                self.create_delsys_tab()
                self.delsys_tab.from_dict(data['Delsys'])
            self.log(f"Configuration loaded from: {file_path}. Found {list(data.keys())} tabs")
        except Exception as e:
            self.log(f"Error while loading configuration: {e}")

    def save_config_file(self, file_path: str=None):
        if not self.export_tab.check_overwriting():
            return False
        try:
            file_path = file_path if file_path else self.config_path
            dic_to_save = {}
            dic_to_save.update({'Export': self.export_tab.get_dict()})
            if self.rgbd_tab:
                dic_to_save.update({'RGBD': self.rgbd_tab.get_dict()})
            if self.trig_tab:
                dic_to_save.update({'Trigger': self.trig_tab.get_dict()})
            if self.delsys_tab:
                dic_to_save.update({'Delsys': self.delsys_tab.get_dict()})
            with open(file_path, "w") as f:
                json.dump(dic_to_save, f, indent=4)
            self.config_path = file_path
            self.configuration_dict = dic_to_save
            self.log(f"Configuration saved to: {self.config_path}")
            return True
        except Exception as e:
            self.log(f"Error while saving configuration: {e}")
            return False

    def log(self, message):
        if self.log_box is not None:
            self.log_box.log(message)

    def create_rgbd_tab(self):
        if self.rgbd_tab is not None:
            return
        self.rgbd_tab = RgbdWindow(self.log_box)
        self.tab_widget.addTab(self.rgbd_tab, "RGBD")
        tab_idx = self.tab_widget.indexOf(self.rgbd_tab)
        self.tab_widget.tabBar().setTabButton(tab_idx, QTabBar.RightSide, None)

    def create_export_tab(self):
        if self.export_tab is not None:
            return
        self.export_tab = ExportConfig(self.log_box)
        self.tab_widget.addTab(self.export_tab, "Export")
        tab_idx = self.tab_widget.indexOf(self.export_tab)
        self.tab_widget.tabBar().setTabButton(tab_idx, QTabBar.RightSide, None)


    def create_trigger_tab(self):
        if self.trig_tab is not None:
            return
        self.trig_tab = TriggerWindow()
        self.tab_widget.addTab(self.trig_tab, "Trigger settings")

    def create_delsys_tab(self):
        if self.delsys_tab is not None:
            return
        self.delsys_tab = DelsysConfiguration()
        self.tab_widget.addTab(self.delsys_tab, "Delsys")

    def save_config(self, save_as=False):
        close = True
        if self.delsys_tab is not None:
            close = self.delsys_tab.check_same_idx()

        if not close:
            return
        
        if self.config_path is not None and not save_as:
            return self.save_config_file()
        return SaveDialog(
            parent=self,
            caption="Save Configuration",
            filter="Save File (*json)",
            suffix="json",
            save_method=self.save_config_file,
        )
    
    def load_config(self):
        LoadDialog(
            parent=self,
            caption="Load configuration file",
            filter="Save File (*.json);; Any(*)",
            load_method=self.load_config_file,
        )

    def get_tab_names(self):
        return [self.tab_widget.tabText(i) for i in range(self.tab_widget.count())]
    
    def close_window(self):
        close = True
        if self.delsys_tab is not None:
            close = self.delsys_tab.check_same_idx()

        if not close:
            return

        self.close()
        if self.config_path:
            self.load_config_file(self.config_path)

    def get_save_directory(self):
        dir = self.export_tab.get_next_save_directory()
        os.makedirs(dir, exist_ok=True)
        return dir