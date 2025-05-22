from ast import main
import sys
from turtle import color
from cv2 import log
import numpy as np
import multiprocessing as mp
from multiprocessing.sharedctypes import RawArray

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout,
QWidget, QTextEdit, QGridLayout, QFileDialog, QCheckBox, QMessageBox, QTabBar, QComboBox, QPlainTextEdit, QTabWidget, QGroupBox, QSplitter)
from delsys_recorder import DelsysRecorder
from rgbd_recorder import RgbdRecorder
from trigger_recorder import TriggerRecorder
from utils import LogBox
import json
from file_dialog import SaveDialog, LoadDialog, LoadFolderDialog
from configuration import ConfigurationWindow
from synchronizer import Synchronizer
from display import Display
from PyQt5.QtCore import Qt, QTimer


class MenuBar:
    def __init__(self, parent):
        self.menu_bar = parent.menuBar()
        self._file_menu()
        self._run_menu()
    
    def _file_menu(self):
        self.file_menu = self.menu_bar.addMenu("File")
        self.new_conf = self.file_menu.addAction("New configuration")
        self.load_conf = self.file_menu.addAction("Load configuration")
        self.save_config = self.file_menu.addAction("Save configuration")
        self.save_config_as = self.file_menu.addAction("Save configurtion as")
        self.exit = self.file_menu.addAction("Exit")
    
    def _run_menu(self):
        self.run_menu = self.menu_bar.addMenu("Run")
        self.configuration_menu = self.run_menu.addAction("Configuration")
        self.run = self.run_menu.addAction("Run")
        self.trigger_action = self.run_menu.addAction("Add trigger")
        self.gognio_action = self.run_menu.addAction("Add delsys")
        self.disable_run_menu()
    
    def disable_run_menu(self):
        self.run_menu.setEnabled(False)
    
    def enable_run_menu(self):
        self.run_menu.setEnabled(True)


class GUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sync = Synchronizer()
        self.setWindowTitle("RGBD recorder")
        self.log_box = None
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self._init_layout()

        self.refresh_plot = 16  # refresh plot at 60 Hz
        self.buffer_size = 20

        self.configuration = ConfigurationWindow(parent=self, log_box=self.log_box)

        self._create_menu_bar()
        self.trig_tab = None
        self.gognio_tab = None
        self.nb_save_process = 2

        self.show()

        # self.timer_plot = QTimer(self)
        # self.timer_plot.setInterval(self.refresh_plot)
        # self.timer_plot.timeout.connect(self.start_timer)

    def _init_layout(self):
        futur_display = QWidget()
        if self.log_box is None:
            self.log_box = LogBox()
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.log_box.clear)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(futur_display)
        splitter.addWidget(self.log_box)

        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.clear_log_button)
        self.central_widget.setLayout(main_layout)
        
    def _create_menu_bar(self):
        self.menu_bar = MenuBar(self)
        self.menu_bar.trigger_action.triggered.connect(self.configuration.create_trigger_tab)
        self.menu_bar.gognio_action.triggered.connect(self.configuration.create_delsys_tab)

        self.menu_bar.new_conf.triggered.connect(self.show_config)
        self.menu_bar.load_conf.triggered.connect(self.load_config)
        self.menu_bar.save_config.triggered.connect(self.configuration.save_config)
        self.menu_bar.save_config_as.triggered.connect(lambda x: self.configuration.save_config(save_as=True))
        self.menu_bar.save_config.setEnabled(False)
        self.menu_bar.save_config_as.setEnabled(False)
        self.menu_bar.configuration_menu.triggered.connect(self.show_config)
        self.menu_bar.run.triggered.connect(self.start)
        self.menu_bar.exit.triggered.connect(self.popup_quit)

    def show_config(self):
        self.menu_bar.enable_run_menu()
        self.menu_bar.run.setEnabled(False)
        self.menu_bar.configuration_menu.setEnabled(False)
        self.menu_bar.save_config.setEnabled(True)
        self.menu_bar.save_config_as.setEnabled(True)
        self.configuration.show_config()
    
    def load_config(self):
        self.configuration.load_config()
        self.show_config()

    def _init_mp_var(self):
        self.event_started = [mp.Event()] * (len(self.configuration.tabs) + self.nb_save_process)
        
        self.frame_queue = mp.Queue()

        self.trigger_start_event = mp.Event()
        self.trigger_stop_event = mp.Event()

        for name in self.configuration.get_tab_names():
            if 'trigger' in name.lower():
                self.use_trigger = True
                self.trigg_queue = mp.Queue()
            if 'delsys' in name.lower():
                self.use_delsys = True
                self.delsys_queue = mp.Queue()
        image_res = self.configuration.rgbd_tab.get_dict()['image_res'].split('x')
        image_size = (int(image_res[0]), int(image_res[1]))
        color_shape = (3, image_size[1], image_size[0], self.buffer_size)
        depth_shape = (image_size[1], image_size[0], self.buffer_size)

        color_array = RawArray("c", int(np.prod(color_shape)))  # 'c' = uint8
        depth_array = RawArray("H", int(np.prod(depth_shape))) 
        return color_array, depth_array

    def start(self):
        self.save_directory_base = self.configuration.get_save_directory()

        item = self.central_widget.layout().itemAt(0).widget()
        item.setParent(None)
        self.central_widget.layout().removeWidget(item)

        self.display = Display(self.configuration.config_path)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.display)
        splitter.addWidget(self.log_box)
        self.central_widget.layout().insertWidget(0, splitter)

        self.menu_bar.disable_run_menu()

        self.log("Starting processes...")

        color_array, depth_array = self._init_mp_var()
        
        self.processes = []
        p = mp.Process(target=GUI.get_rgbd, args=(self.sync, color_array, depth_array,self.log,), daemon=True, name="rgbd")
        self.processes.append(p)

        for i in range(self.sync.nb_save_process):
            p = mp.Process(target=RgbdRecorder.save_rgbd_from_buffer,
                           args=(self.sync, color_array, depth_array, i,self.log,), daemon=True, name=f"save_{i}")
            self.processes.append(p)

        p = mp.Process(target=GUI.run_delsys,
                        args=(self.sync, self.gagnio_queue, self.log,), daemon=True, name="save_delsys")
        self.processes.append(p)        
        p = mp.Process(target=GUI.get_trigger,
                        args=(self.sync,self.trigger_chan, self.threeshold, self.vicon_ip, self.trig_less, self.trig_queue),
                          daemon=True, name="trigger")
        self.processes.append(p)
        
        p = mp.Process(target=Display.display_tabs, args=(self,), daemon=True, name="display")
        self.processes.append(p)

        for p in self.processes:
            p.start()

        self.log("Processes started.")

    def quit(self):
        if hasattr(self, 'processes'):
            for p in self.processes:
                p.join()
            self.log("All processes stopped.")
        self.close()

    def log(self, message):
        if self.log_box is not None:
            self.log_box.log(message)

        
    def get_rgbd(self, color_array, depth_array, log):

        recorder = RgbdRecorder(self.save_directory_base)
        recorder.get_rgbd(color_array, depth_array, log)
    
    def run_delsys(self, gagnio_queue, log):
        delsys = DelsysRecorder(self.save_directory_base)
        delsys.run_delsys( gagnio_queue, log)

    def get_trigger(self, trigger_chan, threeshold, vicon_ip, trig_less, trig_queue):
        trigger = TriggerRecorder(self.save_directory_base)
        trigger.run_trigger(trigger_chan, threeshold, vicon_ip, trig_less, trig_queue)
    
    def popup_quit(self):
        wind = QMessageBox()
        wind.setText("Do you want to save the configuration before quitting?")
        wind.setWindowTitle("Exit")
        wind.setIcon(QMessageBox.Question)
        wind.setStandardButtons(QMessageBox.Save | QMessageBox.Ignore | QMessageBox.Cancel)
        wind.setDefaultButton(QMessageBox.Save) 
        wind.buttonClicked.connect(self.popup_button)
        wind.exec_()

    def popup_button(self, button):
        if button.text() == "Save":
            self.configuration.save_config()
        elif button.text() == "Ignore":
            pass
        elif button.text() == "Cancel":
            return
        self.quit()

    def save_close_config(self):
        if self.configuration.save_config():
            self.configuration.close()
        self.menu_bar.configuration_menu.setEnabled(True)
        self.menu_bar.run.setEnabled(True)
    
    def close_config(self):
        self.configuration.close_window()
        self.menu_bar.configuration_menu.setEnabled(True)
        self.menu_bar.run.setEnabled(True)


if __name__ == '__main__':
    from synchronizer import Synchronizer
    app = QApplication(sys.argv)
    synch = Synchronizer()
    gui = GUI()
    gui.show()
    app.exec()