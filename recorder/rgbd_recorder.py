from operator import is_
import time
from tracemalloc import stop
import pyrealsense2 as rs
import numpy as np
import cv2
import os
import json

from utils import set_shared_memory_images, show_cv2_images


class RgbdRecorder:
    def __init__(self, save_directory_base, config: dict):
        self.trial_queue = save_directory_base
        self.save_directory_base = self.trial_queue.get()
        self.trial_queue.put_nowait(self.save_directory_base)
        self.config = config
        self._from_config()
        self.save_directory = os.path.join(self.save_directory_base, "rgbd_data")
        self.log_file = os.path.join(self.save_directory, "log.txt")
        self.date_time = time.strftime("%Y%m%d_%H%M%S")
    
    def _from_config(self):
        self.size = self.config["image_res"].split("x")
        self.size = (int(self.size[0]), int(self.size[1]))
        self.fps = int(self.config["camera_fps"])

    def init_camera_pipeline(self):
        self.pipeline = rs.pipeline()
        config = rs.config()
        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        pipeline_profile = config.resolve(pipeline_wrapper)
        device = pipeline_profile.get_device()
        device_product_line = str(device.get_info(rs.camera_info.product_line))
        config.enable_stream(rs.stream.depth, self.size[0], self.size[1], rs.format.z16, self.fps)
        config.enable_stream(rs.stream.color, self.size[0], self.size[1], rs.format.bgr8, self.fps)
        # config.enable_record_to_file('test.bag')
        self.pipeline.start(config)
        d_profile = self.pipeline.get_active_profile().get_stream(rs.stream.depth).as_video_stream_profile()
        d_intr = d_profile.get_intrinsics()
        scale = self.pipeline.get_active_profile().get_device().first_depth_sensor().get_depth_scale()
        c_profile = self.pipeline.get_active_profile().get_stream(rs.stream.color).as_video_stream_profile()
        c_intr = c_profile.get_intrinsics()
        deth_to_color = d_profile.get_extrinsics_to(c_profile)
        r = np.array(deth_to_color.rotation).reshape(3, 3)
        t = np.array(deth_to_color.translation)

        self.dic_config_cam = {
            "camera_name": device_product_line,
            "depth_scale": scale,
            "depth_fx_fy": [d_intr.fx, d_intr.fy],
            "depth_ppx_ppy": [d_intr.ppx, d_intr.ppy],
            "color_fx_fy": [c_intr.fx, c_intr.fy],
            "color_ppx_ppy": [c_intr.ppx, c_intr.ppy],
            "depth_to_color_trans": t.tolist(),
            "depth_to_color_rot": r.tolist(),
            "model_color": c_intr.model.name,
            "model_depth": d_intr.model.name,
            "dist_coeffs_color": c_intr.coeffs,
            "dist_coeffs_depth": d_intr.coeffs,
            "size_color": [c_intr.width, c_intr.height],
            "size_depth": [d_intr.width, d_intr.height],
            "color_rate": c_profile.fps(),
            "depth_rate": d_profile.fps(),
        }

        self.config_file_name = f"config_camera_{self.date_time}.json"
        align_to = rs.stream.color
        self.align = rs.align(align_to)
        os.makedirs(f'{self.save_directory}', exist_ok=True)
        with open(f"{self.save_directory}\{self.config_file_name}", "w") as outfile:
            json.dump(self.dic_config_cam, outfile, indent=4)

    def _get_images(self):
        try:
            aligned_frames = self.pipeline.wait_for_frames()
        except:
            return None, None, None

        aligned_frames = self.align.process(aligned_frames)
        aligned_depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()
        if not aligned_depth_frame or not color_frame:
            return None, None, None
        frame_number = color_frame.frame_number
        depth_image = np.asanyarray(aligned_depth_frame.get_data()).astype(np.uint16)
        color_image = np.asanyarray(color_frame.get_data())
        return color_image, depth_image, frame_number
    

    def _init_bag_file(self):
        self.pipeline = rs.pipeline()
        config = rs.config()
        config.enable_device_from_file(self.bag_file_path, repeat_playback=False)
        config.enable_all_streams()
        self.pipeline.start(config)
        device = self.pipeline.get_active_profile().get_device()
        playback = device.as_playback()
        playback.set_real_time(False)
        align_to = rs.stream.color
        self.align = rs.align(align_to)

    @staticmethod
    def save_rgbd_from_buffer(save_path, event_started, frame_queue, trigger_stop_event, shared_color, shared_depth, i, color_shape, depth_shape, exception_queue, stop_event):
        try:
            shared_color = np.frombuffer(shared_color, dtype=np.uint8).reshape(color_shape)
            shared_depth = np.frombuffer(shared_depth, dtype=np.uint16).reshape(depth_shape)
            # path = f"{self.save_directory}\{self.participant}\{self.file_name}_{self.date_time}"
            
            path = os.path.join(save_path.get(), "rgbd_data")
            os.makedirs(path, exist_ok=True)
            event_started.set()
            count = 0
            stop_count = 0
            while True:
                try:
                    queue = frame_queue.get(timeout=0.005)
                    stop_count = 0
                except:
                    if trigger_stop_event.is_set():
                        if stop_count == 0:
                            save_dir = save_path.get()
                            save_path.put_nowait(save_dir)
                            path = os.path.join(save_dir, "rgbd_data")
                            print(path)
                            os.makedirs(path, exist_ok=True)
                            stop_count += 1
                        else:
                            pass
                    elif stop_event.is_set():
                        break
                    continue
                count +=1
                shared_idx = queue[1]
                frame_number = queue[0]
                depth_image = shared_depth[..., shared_idx]
                color_image = shared_color[..., shared_idx]
                cv2.imwrite(
                        f"{path}\depth_{frame_number}.png",
                        depth_image,
                    )
                cv2.imwrite(
                        f"{path}\color_{frame_number}.png",
                        cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB),
                    )
        except Exception as e:
            exception_queue.put_nowait(e)

    def wait_all(self, event_list):
        for event in event_list:
            event.wait()

    def get_rgbd(self, shared_color, shared_depth, color_shape, depth_shape,trigger_start_event, trigger_stop_event, frame_queue, exception_queue, stop_event, event_started,
                  plot_queue):
        # try:
        buffer_size = color_shape[-1]
        shared_color = np.frombuffer(shared_color, dtype=np.uint8).reshape(color_shape)
        shared_depth = np.frombuffer(shared_depth, dtype=np.uint16).reshape(depth_shape)
        self.init_camera_pipeline()
        loop_time_list = []
        buffer_idx = 0
        count = 0
        # self.wait_all(event_started)
        self.counter = time.perf_counter
        while True:
            if stop_event.is_set():
                break
            tic = time.time()
            color_image, depth_image, frame_number = self._get_images()
            timestamp = self.counter()
            if color_image is None:
                continue
            # fps = 1 / np.mean(loop_time_list[-20:])
            # show_cv2_images(color_image, depth_image, frame_number, fps)
            # if not self.trigger_start_event.is_set() and self.show_images:
            #     fps = 1 / np.mean(loop_time_list[-20:])
            #     self.show_cv2_images(color_image, depth_image, frame_number, fps)
            buffer_idx = frame_number % buffer_size
            set_shared_memory_images(shared_color, shared_depth, color_image, depth_image, buffer_idx)
            try:
                plot_queue.get_nowait()
            except:
                pass
            plot_queue.put_nowait((frame_number, buffer_idx))
            count += 1

            if trigger_start_event.is_set():
                frame_queue.put_nowait((frame_number, buffer_idx))
                self.save_log(frame_number, timestamp)
            loop_time_list.append(time.time() - tic)
            
        self.pipeline.stop()

        # except Exception as e:
        #     print(f"Exception in get_rgbd: {e}")
        #     exception_queue.put_nowait(e)

    def save_log(self, frame_number, timestamp):
        with open(self.log_file, "a") as f:
            f.write(f"{frame_number},{timestamp}\n")
