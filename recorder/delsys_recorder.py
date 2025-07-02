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
        self.trial_queue = save_directory
        self.save_directory_base = self.trial_queue.get(timeout=0.5)
        self.trial_queue.put_nowait(self.save_directory_base)
        self.save_directory = os.path.join(self.save_directory_base, "delsys_data")
        self.save_file_path = os.path.join(self.save_directory, f"_raw_data.bio")
        self.config = config
        self.sensors = []
        self.sdk_client = None

        self._from_config()

    def _from_config(self):
        self.adress = self.config.get("delsys_adress", "127.0.0.1")
        for device in self.config.get("devices", []):
            sensor = Sensor()
            sensor.from_dict(device)
            self.sensors.append(sensor)

    def init_delsys(self, adress="127.0.0.1"):
        self.sdk_client = TrignoSDKClient(host=adress)
        self.sdk_client.connect()
        self.sdk_client.start_streaming()

    def run_delsys(self, event_started, plot_delsys_queue_emg, plot_delsys_queue_aux, trigger_start_event, trigger_stop_event, stop_event, exception_queue):
        self.plot_queue_emg = plot_delsys_queue_emg
        self.plot_queue_aux = plot_delsys_queue_aux
        self.stop_event = stop_event
        self.trigger_start_event = trigger_start_event
        self.trigger_stop_event = trigger_stop_event
        self.sensors_names = [s.name for s in self.sensors]
        os.makedirs(self.save_directory, exist_ok=True)
        try:
            if not self.sdk_client:
                self.init_delsys(self.adress)
            self._listen_threads()
            event_started.set()
        except Exception as e:
            exception_queue.put(e)

    def _listen_threads(self):
        self.threads = []
        for name, socket in self.sdk_client.all_socket.items():
            if not socket:
                continue
            thread = threading.Thread(target=self._listen_queue, args=(self.sdk_client.all_queue[name], name, self.trial_queue), daemon=True)
            thread.start()
            self.threads.append(thread)
    
    def stop_threads(self):
        for thread in self.threads:
            thread.join()

    def _listen_queue(self, queue, name, trial_queue):
        plot_queue = self.plot_queue_emg if "emg" in name else self.plot_queue_aux
        stop_count = 0
        while True:
            try:
                data = queue.get(timeout=0.1)
                if plot_queue is not None:
                    try:
                        plot_queue.get_nowait()
                    except:
                        pass
                    plot_queue.put_nowait(data[0])
                if self.trigger_start_event.is_set():
                    stop_count = 0
                    self._process_data(data, name)
                elif self.trigger_stop_event.is_set():
                    if stop_count == 0:
                        save_dir = trial_queue.get()
                        trial_queue.put_nowait(save_dir)
                        self.save_directory = os.path.join(save_dir, "delsys_data")
                        self.save_file_path = os.path.join(self.save_directory, f"_raw_data.bio")
                        os.makedirs(self.save_directory, exist_ok=True)
                        stop_count += 1
                    else:
                        pass

            except Exception as e:
                continue
            if self.stop_event.is_set():
                break

    def _process_data(self, data, name):
        data, timestamp = data
        self._save_data(data, name, timestamp)
    
    def _save_data(self, data, name, timestamp):
        save({f"{name}": data, "timestamp": timestamp, 'channel_names': self.sensors_names},
              self.save_file_path,
                add_data=True)

