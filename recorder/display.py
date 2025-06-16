import json
import time
from turtle import color
from PyQt5.QtWidgets import QTabWidget, QMainWindow, QApplication
from display_utils import ImageTab, CurveTab
from PyQt5.QtCore import QTimer
import multiprocessing as mp
from multiprocessing.sharedctypes import RawArray
import numpy as np

class DymmyReccorder(QMainWindow):
    def __init__(self, config_file):
        super().__init__()
        self.setWindowTitle("Dummy Reccorder")

        self.display = Display(config_file)
        self.setCentralWidget(self.display)

        self.show()

        self.queue_delsys = mp.Queue()
        self.queue_trigger = mp.Queue()
        self.timer = QTimer(self)
        self.timer.setInterval(16)  # ms
        self.timer.timeout.connect(self.start_timer)
   
    
    def generate_data(n_curve, color_array, depth_array, queue_trigger, queue_delsys):
        size_rgbd = (3, 460, 848)
        depth_shape = (460, 848)
        shared_color = np.frombuffer(color_array, dtype=np.uint8).reshape(size_rgbd)
        shared_depth = np.frombuffer(depth_array, dtype=np.uint16).reshape(depth_shape)
        while True:
            rand_color = np.random.randint(0, 255, size=size_rgbd, dtype=np.uint8)
            rand_depth = np.random.randint(0, 65535, size=depth_shape, dtype=np.uint16)
            np.copyto(shared_color, rand_color)
            np.copyto(shared_depth, rand_depth)
            rand_trigger = np.random.randn(1, 10)
            queue_trigger.put_nowait(rand_trigger)
            rand_delsys = np.random.randn(n_curve, 10)
            queue_delsys.put_nowait(rand_delsys)

        
    def start(self):
        self.color_shape = np.prod((3, 460, 848))
        self.depth_shape = np.prod((460, 848))
        color_array = RawArray("c", int(np.prod(self.color_shape)))  # 'c' = uint8
        depth_array = RawArray("H", int(np.prod(self.depth_shape)))  # 'H' = uint16     
        self.data_generator = mp.Process(target=DymmyReccorder.generate_data, args=(2, color_array, depth_array, self.queue_trigger, self.queue_delsys,))
        # self.diplay_process = mp.Process(target=Display.run, args=(color_array, depth_array, self.queue_trigger, self.queue_delsys))
        self.data_generator.start()
        self.display.run(color_array, depth_array, self.queue_trigger, self.queue_delsys)

        self.timer.start()
        # self.diplay_process.start()
    

    def start_timer(self):
        self.display.tabs[self.display.currentIndex()].update_plot()

    def stop(self):
        self.data_generator.terminate()
        self.diplay_process.terminate()
        self.data_generator.join()
        self.diplay_process.join()




class Display(QTabWidget):
    def __init__(self, config_file, log_box):
        super().__init__()
        self.queue_current_tab = mp.Queue()
        # get current tab index
        # self.currentChanged.connect(self.on_current_tab)
        # self.currentChanged.connect(self.on_curent_tab)
        self.setTabsClosable(False)
        self.log_box = log_box

        self.on_curent_tab = config_file
        with open(config_file, 'r') as f:
            self.config = json.load(f)

        self.init_tab_layout(self.config)
    
    def run(self, color_array, depth_array, queue_trigger, queue_delsys, timer):
        res = self.config["RGBD"]['image_res'].split('x')
        w, h = int(res[1]), int(res[0]) 
        size_rgbd = (3, w, h)
        depth_shape = (w, h)
        shared_color = np.frombuffer(color_array, dtype=np.uint8).reshape(size_rgbd)
        shared_depth = np.frombuffer(depth_array, dtype=np.uint16).reshape(depth_shape)
        for tab in self.tabs:
            if tab.name == 'rgbd':
                tab.set_data(shared_color, shared_depth)
            elif tab.name == 'trigger':
                tab.set_data(queue_trigger)
            elif tab.name == 'delsys':
                tab.set_data(queue_delsys)
        self.timer_plot.timeout.connect(self.start_timer)

    def start_timer(self):
        self.tabs[self.currentIndex()].update_plot()

    def print_idx(self):
        print(self.currentIndex())

    def init_tab_layout(self, config):
        self.tabs = []
        for tab_name, tab_content in config.items():
            self._append_tab(tab_name, tab_content)
    
    def _append_tab(self, tab_name, tab_content):
        tab_name = tab_name.lower()
        curve_tab_names = ["trigger", "delsys"]
        image_tab_names = ["rgbd"]
        if tab_name not in curve_tab_names and tab_name not in image_tab_names:
            return
        tab = CurveTab if tab_name in curve_tab_names else ImageTab
        self.tabs.append(tab(tab_name, tab_content))
        self.addTab(self.tabs[-1], tab_name)

    def on_current_tab(self):
        self.queue_current_tab.put_nowait(self.currentWidget())


if __name__ == '__main__':
    import sys
    conf_file = r"D:\Documents\Programmation\rgbd_reccorder\data\test\config.json"
    app = QApplication(sys.argv)
    gui = DymmyReccorder(conf_file)
    gui.start()
    app.exec()



