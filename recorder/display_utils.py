from venv import create
from PyQt5.QtWidgets import QWidget,QVBoxLayout, QLabel
import cv2
from enums import DisplayType
import pyqtgraph as pg
from biosiglive import LivePlot, PlotType
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QPen
from PyQt5.QtCore import Qt
import numpy as np


class Tab(QWidget):
    def __init__(self, name, content):
        super().__init__()
        self.name = name
        self.content = content 
        self.data_buffer = None
        self.type = None

    def initialize_widget(self):
        pass

class CurveTab(Tab):
    def __init__(self, name, content):
        super().__init__(name, content)
        self.type = DisplayType.CURVE
        self.data_queue = None
        self.nb_channels = 1 if name == 'trigger' else len(self.content["devices"])
        self.channel_names = ["trigger"] if name == 'trigger' else [device["name"] for device in self.content["devices"]]
        self.initialize_widget()
    
    def initialize_widget(self):
        self.plot_curve = LivePlot(
        name=self.name,
        rate=100,
        plot_type=PlotType.Curve,
        nb_subplots=self.nb_channels,
        channel_names=self.channel_names
        )
        self.plot_curve.init(plot_windows=10000, y_labels=["V"] * self.nb_channels, create_app=False)

        self.widget = self.plot_curve.win
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)
    
    def update_plot(self):
        try:
            data = self.data_queue.get(timeout=0.1)
        except:
            return
        self.plot_curve.update(data[None, :])

        
    def set_data(self, data):
        self.data_queue = data


class ImageTab(Tab):
    def __init__(self, name, content):
        super().__init__(name, content)
        self.type = DisplayType.IMAGE
        self.data_shape = content['image_res'].split('x')
        self.data_shape = (int(self.data_shape[1]), int(self.data_shape[0]))
        self.shared_color_image = np.zeros((3, self.data_shape[0], self.data_shape[1]))
        self.shared_depth_image = np.zeros(self.data_shape)
        self.initialize_widget()

    def initialize_widget(self):
        self.image_widget = ScaledImage(self.data_shape)
        layout = QVBoxLayout()
        layout.addWidget(self.image_widget)
        self.setLayout(layout)
    
    # def resizeEvent(self, a0):
    #     self.image_widget.update_scaled_image()
    
    def update_plot(self):
        try:
            frame_number, buff_idx = self.frame_queue.get(timeout=0.1)
            color_image = self.shared_color_image[..., buff_idx].copy()
            depth_image = self.shared_depth_image[..., buff_idx].copy()
            self.image_widget.update_scaled_image(color_image, depth_image, frame_number)
        except:
            pass

    def set_data(self, color_image, depth_image, frame_queue):
        self.shared_color_image = color_image
        self.shared_depth_image = depth_image
        self.frame_queue = frame_queue
    
    
class ScaledImage(QLabel):
    def __init__(self, image_shape):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.image_shape = image_shape
        self.update_scaled_image(np.zeros((image_shape[0], image_shape[1], 3), dtype=np.uint8), np.zeros(image_shape, dtype=np.float32))
    
    def update_scaled_image(self, color, depth, frame_number = None):
        if frame_number is None:
            frame_number = 0

        color = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth, alpha=0.03), cv2.COLORMAP_JET)
        cv2.addWeighted(depth_colormap, 0.8, color, 0.8, 0, color)
        cv2.putText(
            color,
            f"Frame: {frame_number}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

        image = QImage(color, color.shape[1], color.shape[0], color.strides[0],  QImage.Format_RGB888)
        original_map = QPixmap.fromImage(image)
        # scaled_pixmap = original_map.scaled(
        #     self.size().width(), self.size().height(),
        #     Qt.KeepAspectRatio,
        #     Qt.TransformationMode.SmoothTransformation
        # )
        self.setPixmap(original_map)
        self.setScaledContents(True)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    main_window = QMainWindow()

    area = (100, 100, 400, 400)
    vt = ScaledImage()
    main_window.setCentralWidget(vt)

    main_window.show()
    sys.exit(app.exec_())



