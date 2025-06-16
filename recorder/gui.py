import sys
from threading import Thread
import numpy as np
import multiprocessing as mp
from multiprocessing.sharedctypes import RawArray

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QLineEdit, QHBoxLayout,QWidget,  QMessageBox, QSplitter)

from delsys_recorder import DelsysRecorder
from rgbd_recorder import RgbdRecorder
from trigger_recorder import TriggerRecorder
from utils import LogBox
from configuration import ConfigurationWindow
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
        self.stop = self.run_menu.addAction("Stop")
        self.run.setEnabled(False)
        self.stop.setEnabled(False)
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
        self.setWindowTitle("RGBD recorder")
        self.log_box = None
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self._init_layout()
        self.running = False

        self.trigger_queue = None
        self.delsys_queue = None
        self.delsys_queue_display = None
        self.trigger_queue_display = None
        self.use_trigger = False
        self.trigger_start_event = None
        self.trigger_stop_event = None

        self.refresh_plot = 16  # refresh plot at 60 Hz
        self.buffer_size = 20

        self.configuration = ConfigurationWindow(parent=self, log_box=self.log_box)

        self._create_menu_bar()
        self.trig_tab = None
        self.gognio_tab = None
        self.nb_save_process = 2

        self.show()
        
        self.timer_plot = QTimer(self)
        self.timer_plot.setInterval(self.refresh_plot)
        self.timer_plot.timeout.connect(self.start_timer)


    def _init_layout(self):
        futur_display = QWidget()
        if self.log_box is None:
            self.log_box = LogBox()

        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.log_box.clear)
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_recording)
        self.start_button.setEnabled(False)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(futur_display)
        splitter.addWidget(self.log_box)

        splitter_hor = QSplitter(Qt.Horizontal)
        splitter_hor.addWidget(self.start_button)
        splitter_hor.addWidget(self.stop_button)

        # main_layout = QGridLayout()
        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        main_layout.addWidget(splitter_hor)
        main_layout.addWidget(self.clear_log_button)
        # main_layout.addWidget(splitter, 0, 0, 1, 2)
        # main_layout.addWidget(self.start_button, 1, 0)
        # main_layout.addWidget(self.stop_button, 1, 1)
        # main_layout.addWidget(self.clear_log_button, 2, 0, 1, 2)
        self.central_widget.setLayout(main_layout)
        
    def start_recording(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.trigger_start_event.set()

    def stop_recording(self):
        self.trigger_stop_event.set()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

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
        self.menu_bar.stop.triggered.connect(self.stop)
        self.menu_bar.exit.triggered.connect(self.popup_quit)

    def show_config(self):
        self.menu_bar.enable_run_menu()
        self.menu_bar.run.setEnabled(False)
        self.menu_bar.stop.setEnabled(False)
        self.menu_bar.configuration_menu.setEnabled(False)
        self.menu_bar.save_config.setEnabled(True)
        self.menu_bar.save_config_as.setEnabled(True)
        self.menu_bar.trigger_action.setEnabled(True)
        self.menu_bar.gognio_action.setEnabled(True)
        
        self.configuration.show_config()
    
    def load_config(self):
        self.configuration.load_config()
        self.show_config()

    def _init_mp_var(self):
        self.event_started = [mp.Event()] * (len(self.configuration.get_tab_names()) - 1 + self.nb_save_process)
        
        self.frame_queue = mp.Manager().Queue()

        self.trigger_start_event = mp.Event()
        self.trigger_stop_event = mp.Event()

        self.stop_event = mp.Event()

        self.log_queue = mp.Manager().Queue()

        self.exception_thread = Thread(target=self.exception_handler, daemon=True)
        self.exception_thread.start()

        self.plot_frame_queue = mp.Manager().Queue()

        if self.configuration.trig_tab is not None:
            self.use_trigger = True
            self.trigger_queue = mp.Manager().Queue()

        if self.configuration.delsys_tab is not None:
            self.use_delsys = True
            self.delsys_queue = mp.Manager().Queue()
            self.delsys_queue_display = mp.Manager().Queue()

        image_res = self.configuration.rgbd_tab.get_dict()['image_res'].split('x')
        image_size = (int(image_res[0]), int(image_res[1]))
        color_shape = (image_size[1], image_size[0], 3, self.buffer_size)
        depth_shape = (image_size[1], image_size[0], self.buffer_size)

        color_array = RawArray("c", int(np.prod(color_shape)))  # 'c' = uint8
        depth_array = RawArray("H", int(np.prod(depth_shape))) 
        return color_array, depth_array, color_shape, depth_shape
    
    def exception_handler(self):
        while True:
            try:
                self.log(self.log_queue.get(timeout=0.5))
            except:
                continue

    def start(self):
        self.menu_bar.disable_run_menu()
        self.running = True
        self.start_button.setEnabled(True)
        self.save_directory_base = self.configuration.get_save_directory()

        item = self.central_widget.layout().itemAt(0).widget()
        item.setParent(None)
        self.central_widget.layout().removeWidget(item)

        self.display = Display(self.configuration.config_path, log_box=self.log_box)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.display)
        splitter.addWidget(self.log_box)
        self.central_widget.layout().insertWidget(0, splitter)

        self.log("Starting processes...")

        color_array, depth_array, color_shape, depth_shape = self._init_mp_var()
        
        self.processes = []
        p = mp.Process(target=GUI.get_rgbd, args=(self.save_directory_base, color_array, depth_array,
                                                  self.event_started,
                                                  self.frame_queue,
                                                  self.trigger_start_event,
                                                    self.trigger_stop_event,
                                                   self.stop_event, self.configuration.rgbd_tab.get_dict(), color_shape, depth_shape,
                                                   self.log_queue, self.plot_frame_queue,), daemon=True, name="rgbd")
        self.processes.append(p)

        for i in range(self.nb_save_process):
            p = mp.Process(target=RgbdRecorder.save_rgbd_from_buffer,
                           args=(self.save_directory_base, self.event_started,
                                  self.frame_queue, self.trigger_stop_event,
                                    color_array, depth_array, i,
                                        color_shape, depth_shape, self.log_queue,),
                             daemon=True, name=f"save_{i}")
            self.processes.append(p)

        if self.configuration.delsys_tab is not None:
            p = mp.Process(target=GUI.run_delsys,
                            args=(self.save_directory_base, self.configuration.delsys_tab.get_dict(),
                                  self.trigger_start_event,
                                                    self.trigger_stop_event,
                                                   self.stop_event, 
                                  self.delsys_queue, self.log_queue,), daemon=True, name="save_delsys")
            self.processes.append(p)    

        if self.configuration.trig_tab is not None:
            p = mp.Process(target=GUI.get_trigger,
                            args=(self.save_directory_base, self.configuration.trig_tab.get_dict(),
                                  self.event_started, self.trigger_start_event, self.trigger_stop_event, self.stop_event, self.log_queue,
                                    self.trigger_queue,),
                            daemon=True, name="trigger")
            self.processes.append(p)

        self.log("Starting display...")
        self.display.run(color_array, depth_array, color_shape, depth_shape, self.plot_frame_queue, self.trigger_queue, self.delsys_queue, self.timer_plot)

        self.timer_plot.start()

        self.log("Starting processes...")
        for p in self.processes:
            p.start()
            
        self.log("Programm started. Waiting for data...")

    
    def start_timer(self):
        self.display.tabs[self.display.currentIndex()].update_plot()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        for p in self.processes:
            p.join()
        self.log("All processes stopped.")
        self.menu_bar.enable_run_menu()
        self.menu_bar.run.setEnabled(True)
        self.menu_bar.configuration_menu.setEnabled(True)
        self.menu_bar.stop.setEnable(False)

    def quit(self):
        self.stop()
        self.close()

    def log(self, message):
        if self.log_box is not None:
            self.log_box.log(message)
    
    @staticmethod
    def get_rgbd(save_directory_base, color_array, depth_array, event_started,
                                                  frame_queue,
                                                  trigger_start_event,
                                                    trigger_stop_event, stop_event, config_dict, color_shape, depth_shape, log_queue, plot_queue):
        recorder = RgbdRecorder(save_directory_base, config_dict)
        recorder.get_rgbd(color_array, depth_array, color_shape, depth_shape, trigger_start_event,trigger_stop_event, 
                           frame_queue, log_queue, stop_event, event_started, plot_queue)
    
    @staticmethod
    def run_delsys(save_directory_base, config_dict, trigger_start_event,trigger_stop_event, stop_event, delsys_queue, log_queue):
        delsys = DelsysRecorder(save_directory_base, config_dict)
        delsys.run_delsys(delsys_queue, trigger_start_event,trigger_stop_event, stop_event, log_queue)
    
    @staticmethod
    def get_trigger(save_directory_base, config_dict, event_started,
                                                  trigger_start_event,
                                                    trigger_stop_event, stop_event, log_queue, plot_queue):
        trigger = TriggerRecorder(save_directory_base, config=config_dict)
        trigger.get_trigger(event_started, trigger_start_event, trigger_stop_event, plot_queue, log_queue, stop_event)
    
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
        self.menu_bar.trigger_action.setEnabled(False)
        self.menu_bar.gognio_action.setEnabled(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = GUI()
    gui.show()
    app.exec()