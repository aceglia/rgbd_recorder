from operator import is_
import queue
from sqlite3.dbapi2 import Timestamp
from biosiglive import ViconClient, save, DeviceType
import time
import numpy as np
import os



class TriggerRecorder:
    def __init__(self, save_directory, config: dict):
        self.save_directory_base = save_directory
        self.save_directory = os.path.join(save_directory, "trigger_data")
        self.save_file_path = os.path.join(self.save_directory, f"_raw_data.bio")
        self.config = config
        self._from_config()
    
    def _from_config(self):
        self.trigger_channel = self.config["trigger_channel"]
        self.ip = self.config['vicon_adress']
        self.vicon_port = self.config['vicon_port']
        self.threeshold = self.config['trigger_threshold']
        self.less = self.config["condition"] == "lesser than"

    def _init_trigger(self):
        self.interface = ViconClient(system_rate=100, ip=self.ip, port=self.vicon_port, init_now=True)

    def get_trigger(self, event_started, trigger_start_event, trigger_stop_event, queue_trig, exception_queue, stop_event):
        # try:
        self._init_trigger()
        self.interface.get_frame()
        self.interface.add_device(
            nb_channels=1,
            name=self.trigger_channel,
            rate=2000,
            device_type=DeviceType.Generic
        )
        comparator_func = np.less if self.less else np.greater
        self.counter = time.perf_counter
        count = 0
        os.makedirs(self.save_directory, exist_ok=True)
        while True:
            trigger_data = self.interface.get_device_data(device_name=self.trigger_channel)
            if trigger_data is None:
                continue
            timestamp = self.counter()
            try:
                queue_trig.get_nowait()
            except:
                pass
            queue_trig.put_nowait(trigger_data[0])
            is_triggered = np.argwhere(comparator_func(trigger_data[0], self.threeshold) == True).shape[0]
            if is_triggered and not trigger_start_event.is_set():
                trigger_start_event.set()
                exception_queue.put_nowait("start recording...")
            if is_triggered and trigger_start_event.is_set():
                self._process_data(trigger_data[0], timestamp)
            if trigger_start_event.is_set() and count < 150:
                count += 1
            elif is_triggered and trigger_start_event.is_set() and count > 100:
                trigger_stop_event.set()
                print("stop recording...")
                break
            if stop_event.is_set():
                break
        #     if stop_event.is_set():
        # except Exception as e:
        #     exception_queue.put_nowait(e)

    def _process_data(self, data, timestamp):
        save({'trigger': data, "timestamp": timestamp}, self.save_file_path, add_data=True)
                        