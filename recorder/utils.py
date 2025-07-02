import numpy as np
import cv2
from PyQt5.QtWidgets import QTabWidget, QPlainTextEdit


def set_shared_memory_images(shared_color, shared_depth, color_image, depth_image, idx):
    np.copyto(shared_color[..., idx], color_image)
    np.copyto(shared_depth[..., idx], depth_image)


def show_cv2_images(color, depth, frame_number, fps):
    fps = 0 if not np.isfinite(fps) else fps
    color_image = cv2.cvtColor(color, cv2.COLOR_BGR2RGB)
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth, alpha=0.03), cv2.COLORMAP_JET)
    cv2.addWeighted(depth_colormap, 0.8, color_image, 0.8, 0, color_image)
    cv2.putText(
        color_image,
        f"FPS: {int(fps)} | frame: {frame_number}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 0),
        2,
        cv2.LINE_AA,
    )
    cv2.waitKey(1)
    cv2.namedWindow("RealSense", cv2.WINDOW_NORMAL)
    cv2.imshow("RealSense", color_image)

def log(log_box, message):
    all_logs = log_box.toPlainText() + message + "\n" 
    log_box.setPlainText(all_logs)


class CustomTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent

    def removeTab(self, index):
        tab_name = self.tabText(index)
        super().removeTab(index)
        if tab_name == 'RGBD':
            self.parent.rgbd_tab = None
        elif tab_name == 'Trigger settings':
            self.parent.trig_tab = None
        elif tab_name == 'Delsys Gogniometer':
            self.parent.gognio_tab = None
        self.parent.log(f"Settings for {tab_name} has been removed.")


class LogBox(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

    def log(self, message):
        self.appendPlainText(message)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    


    


