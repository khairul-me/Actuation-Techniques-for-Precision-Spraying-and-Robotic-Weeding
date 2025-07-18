from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QVBoxLayout, QSlider, QLabel, QFileDialog, QMainWindow, QButtonGroup, QApplication
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QCoreApplication, QObject, QRunnable, QThread, QThreadPool, pyqtSignal, QTimer, QRect
from PyQt5 import QtCore

import serial
import numpy as np
import config as cfg
import time
import traceback
import threading

valve_signal_idx = 0

class SignalValve(QObject):
    # finished = pyqtSignal()
    # progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.signal_write_path = 'arduino_code/valve_control/signal_1to12.txt'
        self.signal_write_path2 = 'arduino_code/valve_control/signal_13to24.txt'
        with open(self.signal_write_path, 'w') as f:
            f.write('0')
        with open(self.signal_write_path2, 'w') as f:
            f.write('0')

    def run(self, nearest_valve_idxes_cur, valve_signal_idx):
        try: 
            # invertal = 3/100.0 # m, 50 pixel
            # invertal = 6/100.0 # m 100 pixel
            invertal = 10/100.0 # m 100 pixel
            delay_time = -1
            # valve_response_time = 0.1
            valve_response_time = 0.05
            if cfg.current_speed > 0:
                delay_time = round(invertal/cfg.current_speed, 3)
                delay_time = max(0, delay_time-valve_response_time)
            # time.sleep(1.500)
            if delay_time > 0:
                time.sleep(delay_time)
            else:
                return
            msg=str(valve_signal_idx) + ', open valves:' + str(nearest_valve_idxes_cur) + ', all candidates' + str(nearest_valve_idxes_cur)

            cfg.log_xalg(msg)
            cfg.global_window.statusBar().showMessage(msg)
            for nearest_valve_idx in nearest_valve_idxes_cur:
                text_id = cfg.valve_idx_to_text_dict[nearest_valve_idx]
                if text_id >= '13':
                    control_path = self.signal_write_path2
                else:
                    control_path = self.signal_write_path
                with open(control_path, 'w') as f:
                    f.write(text_id)
                time.sleep(0.05)
            time.sleep(0.05)
            with open(self.signal_write_path, 'w') as f:
                f.write('0')
            with open(self.signal_write_path2, 'w') as f:
                f.write('0')         
            # with open(self.signal_write_path, 'r') as f:
            #     xxx = f.read()
            #     if xxx != '':
            #         with open(self.signal_write_path, 'w') as f:
            #             f.write('0')
            # with open(self.signal_write_path2, 'r') as f:
            #     xxx = f.read()
            #     if xxx != '':
            #         with open(self.signal_write_path2, 'w') as f:
            #             f.write('0')
            # time.sleep(1.0)
            msg=str(valve_signal_idx) + ', done:' + str(nearest_valve_idxes_cur)
            cfg.log_xalg(msg)
            cfg.global_window.statusBar().showMessage(msg)
            time.sleep(0.5)
            msg=str(valve_signal_idx) + ', can reopen valves now:' + str(nearest_valve_idxes_cur)
            cfg.log_xalg(msg)
            cfg.global_window.statusBar().showMessage(msg)
            for nearest_valve_idx in nearest_valve_idxes_cur:
                if nearest_valve_idx in cfg.nearest_valve_idxes_in_process:
                    cfg.nearest_valve_idxes_in_process.remove(nearest_valve_idx)
        except Exception as e:
            print(traceback.format_exc())
            print(e)

