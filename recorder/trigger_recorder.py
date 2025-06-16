from biosiglive import ViconClient, save
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
        self.threeshold = self.config['trigger_threeshold']
        self.less = self.config["condition"] == "lesser than"

    def _init_trigger(self):
        self.interface = ViconClient(ip=self.ip, port=self.vicon_port, init_now=True)

    def get_trigger(self, event_started, trigger_start_event, trigger_stop_event, queue_trig=None, exception_queue=None, stop_event=None):
        try:
            if self.use_trigger:
                self._init_trigger()
                self.interface.get_frame()
                self.interface.add_device(
                    nb_channels=1,
                    name=self.trigger_channel,
                )
                comparator_func = np.less if self.less else np.greater
            self.counter = time.perf_counter
            event_started.set()
            count = 0
            while True:
                if self.use_trigger:
                    trigger_data = self.interface.get_device_data(device_name=self.trigger_channel)
                    if trigger_data is None:
                        continue
                    queue_trig.put_nowait(trigger_data[0], self.counter())
                    is_triggered = np.argwhere(comparator_func(trigger_data[0], self.threeshold) == True).shape[0]
                    if is_triggered and not self.trigger_start_event.is_set():
                        trigger_start_event.set()
                        exception_queue.put_nowait("start recording...")
                    if trigger_start_event.is_set() and count < 150:
                        count += 1
                    elif is_triggered and trigger_start_event.is_set() and count > 100:
                        trigger_stop_event.set()
                        print("stop recording...")
                        break
                if stop_event.is_set():
                    break
        except Exception as e:
            exception_queue.put_nowait(e)

    def _process_data(self, data, timestamp):
        if self.use_trigger:
            save({'trigger': data, "timestamp": timestamp}, self.save_file_path)

        return data
                        