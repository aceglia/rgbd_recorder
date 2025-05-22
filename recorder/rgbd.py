from PyQt5.QtWidgets import QWidget, QPushButton, QDesktopWidget, QPlainTextEdit, QGridLayout, QCheckBox, QLabel, QComboBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
import numpy as np
from enums import ImageResolution
import pyrealsense2 as rs
from utils import log
from threading import Thread
import time 

class RgbdWindow(QWidget):
    def __init__(self, log_box):
        super(RgbdWindow, self).__init__()
        self.label = QLabel(self)
        # self.label.setMinimumSize(300, 300)
        screen = QDesktopWidget().screenGeometry()
        screen_width = screen.width()
        screen_height = screen.height()
        self.log_box = log_box

        self._create_layout_objects()

    def _create_layout_objects(self):
        self.image_res_list = QComboBox()
        self.image_res_label = QLabel("Image Resolution")
        self.image_res_list.addItems(ImageResolution.list())
        self.image_fps_label = QLabel("Camera FPS")
        self.camera_fps_list = QComboBox()
        self.camera_fps_list.addItems(["15", "30", "60", "90"])
        self.try_config_button = QPushButton("Try Configuration")
        self.try_config_button.clicked.connect(self.try_config)

        layout = QGridLayout()
        layout.addWidget(self.image_res_label, 0, 0, 1, 1)
        layout.addWidget(self.image_res_list, 0, 1, 1, 1)
        layout.addWidget(self.image_fps_label, 0, 2, 1, 1)
        layout.addWidget(self.camera_fps_list, 0, 3, 1, 1)
        layout.addWidget(self.try_config_button, 0, 4, 1, 1)
        layout.addWidget(self.label, 1, 0, 1, 5)

        self.setLayout(layout)

    def get_dict(self):
        return {
            "image_res": self.image_res_list.currentText(),
            "camera_fps": self.camera_fps_list.currentText()
        }

    def from_dict(self, data):
        self.image_res_list.setCurrentText(data["image_res"])
        self.camera_fps_list.setCurrentText(data["camera_fps"])

    def update_image(self):
        """This function will resize the image and save it
        into the 'resized_image' variable this function
        is only for display purposes.
        """
        if self.image is None:
            return
        format = QImage.Format_RGB888 if len(self.image.shape) == 3 else QImage.Format_Grayscale8
        image = QImage(self.image, self.image.shape[1], self.image.shape[0], self.image.strides[0], format)

        self.resized_image = QPixmap.fromImage(image).scaled(
            self.label.size().width(), self.label.size().height(), Qt.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        
        self.pixmap = QPixmap.fromImage(image)

        # If successful apply the image to the QLabel
        self.label.setPixmap(self.pixmap)

    def set_image(self, image, depth):
        """
        Set the current image of the VideoCropper with
        the given image param and update the image afterward
        """
        self.image = image
        self.depth = depth

        self.update_image()


    def init_camera_pipeline(self):
        try: 
            self.pipeline = rs.pipeline()
            config = rs.config()
            pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
            pipeline_profile = config.resolve(pipeline_wrapper)
            device = pipeline_profile.get_device()
            device_product_line = str(device.get_info(rs.camera_info.product_line))
            config.enable_stream(rs.stream.depth, self.size[1], self.size[0], rs.format.z16, self.fps)
            config.enable_stream(rs.stream.color, self.size[1], self.size[0], rs.format.bgr8, self.fps)
            self.pipeline.start(config)
            align_to = rs.stream.color
            self.align = rs.align(align_to)

            self.log(self.log_box, f"{device_product_line} camera initialized with resolution {self.size[1]}x{self.size[0]} and FPS {self.fps}")
        except Exception as e:
            self.log(self.log_box, "Error while initializing camera pipeline: " + str(e))

    def read_images(self):
        try:
            frames = self.pipeline.wait_for_frames()
            aligned_frames = self.align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            if not depth_frame or not color_frame:
                return None, None
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            return color_image, depth_image
        except Exception as e:
            self.log(self.log_box, "Error while reading images: " + str(e))
            return None, None

    def try_config(self):
        
        self.size = (int(self.image_res_list.currentText().split("x")[0]), int(self.image_res_list.currentText().split("x")[1]))
        self.fps = int(self.camera_fps_list.currentText())
        self.image = np.random.randint(0, 255, (self.size[1], self.size[0], 3), dtype=np.uint8)
        # self.init_camera_pipeline()
        # while True:
        time.sleep(0.1)
        # color_image, depth_image = self.read_images()
        if self.image is not None:
            # self.set_image(color_image, depth_image)
            self.update_image()

    def im_show_thread(self):
        self.thread = Thread(target=self.try_config)
        self.thread.start()
        