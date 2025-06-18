import os
import threading
from pytrigno import TrignoSDKClient
from biosiglive import save

class Sensor:
    def __init__(self):
        self.name = None
        self.type = None
        self.rate = None
        self.idx = None
    
    def from_dict(self, data):
        self.name = data.get("name", None)
        self.type = data.get("data_type", None)
        self.idx = data.get("sensor_idx", None)


class DelsysRecorder:
    def __init__(self, save_directory, config: dict):
        self.save_directory_base = save_directory
        self.save_directory = os.path.join(save_directory, "delsys_data")
        self.save_file_path = os.path.join(self.save_directory, f"_raw_data.bio")
        self.config = config
        self._from_config()
        self.sensors = []

    def _from_config(self):
        self.adress = self.config.get("delsys_adress", "127.0.0.1")
        for device in self.config.get("devices", []):
            sensor = Sensor()
            sensor.from_dict(device)
            self.sensors.append(sensor)

    def init_delsys(self, adress="127.0.0.1"):
        self.sdk_client = TrignoSDKClient(ip=adress)
        self.sdk_client.connect()

    def run_delsys(self, event_started, plot_delsys_queue, trigger_start_event, trigger_stop_event, stop_event, exception_queue):
        self.plot_queue = plot_delsys_queue
        self.stop_envent = stop_event
        self.trigger_start_event = trigger_start_event
        self.trigger_stop_event = trigger_stop_event
        self.sensors_names = [s.name for s in self.sensors]
        try:
            if not self.sdk_client.is_connected:
                self.init_delsys(self.adress)
            self._listen_threads()
            event_started.set()
        except Exception as e:
            exception_queue.put(e)

    def _listen_threads(self):
        self.threads = []
        for name, queue in self.sdk_client.all_queue.items():
            if queue is None:
                continue
            thread = threading.Thread(target=self._listen_queue, args=(queue, name), daemon=True)
            thread.start()

    def _listen_queue(self, queue, name):
        while self.trigger_stop_event.is_set() is False:
            try:
                data = queue.get(timeout=2)
                self._process_data(data, name)
            except Exception as e:
                continue

    def _process_data(self, data, name):
        data, timestamp = data
        self.plot_queue.put_nowait(data)
        if self.trigger_start_event.is_set():
            self._save_data(data, name, timestamp)
    
    def _save_data(self, data, name, timestamp):
        save({f"{name}": data, "timestamp": timestamp, 'channel_names': self.sensors_names},
              self.save_file_path,
                add_data=True)