class WorkerSendSignalValve(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.last_results_boxes = None
        self.global_idx = 0 
        self.nozzle_idxes = list(cfg.valve_idx_to_text_dict.keys())

    def bb_intersection_over_union(self, boxA, boxB):
        # determine the (x, y)-coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        # compute the area of intersection rectangle
        interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
        # compute the area of both the prediction and ground-truth
        # rectangles
        boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
        boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
        # compute the intersection over union by taking the intersection
        # area and dividing it by the sum of prediction + ground-truth
        # areas - the interesection area
        iou = interArea / float(boxAArea + boxBArea - interArea)
        # return the intersection over union value
        return iou
    
    def calculate_direction(self, box, box_last):
        xmin = int(box[0])
        ymin = int(box[1])
        xmax = int(box[2])
        ymax = int(box[3])
        xmin_last = int(box_last[0])
        ymin_last = int(box_last[1])
        xmax_last = int(box_last[2])
        ymax_last = int(box_last[3])
        if xmin-xmin_last < -10:
            direction = 1
        else:
            direction = -1
        return direction

    def check_box_location(self, bboxes, global_idx):
        nearest_valve_idxes_new = []
        nearest_valve_idxes_tmp = []
        h_im, w_im = cfg.detect_size[:2]
        range_per_valve = h_im/cfg.valve_num
        for box in bboxes:
            xmin = int(box[0])
            ymin = int(box[1])
            xmax = int(box[2])
            ymax = int(box[3])
            if len(box) >= 6:
                conf = int(round(box[4], 2)*100)
                sku = int(box[5])
            # print(box)
            if self.last_results_boxes is not None:
                ious = []
                for last_box in self.last_results_boxes:
                    iou = self.bb_intersection_over_union(box, last_box)
                    iou = round(iou, 2)
                    ious += [iou]
                    if iou > 0.1 and iou < 0.9:
                        """
                        old setting when weed close to the edge
                        # if xmin < 30 and xmax < 100:
                        # if xmin < 75 and xmin > 50:
                        xmin < 100 and xmin > 50
                        """
                        direction = self.calculate_direction(box, last_box)
                        y_ave = (ymin+ymax)/2
                        nearest_valve_idx = int(y_ave/range_per_valve) + 1
                        nearest_valve_idx = np.clip(nearest_valve_idx, min(self.nozzle_idxes), max(self.nozzle_idxes))
                        nearest_valve_idxes_tmp += [nearest_valve_idx]
                        # odd nozzle idx
                        if xmin < 1050 and xmin > 1000 and direction > 0:
                            possible_nozzles = nearest_valve_idxes_tmp[:-4]
                            possible_nozzles = np.unique(possible_nozzles)
                            for x in possible_nozzles:
                                if x % 2 == 1:
                                    nearest_valve_idxes_new += [x]
                            print('iou:', iou, box)
                        # even nozzle idx
                        elif xmin < 750 and xmin > 700 and direction < 0:
                            possible_nozzles = nearest_valve_idxes_tmp[4:]
                            possible_nozzles = np.unique(possible_nozzles)
                            for x in possible_nozzles:
                                if x % 2 == 0:
                                    nearest_valve_idxes_new += [x]
                            print('iou:', iou, box)
                # if global_idx % 500 == 0:
                #     print('global_idx:', global_idx, 'ious:', ious)
        return nearest_valve_idxes_new    
    
    def get_current_speed(self):
        speed = -1
        with open('./amiga_control/states.txt', 'r') as f:
            info = f.readlines()
            texts = info[-1].split(' ')
            try:
                idx = texts.index('speed')
                speed = texts[idx+1]
                speed = round(float(speed),3)
            except:
                speed = -1
        cfg.current_speed = speed
        return speed

    def send_signal(self, nearest_valve_idxes_cur, valve_signal_idx):
        self.worker = SignalValve()
        # self.thread = QThread()
        # self.worker.moveToThread(self.thread)
        # self.thread.started.connect(self.worker.run)
        # self.worker.finished.connect(self.thread.quit)
        # self.worker.finished.connect(self.worker.deleteLater)
        # self.thread.finished.connect(self.thread.deleteLater)
        # self.thread.start()

        t1 = threading.Thread(target=self.worker.run, args=(nearest_valve_idxes_cur, valve_signal_idx))  
        t1.start()  
        # t1.join()

    def run_sync(self):
        """
        Since directly send through seriel port cannot work, using valve_control/valve_serial_send_port2.py
        """
        #memory increasing
        try:
            global valve_signal_idx
            if True:
                self.global_idx += 1
                global_idx = self.global_idx
                time.sleep(0.01)
                if global_idx % 3000 == 0:
                    print('global_idx:', global_idx)

                need_open_valve = len(cfg.nearest_valve_idxes_manual_control) > 0 # and cfg.nearest_valve_idxes_manual_control != cfg.nearest_valve_idxes_in_process
                print('need_open_valve:', need_open_valve, cfg.nearest_valve_idxes_manual_control)
                if need_open_valve:
                    nearest_valve_idxes_cur = cfg.nearest_valve_idxes_manual_control.copy()
                    # for nearest_valve_idx in cfg.nearest_valve_idxes_in_process:
                    #     if nearest_valve_idx in nearest_valve_idxes_cur:
                    #         nearest_valve_idxes_cur.remove(nearest_valve_idx)
                    for nearest_valve_idx in nearest_valve_idxes_cur:
                        if nearest_valve_idx not in cfg.nearest_valve_idxes_in_process:
                            cfg.nearest_valve_idxes_in_process += [nearest_valve_idx]
                    valve_signal_idx += 1
                    if len(nearest_valve_idxes_cur) > 0:
                        self.send_signal(nearest_valve_idxes_cur, valve_signal_idx)
                        
                if cfg.global_detector.results_grade is None:
                    return
                speed = self.get_current_speed()
                if cfg.global_detector.results_grade is None:
                    return
                if type(cfg.global_detector.results_grade) is list:
                    grade_boxes = cfg.global_detector.results_grade
                else:
                    grade_boxes = cfg.global_detector.results_grade.boxes.data.cpu().numpy()
                if len(grade_boxes) > 0:
                    if self.last_results_boxes is None or self.last_results_boxes[0][0] != grade_boxes[0][0]:
                        nearest_valve_idxes_new = self.check_box_location(grade_boxes, global_idx)
                        need_open_valve = len(nearest_valve_idxes_new) > 0 and nearest_valve_idxes_new != cfg.nearest_valve_idxes_in_process
                        if need_open_valve:
                            nearest_valve_idxes_cur = nearest_valve_idxes_new.copy()
                            for nearest_valve_idx in cfg.nearest_valve_idxes_in_process:
                                if nearest_valve_idx in nearest_valve_idxes_cur:
                                    nearest_valve_idxes_cur.remove(nearest_valve_idx)
                            for nearest_valve_idx in nearest_valve_idxes_cur:
                                if nearest_valve_idx not in cfg.nearest_valve_idxes_in_process:
                                    cfg.nearest_valve_idxes_in_process += [nearest_valve_idx]
                            valve_signal_idx += 1
                            if len(nearest_valve_idxes_cur) > 0:
                                self.send_signal(nearest_valve_idxes_cur, valve_signal_idx)
                        self.last_results_boxes = grade_boxes
                    else:
                        pass
        except Exception as e:
            print(traceback.format_exc())
            print(e)
        self.finished.emit()

    def run(self):
        """
        Since directly send through seriel port cannot work, using valve_control/valve_serial_send_port2.py
        """
        #memory increasing
        try:
            global valve_signal_idx
            while True:
                self.global_idx += 1
                global_idx = self.global_idx
                time.sleep(0.01)
                if global_idx % 3000 == 0:
                    cfg.log_xalg('valve control thread, global_idx:', global_idx)

                need_open_valve = len(cfg.nearest_valve_idxes_manual_control) > 0 and cfg.nearest_valve_idxes_manual_control != cfg.nearest_valve_idxes_in_process
                # print('need_open_valve:', need_open_valve, cfg.nearest_valve_idxes_manual_control)
                if need_open_valve:
                    nearest_valve_idxes_cur = cfg.nearest_valve_idxes_manual_control.copy()
                    for nearest_valve_idx in cfg.nearest_valve_idxes_in_process:
                        if nearest_valve_idx in nearest_valve_idxes_cur:
                            nearest_valve_idxes_cur.remove(nearest_valve_idx)
                    for nearest_valve_idx in nearest_valve_idxes_cur:
                        if nearest_valve_idx not in cfg.nearest_valve_idxes_in_process:
                            cfg.nearest_valve_idxes_in_process += [nearest_valve_idx]
                    valve_signal_idx += 1
                    if len(nearest_valve_idxes_cur) > 0:
                        self.send_signal(nearest_valve_idxes_cur, valve_signal_idx)
                        
                if cfg.global_detector.results_grade is None:
                    continue
                speed = self.get_current_speed()
                if cfg.global_detector.results_grade is None:
                    continue
                if type(cfg.global_detector.results_grade) is list:
                    grade_boxes = cfg.global_detector.results_grade
                else:
                    grade_boxes = cfg.global_detector.results_grade.boxes.data.cpu().numpy()
                # if global_idx % 1000 == 0:
                #     print('grade_boxes:', grade_boxes)
                if len(grade_boxes) > 0:
                    if self.last_results_boxes is None:
                        self.last_results_boxes = grade_boxes
                        continue
                    # if  self.last_results_boxes[0][0] != grade_boxes[0][0]:
                    if  True:
                        nearest_valve_idxes_new = self.check_box_location(grade_boxes, global_idx)
                        if len(nearest_valve_idxes_new) > 0 and nearest_valve_idxes_new != cfg.nearest_valve_idxes_in_process:
                            nearest_valve_idxes_cur = nearest_valve_idxes_new.copy()
                            for nearest_valve_idx in cfg.nearest_valve_idxes_in_process:
                                if nearest_valve_idx in nearest_valve_idxes_cur:
                                    nearest_valve_idxes_cur.remove(nearest_valve_idx)
                            for nearest_valve_idx in nearest_valve_idxes_cur:
                                if nearest_valve_idx not in cfg.nearest_valve_idxes_in_process:
                                    cfg.nearest_valve_idxes_in_process += [nearest_valve_idx]
                            valve_signal_idx += 1
                            if len(nearest_valve_idxes_cur) > 0:
                                self.send_signal(nearest_valve_idxes_cur, valve_signal_idx)
                    else:
                        pass
                    self.last_results_boxes = grade_boxes
        except Exception as e:
            print(traceback.format_exc())
            print(e)
        self.finished.emit()

class WorkerSendSignalSpeed(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        # self.signal_dir = '/home/agfoodsensinglab/Desktop/Arduino/signal.txt'
        self.signal_read_path = 'sensing/signal_read.txt'
        self.signal_write_path = 'sensing/signal_write.txt'
        self.signal_new_sample_path = 'sensing/signal_new_sample.txt'
        with open(self.signal_new_sample_path, 'w') as f:
            f.write('')
        with open(self.signal_read_path, 'w') as f:
            f.write('')
        with open(self.signal_write_path, 'w') as f:
            f.write('0')

    def run(self):
        """
        if directly send through seriel port cannot work, using test/serial_send.py
        """
        # arduino = serial.Serial('COM5', 9600, timeout=1)
        #memory increasing
        processed_ids = []
        last_times = []
        need_seperate = False
        signal_txt = '0'
        last_target_id = -1
        last_available_ids = []
        try:
            with open(self.signal_read_path, 'w') as f:
                f.write('')
            while True:
                time.sleep(0.005)
                ids = list(cfg.global_detector.graded_sps.keys())
                available_ids = list(set(ids)-set(processed_ids))
                if last_available_ids != available_ids:
                    last_available_ids = available_ids
                    print('available_ids:', available_ids)
                    with open(self.signal_read_path, 'w') as f:
                        f.write('')
                if len(available_ids) == 0:
                    continue
                target_id = min(available_ids)
                if last_target_id != target_id:
                    last_target_id = target_id
                    print('target_id:', target_id)
                target_id_info = cfg.global_detector.graded_sps[target_id]
                f_grade = target_id_info['f_grade_sample']

                # if arduino.in_waiting > 0:
                #     has_sense_something = arduino.readline().decode("utf-8")
                with open(self.signal_read_path, 'r') as f:
                    is_sense_something = f.read()
                if is_sense_something:
                    print('is_sense_something:', is_sense_something)
                    with open(self.signal_new_sample_path, 'w') as f:
                        f.write('1')
                    with open(self.signal_read_path, 'w') as f:
                        f.write('')
                    current_time = cfg.global_timer.get_cur_time(is_init=True)
                    if len(last_times) > 0:
                        time_gap = current_time - last_times[-1]
                        if time_gap <=0:
                            continue
                    last_times.append(current_time)
                    print('f_grade_sample:', f_grade)
                    if f_grade == cfg.sku_names[1]:
                        need_seperate = True
                        # 4cm 1500ms
                        wait_time = max(400, 1250 - (cfg.conveyor_current_speed-4) * 150)
                        signal_txt = '1'
                    elif f_grade == cfg.sku_names[2]:
                        need_seperate = True
                        # 4cm 4000ms
                        wait_time = max(1200, 3500 - (cfg.conveyor_current_speed-4) * 450)
                        signal_txt = '2'
                    
                    if need_seperate:
                        need_seperate = False
                        print('wait_time:', wait_time, 'ms')
                        wait_time/=1000
                        print('wait start')
                        time.sleep(wait_time)
                        print('wait end')
                        with open(self.signal_write_path, 'w') as f:
                            f.write(signal_txt)
                            # arduino.write(bytes(signal_txt, 'utf-8'))
                        print('signal_txt:', signal_txt)
                    else:
                        print('wait start')
                        time.sleep(1.0)
                        print('wait end')
                    processed_ids += [target_id]
                    print('reset:', self.signal_read_path)
                    with open(self.signal_read_path, 'w') as f:
                        f.write('')
                    with open(self.signal_new_sample_path, 'w') as f:
                        f.write('')
        except Exception as e:
            print(traceback.format_exc())
            print(e)
        self.finished.emit()

