import time
import pyrealsense2 as rs
import numpy as np
import cv2
import os
import json


class RgbdRecorder:
    def __init__(self, save_directory, config: dict):
        self.save_directory_base = save_directory
        self.save_directory = os.path.join(save_directory, "rgbd_data")
        
        self.init_camera_pipeline()
        pass

    def init_camera_pipeline(self):
        self.pipeline = rs.pipeline()
        config = rs.config()
        pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
        pipeline_profile = config.resolve(pipeline_wrapper)
        device = pipeline_profile.get_device()
        device_product_line = str(device.get_info(rs.camera_info.product_line))
        config.enable_stream(rs.stream.depth, self.size[1], self.size[0], rs.format.z16, self.fps)
        config.enable_stream(rs.stream.color, self.size[1], self.size[0], rs.format.bgr8, self.fps)
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
        congif_dir = "config_camera_files"
        align_to = rs.stream.color
        self.align = rs.align(align_to)
        os.makedirs(f'{self.save_directory}\{congif_dir}', exist_ok=True)
        with open(f"{self.save_directory}\{congif_dir}\{self.config_file_name}", "w") as outfile:
            json.dump(self.dic_config_cam, outfile, indent=4)

    def get_images(self):
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
        # Configure depth and color streams
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
    def save_rgbd_from_buffer(save_path, event_started, frame_queue, trigger_stop_event, shared_color, shared_depth, i, color_shape, depth_shape):
        shared_color = np.frombuffer(shared_color, dtype=np.uint8).reshape(color_shape)
        shared_depth = np.frombuffer(shared_depth, dtype=np.uint16).reshape(depth_shape)
        # path = f"{self.save_directory}\{self.participant}\{self.file_name}_{self.date_time}"
        path = save_path
        os.makedirs(path, exist_ok=True)
        event_started[i].set()
        count = 0
        while True:
            try:
                queue = frame_queue.get(timeout=0.005)
            except:
                if trigger_stop_event.is_set():
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
        print(f"{count} frame saved by the {i} process")


    def get_rgbd(self, shared_color, shared_depth):
        shared_color = np.frombuffer(shared_color, dtype=np.uint8).reshape((self.color_shape))
        shared_depth = np.frombuffer(shared_depth, dtype=np.uint16).reshape((self.depth_shape))
        if not self.from_bag_file:
            self.init_camera_pipeline()
        else:
            self._init_bag_file()
        loop_time_list = []
        buffer_idx = 0
        count = 0
        self.wait_all()
        while True:
            if self.trigger_stop_event.is_set():
                break
            tic = time.time()
            color_image, depth_image, frame_number = self.get_images()
            if color_image is None:
                continue
            fps = 1 / np.mean(loop_time_list[-20:])

            self.show_cv2_images(color_image, depth_image, frame_number, fps)
            # if not self.trigger_start_event.is_set() and self.show_images:
            #     fps = 1 / np.mean(loop_time_list[-20:])
            #     self.show_cv2_images(color_image, depth_image, frame_number, fps)
            if self.trigger_start_event.is_set():
                # if count == 0:
                #     cv2.destroyAllWindows()
                buffer_idx = frame_number % self.buffer_size
                # self.set_shared_memory_images(shared_color, shared_depth, color_image, depth_image, buffer_idx)
                self.frame_queue.put_nowait((frame_number, buffer_idx))
                count += 1
            loop_time_list.append(time.time() - tic)

        print(f"stop recording...nb frame: {count}, in {np.array(loop_time_list).sum():.2f}\n" 
              "Wait until all data are saved")
        cv2.destroyAllWindows()
        
        self.pipeline.stop()