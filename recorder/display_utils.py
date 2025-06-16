from venv import create
from PyQt5.QtWidgets import QWidget,QVBoxLayout, QLabel
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
        self.plot_curve.init(plot_windows=1000, y_labels=["V"] * self.nb_channels, create_app=False)

        self.widget = self.plot_curve.win
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)
    
    def update_plot(self):
        try:
            data = self.data_queue.get(timeout=0.1)
            self.plot_curve.update(data)
        except:
            print("Queue empty")
        
    def set_data(self, data):
        self.data_queue = data


class ImageTab(Tab):
    def __init__(self, name, content):
        super().__init__(name, content)
        self.type = DisplayType.IMAGE
        self.data_shape = (848, 480)
        self.shared_color_image = np.zeros((3, 848, 480))
        self.shared_depth_image = np.zeros((848, 480))
        self.initialize_widget()

    def initialize_widget(self):
        self.image_widget = ScaledImage()
        layout = QVBoxLayout()
        layout.addWidget(self.image_widget)
        self.setLayout(layout)
    
    # def resizeEvent(self, a0):
    #     self.image_widget.update_scaled_image()
    
    def update_plot(self):
        color = self.shared_color_image.copy()
        depth = self.shared_depth_image.copy()
        self.image_widget.update_scaled_image(color, depth)
    
    def set_data(self, color_image, depth_image):
        self.shared_color_image = color_image
        self.shared_depth_image = depth_image
    
    
class ScaledImage(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.data_shape = (10, 10)
        import cv2
        path = "D:\Documents\Programmation\pose_estimation\data_files\P9\gear_5_11-01-2024_16_59_32/"
        image_tmp = cv2.imread(path + "color_1372.png")
        self.image = cv2.cvtColor(image_tmp, cv2.COLOR_BGR2RGB)
        image = QImage(self.image, self.image.shape[1], self.image.shape[0],self.image.strides[0],  QImage.Format_RGB888)
        # image.fill(QColor(0, 0, 0))
        self.original_pixmap = QPixmap.fromImage(image)
        # self.update_scaled_image(self.image)
    
    def update_scaled_image(self, color, depth):
        # def show_cv2_images(self, color, depth, frame_number, fps):
        # fps = 0 if not np.isfinite(fps) else fps
        # color_image = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
        # depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth, alpha=0.03), cv2.COLORMAP_JET)
        # cv2.addWeighted(depth_colormap, 0.8, color_image, 0.8, 0, color_image)
        # cv2.putText(
        #     color_image,
        #     f"FPS: {int(fps)} | frame: {frame_number}",
        #     (10, 30),
        #     cv2.FONT_HERSHEY_SIMPLEX,
        #     1,
        #     (0, 0, 0),
        #     2,
        #     cv2.LINE_AA,
        # )
        # cv2.waitKey(1)
        # cv2.namedWindow("RealSense", cv2.WINDOW_NORMAL)
        # cv2.imshow("RealSense", color_image)

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



