from math import e
from PyQt5.QtWidgets import QWidget, QGridLayout, QCheckBox, QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox
from biosiglive import LivePlot, PlotType
import multiprocessing as mp


class TriggerWindow(QWidget):
    def __init__(self):
        super().__init__()
        # self._create_plot()
        self._create_layout_objects()
        self.queue = mp.Queue()
    
    def get_dict(self):
        return {
            "vicon_adress": self.vicon_adress,
            "vicon_port": self.vicon_port,
            "trigger_channel": self.trigger_chanel,
            "trigger_threshold": self.trigger_thres,
            "condition": self.condition,
            }

    def from_dict(self, d):
        self.vicon_adress_input.setText(d["vicon_adress"])
        self.vicon_port_input.setText(str(d["vicon_port"]))
        self.trigger_chanel_input.setText(d["trigger_channel"])
        self.trigger_thres_input.setText(str(d["trigger_threshold"]))
        self.condition_input.setCurrentText(d["condition"])

    def _create_layout_objects(self):
        self.label_trig_start = QLabel("Trigger start")
        self.vicon_adress_label = QLabel("Vicon adress:")
        self.vicon_adress_input = QLineEdit("127.0.0.1")
        self.vicon_port_label = QLabel("Port:")
        self.trigger_chanel_label = QLabel("Trigger channel name:")
        self.trigger_chanel_input = QLineEdit("")
        self.trigger_thres_label = QLabel("Trigger threshold:")
        self.trigger_thres_input = QLineEdit("100")
        self.list_condition = ["greater than", "lesser than"]
        self.condition_input = QComboBox()
        self.condition_input.addItems(self.list_condition)
        self.vicon_port_input = QLineEdit(str(801))
        # self.button_ok = QPushButton("Ok")
        # self.button_cancel = QPushButton("Cancel")
        # self.plot_check = QCheckBox("Plot")
        # self.plot_check.setChecked(True)

        self.layout = QGridLayout()
        self.layout.addWidget(self.vicon_adress_label, 0, 0)
        self.layout.addWidget(self.vicon_adress_input, 0, 1)
        self.layout.addWidget(self.vicon_port_label, 0, 2 )
        self.layout.addWidget(self.vicon_port_input, 0, 3)
        self.layout.addWidget(self.trigger_chanel_label, 1, 0)
        self.layout.addWidget(self.trigger_chanel_input, 1, 1)
        self.layout.addWidget(self.trigger_thres_label, 1, 2)
        self.layout.addWidget(self.trigger_thres_input, 1, 4)
        self.layout.addWidget(self.condition_input, 1, 3)
        # self.layout.addWidget(self.plot_curve.win, 3, 0, 1, 5)
        # self.layout.addWidget(self.button_ok, 4, 0)
        # self.layout.addWidget(self.button_cancel, 4, 1)
        self.setLayout(self.layout)

    @property
    def vicon_adress(self):
        return self.vicon_adress_input.text()
    
    @property
    def vicon_port(self):
        return int(self.vicon_port_input.text())
    
    @property
    def trigger_chanel(self):
        return self.trigger_chanel_input.text()
    
    @property
    def trigger_thres(self):
        return float(self.trigger_thres_input.text())
    
    @property
    def condition(self):
        return self.condition_input.currentText()
    
    def _create_plot(self):
        self.plot_curve = LivePlot(
        name="trigger",
        rate=100,
        plot_type=PlotType.Curve,
        nb_subplots=1,
        channel_names=[""],
        )
        self.plot_curve.init(plot_windows=1000, y_labels=["V"])
    
    def update_plot(self):
        while self.plot_check.isChecked():
            try:
                data = self.queue.get(timeout=0.01)
                self.plot_curve.update(data)
            except:
                continue

