from functools import cached_property
from math import comb
from os import name
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QMessageBox, QInputDialog, QTableWidget, QTableWidgetItem, QCheckBox, QLineEdit, QGridLayout, QHBoxLayout, QPushButton, QSpinBox, QLabel, QGroupBox, QRadioButton, QButtonGroup
from biosiglive import PytrignoClient, DeviceType
from biosiglive import LivePlot, PlotType
import multiprocessing as mp
from enums import DelsysType


class Device:
    def __init__(self, name=None, sensor_idx=None, data_type:DelsysType =None):
        self.name = name
        self.sensor_idx = sensor_idx
        self.data_type = data_type

    def get_dict(self):
        return {
            "name": self.name,
            "sensor_idx": self.sensor_idx,
            "data_type": self.data_type,
        }

    def from_dict(self, data):
        self.name = data["name"]
        self.sensor_idx = data["sensor_idx"]
        self.data_type = DelsysType(data["data_type"])
        return self


class DelsysConfiguration(QWidget):
    def __init__(self):
        super().__init__()
        self.client = PytrignoClient(system_rate=100, ip="127.0.0.1")
        self.device_names = []
        self.queue = mp.Queue()
        self.table_widget = None
        self._create_layout()
        self.list_device = list(range(1, 17))
    
    def _create_layout(self):
        self.delsys_adress_label = QLabel("Delsys adress:")
        self.delsys_adress_input = QLineEdit("127.0.0.1")
        self.plot_check = QCheckBox("Plot")
        self.plot_check.setChecked(True)
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels(['Device name', 'Sensor #', 'Data type'])


        self.add_device_button = QPushButton("Add device")
        self.add_device_button.clicked.connect(self._add_row)
        self.remove_device_button = QPushButton("Remove device")
        self.remove_device_button.clicked.connect(self._remove_row)
        # self._create_plot()

        self.layout = QGridLayout()
        self.layout.addWidget(self.delsys_adress_label, 0, 0)
        self.layout.addWidget(self.delsys_adress_input, 0, 1)
        self.layout.addWidget(self.table_widget, 1, 0, 1, 2)
        self.layout.addWidget(self.add_device_button, 2, 0)
        self.layout.addWidget(self.remove_device_button, 2, 1)
        # self.layout.addWidget(self.plot_check, 3, 0)
        # self.layout.addWidget(self.plot_curve.win, 4, 0, 1, 2)
        self.setLayout(self.layout)

    def _add_row(self, device=None):
        row_index = self.table_widget.rowCount()
        self.table_widget.insertRow(row_index)

        combo_type_list = [type.name for type in DelsysType]

        name = device.name if device else f"Device {row_index}"
        idx = device.sensor_idx if device else 0
        data_type = device.data_type if device else DelsysType.Emg
        type_idx = combo_type_list.index(data_type.name)


        self.table_widget.setItem(row_index, 0, QTableWidgetItem(name))

        combo_idx = QComboBox()
        combo_idx.addItems([str(i) for i in range(1, 17)])
        combo_idx.setCurrentIndex(idx)
        self.table_widget.setCellWidget(row_index, 1, combo_idx)
    
        combo_type = QComboBox()
        combo_type.addItems(combo_type_list)
        combo_type.setCurrentIndex(type_idx)
        self.table_widget.setCellWidget(row_index, 2, combo_type)
    
    def _update_row(self, device, row_index):
        combo_type_list = [type.name for type in DelsysType]

        name = device.name
        idx = device.sensor_idx
        data_type = device.data_type
        type_idx = combo_type_list.index(data_type.name)

        self.table_widget.setItem(row_index, 0, QTableWidgetItem(name))
        combo_idx = self.table_widget.cellWidget(row_index, 1)
        combo_idx.setCurrentIndex(idx)
        combo_type = self.table_widget.cellWidget(row_index, 2)
        combo_type.setCurrentIndex(type_idx)

    def _remove_row(self):
        row_index = self.table_widget.currentRow()
        self.table_widget.removeRow(row_index)
        # self._create_plot()
    
    def get_dict(self):
        return {
            "delsys_adress": self.delsys_adress_input.text(),
            "devices": self.get_devices(),
        }

    def from_dict(self, data):
        tab_rows = self.table_widget.rowCount()
        self.delsys_adress_input.setText(data["delsys_adress"])
        for d, device in enumerate(data["devices"]):
            if d not in range(tab_rows):
                self._add_row(Device().from_dict(device))
            else:
                self._update_row(Device().from_dict(device), d)

    def _create_plot(self):
        subplots = len(self.devices) if len(self.devices) != 0 else 1
        channel_names = self.devices if len(self.devices) != 0 else [""]
        self.plot_curve = LivePlot(
        name="",
        rate=100,
        plot_type=PlotType.Curve,
        nb_subplots=subplots,
        channel_names=channel_names,
        )
        self.plot_curve.init(plot_windows=1000, y_labels=["V"])
    
    def update_plot(self, data):
        while self.plot_check.isChecked():
            try:
                data = self.queue.get(timeout=0.01)
                self.plot_curve.update(data)
            except:
                continue

    @cached_property
    def delsys_adress(self):
        return self.delsys_adress_input.text()
    
    def get_devices(self):
        self.devices = [Device(self.table_widget.item(i, 0).text(),
                        int(self.table_widget.cellWidget(i, 1).currentIndex()),
                        DelsysType(self.table_widget.cellWidget(i, 2).currentText().lower()).value) for i in range(self.table_widget.rowCount())]
        return [device.get_dict() for device in self.devices]

    def check_same_idx(self):
        all_idx = [device['sensor_idx'] for device in self.get_devices()]
        duplicates = [i for i in set(all_idx) if all_idx.count(i) > 1]
        if duplicates:
            self.popup_duplicate_idx()
            return False
        return True
    
    def popup_duplicate_idx(self):
        wind = QMessageBox()
        wind.setText("Duplicate in Delsys sensor index detected. Please do not select the same channel for multiple devices.")
        wind.setWindowTitle("Duplicate")
        wind.setIcon(QMessageBox.Critical)
        wind.setStandardButtons(QMessageBox.Ok)
        wind.setDefaultButton(QMessageBox.Ok) 
        wind.buttonClicked.connect(lambda: wind.close())
        wind.exec_()


    
