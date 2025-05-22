from biosiglive import ViconClient
import time
import numpy as np
import os


class TriggerRecorder:
    def __init__(self, save_directory, config: dict):
        self.save_directory_base = save_directory
        self.save_directory = os.path.join(save_directory, "trigger_data")
        self.use_trigger = True
    
    def init_trigger(self, ip="127.0.0.1"):

        if not self.use_trigger:
            return
        
        self.interface = ViconClient(ip=ip, init_now=True)


    def get_trigger(self, chanel_name="trigger", threeshold=5.215, ip="127.0.0.1", less=True, queue_trig=None):
        if self.use_trigger:
            self.init_trigger(ip)
            self.interface.get_frame()
            self.interface.add_device(
                nb_channels=1,
                name=chanel_name,
            )
            comparator_func = np.less if less else np.greater
            
        init_time = time.time()
        self.event_started[0].set()
        is_started=False
        count = 0
        while True:
            if self.use_trigger:
                trigger_data = self.interface.get_device_data(device_name="trigger")
                if trigger_data is None:
                    continue
                queue_trig.put_nowait(trigger_data[0])
                is_triggered = np.argwhere(comparator_func(trigger_data[0], threeshold) == True).shape[0]
                if is_triggered and not self.trigger_start_event.is_set():
                    self.trigger_start_event.set()
                    print("start recording...")
                if self.trigger_start_event.is_set() and count < 150:
                    count += 1
                elif is_triggered and self.trigger_start_event.is_set() and count > 100:
                    self.trigger_stop_event.set()
                    print("stop recording...")
                    break
            else:
                time.sleep(0.005)
                delay = time.time() - init_time
                if not is_started and delay > self.start_delay:
                    self.trigger_start_event.set()
                    print("start recording...")
                    init_time = time.time()
                    is_started = True
                elif delay > self.stop_delay and is_started:
                        self.trigger_stop_event.set()
                        break