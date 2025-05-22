import numpy as np
import multiprocessing as mp
from multiprocessing.sharedctypes import RawArray
from PyQt5.QtWidgets import QMainWindow, QTimer
from recorder.display import Display



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