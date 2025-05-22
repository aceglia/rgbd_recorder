from datetime import datetime
import queue
from threading import Thread
import tkinter as tk

import os
from tkinter import filedialog
from tkinter import scrolledtext
import cv2
import pyrealsense2 as rs
import numpy as np
import json
import datetime
from biosiglive import ViconClient, DeviceType
import multiprocessing as mp
from multiprocessing import RawArray
import time


class Synchronizer:
    def __init__(self, use_trigger=True, fps=60, show_images=True, buffer_size=30, 
                 start_delay=0, stop_delay=200, from_bag_file=False, bag_path="", n_save_process=3, save_directory=""):
        
        self.from_bag_file = from_bag_file
        self.bag_file_path = bag_path
        self.show_images = show_images
        self.buffer_size = buffer_size
        self.start_delay = start_delay
        self.stop_delay = stop_delay
        self.pipeline = None
        self.participant = None
        self.align = None
        self.dic_config_cam = {}
        self.interface = None
        self.use_trigger = use_trigger
        self.file_name = "data"
        self.config_file_name = None
        self.event_started = [mp.Event()] * (n_save_process + 1)
        self.save_directory = save_directory

        now = datetime.datetime.now()
        self.date_time = now.strftime("%d-%m-%Y_%H_%M_%S")
        self.nb_save_process = n_save_process
        self.buffer_size = max(self.buffer_size, self.nb_save_process)
        self.fps = fps
        self.frame_queue = mp.Queue()

        self.trigger_start_event = mp.Event()
        self.trigger_stop_event = mp.Event()
        # self.size = (480, 848)
        self.size = (480, 640)

        self.color_shape = self.size + (3, self.buffer_size)
        self.depth_shape = self.size + (self.buffer_size,)
        self.stop_event = mp.Event()

    def wait_all(self):
        for i in range(len(self.event_started)):
            self.event_started[i].wait()
        return

    def start(self):
        color_array = RawArray("c", int(np.prod(self.color_shape)))  # 'c' -> value between 0-255
        depth_array = RawArray("H", int(np.prod(self.depth_shape)))  # 'H' -> uint16
        processes = []
        p = mp.Process(target=Synchronizer.get_rgbd, args=(self, color_array, depth_array,), daemon=True, name="rgbd")
        processes.append(p)
        # for i in range(self.nb_save_process):
        #     p = mp.Process(target=Synchronizer.save_rgbd_from_buffer, args=(self, color_array, depth_array, i,), daemon=True, name=f"save_{i}")
        #     processes.append(p)
        p = mp.Process(target=Synchronizer.get_trigger, args=(self,), daemon=True, name="triger")
        processes.append(p)
        for p in processes:
            p.start()
        for p in processes:
            p.join()
        print("All process stopped")
        return
    


class GUI:
    def __init__(self, synch):
        self.root =  tk.Tk()
        self.sync = synch
        self.root.title("Annotation tool")
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self._create_layout_objects()

    def _create_layout_objects(self):
        self.button_stop_trig = tk.Button(master=self.root, text="Stop\nrecording", command=self.send_trig_stop)
        self.button_stop = tk.Button(master=self.root, text="Quit", command=self.quit)
        self.button_run = tk.Button(master=self.root, text="Run", command=self.start)
        self.button_start_trig = tk.Button(master=self.root, text="Send\ntrig", command=self.send_trig_start)
        self.button_open_file = tk.Button(master=self.root, text="Open file", command=self.get_file_path)
        self.log_box = scrolledtext.ScrolledText(self.root, height=8, width=60, state=tk.DISABLED)
        sticky=tk.E
        padx = 5
        pady = 5
        self.button_open_file.grid(row=0, column=0, padx=padx, pady=pady, sticky=sticky)
        self.button_run.grid(row=1, column=1, padx=padx, pady=pady, sticky=sticky)
        self.button_start_trig.grid(row=1, column=0, padx=padx, pady=pady, sticky=sticky)
        self.button_stop_trig.grid(row=2, column=0, padx=padx, pady=pady, sticky=sticky)
        self.button_stop.grid(row=2, column=1, padx=padx, pady=pady, sticky=sticky)
        self.log_box.grid(row=3, column=0, columnspan=2, padx=padx, pady=pady, sticky=sticky)

    def get_file_path(self):
        self.save_directory = filedialog.askdirectory()


    def send_trig_start(self):
        self.trig_start.set()
        print("start recording...")
        

    def send_trig_stop(self):
        self.trig_stop.set()
        print("stop recording...")

    def start(self):
        color_array = RawArray("c", int(np.prod(self.sync.color_shape)))  # 'c' -> value between 0-255
        depth_array = RawArray("H", int(np.prod(self.sync.depth_shape)))  # 'H' -> uint16
        self.trig_start = sync.trigger_start_event
        self.trig_stop = sync.trigger_stop_event
        self.trig_start.clear()
        self.trig_stop.clear()
        self.processes = []
        p = mp.Process(target=Synchronizer.get_rgbd, args=(self.sync, color_array, depth_array,), daemon=True, name="rgbd")
        self.processes.append(p)
        for i in range(self.sync.nb_save_process):
            p = mp.Process(target=Synchronizer.save_rgbd_from_buffer, args=(self.sync, color_array, depth_array, i,), daemon=True, name=f"save_{i}")
            self.processes.append(p)
        for p in self.processes:
            p.start()
        return
    
    def quit(self):
        for p in self.processes:
            p.join()
        print("All process stopped")
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    sync = Synchronizer(use_trigger=False, start_delay=1, stop_delay=5, from_bag_file=True, 
                        bag_path=r"test.bag", n_save_process=3, show_images=True,
                        #   save_directory=r"C:\Users\Usager\Documents\amedeo\rgbd_data",
                          save_directory=r"D:\Documents\Programmation\rgbd_reccorder\data",
                        )
    sync.fps = 60
    sync.file_name = "test"
    sync.participant = "P00"
    gui = GUI(sync) 
    gui.root.mainloop()
    sync.start()
