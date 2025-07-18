from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QVBoxLayout, QSlider, QLabel, QFileDialog, QMainWindow, QButtonGroup, QApplication
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QCoreApplication, QObject, QRunnable, QThread, QThreadPool, pyqtSignal, QTimer, QRect
import config as cfg
import serial
import numpy as np

need_start_relay = True


class WorkerSpeed(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.sr = SpeedReceiver()

    def read(self):
        data = self.sr.read_magnetic_signal()
        return data

    def run(self):
        while True:
            self.read()
        self.finished.emit()


class SpeedReceiver:
    def __init__(self):
        self.serial_portal = '/dev/ttyACM0'
        self.port = 9600
        self.serial_controller = serial.Serial(self.serial_portal, self.port, timeout=1)
        self.wheel_radius = 6.5 * 2.54  # cm
        self.wheel_perimeter = np.pi * 2 * self.wheel_radius

    def receive_magnetic_signal(self):
        if self.serial_controller.in_waiting > 0:
            data = self.serial_controller.readline().decode("ascii")
            with open('/home/agfoodsensinglab/Desktop/Arduino/speed_ave_count.txt', 'w') as f:
                f.write(data)
        return data


class SpeedMonitor:
    def __init__(self):
        # self.wheel_radius = 6.5 * 2.54  # cm
        self.wheel_radius = 5 * 2.54  # cm small wheel
        self.wheel_perimeter = np.pi * 2 * self.wheel_radius

    def read_magnetic_signal(self):
        with open('/home/agfoodsensinglab/Desktop/Arduino/speed_ave_count.txt', 'r') as f:
            ave_count_by_time = f.read()
            ave_count_by_time = float(ave_count_by_time)
        return ave_count_by_time

    
    def caculate_speed(self):
        # ave_count_by_time = self.read_magnetic_signal()
        # speed = ave_count_by_time * self.wheel_perimeter
        speed = cfg.current_speed
        speed = round(speed, 3)
        return speed

    def start_worker(self):
        self.thread = QThread()
        self.worker = WorkerSpeed()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
