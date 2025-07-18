from detection.detection import Detector
from sensing.speed_monitor import SpeedMonitor
from sensing.relay_monitor import RelayMonitor
from im_operation.im_operation import ImageHandler
from camera.camera_handler import CameraHandler
from video.video_handler import VideoHandler
from gui.MyWeedGUI import MainWindow
from custom_timer.timer import Timer
import json
import random
from queue import SimpleQueue, Queue
import platform
sys_name = platform.system()


current_speed = -1
# h, w
original_size = (2056, 2464)
# sweet potato
# detect_size = (640, 384)
# weed
# detect_size = (960, 960)
detect_size = (800, 800)
# detect_size = (640, 640)
# display_size = (800, 800)
display_size = detect_size
frame_buffer_count = 10

valve_num = 24
nearest_valve_idxes_manual_control = []
nearest_valve_idxes_in_process = []
# Closed / Open  resultWidget
valve_states_dict = {}
for i_valve in range(1, valve_num+1):
    valve_states_dict[i_valve] = 'Closed'


save_video = True
save_frame = False

async_detection = True

# for indoor testing
pattern_detection_by_morphology = True
if pattern_detection_by_morphology:
    async_detection = False
# for outdoor testing
only_model_detection = True and not pattern_detection_by_morphology
only_track = False and not only_model_detection

async_valve_control = True

plot_improve_label_visibility  = True

# vimba realsense opencv
camera_vendor = 'vimba'
async_camera_stream = False

global_speed_monitor = SpeedMonitor()
global_relay_monitor = RelayMonitor()
global_image_handler = ImageHandler()
global_camera_handler = CameraHandler()
global_video_handler = VideoHandler()
global_detector = Detector()
global_timer = Timer()
global_window = None

# sku_names = ["Premium", "Good" ,"Fair"]
# readable_name_to_sku_name_dict = {"Normal": "Grade1", "Minor defects": "Grade2", "Severe defects": "Grade3"}

conveyor_current_speed = 12  #cm

yolov8_class = ["Lambsquarters", "Unknown", "Ragweed", "Purslane", "Pigweed", "Smartweed"]
yolov8_class_more = ["Waterhemp", "MorningGlory", "Purslane", "SpottedSpurge", "Carpetweed", "Ragweed",
                    "Eclipta", "PricklySida", "PalmerAmaranth", "Sicklepod", "Goosegrass", "CutleafGroundcherry",
                    "Lambsquarters", "Pigweed", "Unknown", "Smartweed", "HophornbeamCopperleaf", "Cocklebur",
                    "Nutsedge", "VirginiaButtonweed", "PurpleAmmania", "GroundIvy", "Swinecress"]

with open('./model/catname2id_yolo.json') as f:
    catname2id_yolo = json.load(f)

sku_names = []
readable_name_to_sku_name_dict = {}
catname2id_yolo = sorted(catname2id_yolo.items(), key=lambda x: x[1])
for item in catname2id_yolo:
    sku_name = item[0]
    sku_names += [sku_name]
    readable_name_to_sku_name_dict[sku_name] = sku_name

readable_names = list(readable_name_to_sku_name_dict.keys())
sku_name_to_readable_name_dict = {}
for grade_name in sku_names:
    sku_name_to_readable_name_dict[readable_name_to_sku_name_dict[grade_name]] = grade_name

sku_colors = [[random.randint(0, 255) for _ in range(3)] for _ in sku_names]

if sys_name == "Windows":
    # detection_mode_path = r'C:\Users\15172\OneDrive_MSU\Project\WeedRobot\Model\yolov10s_weed10sku_36epoch_800\weights\best_weed_10sku_YOLOV10s_800.pt'
    # detection_mode_path = r'C:\Repos\farmng_amigacontrol\model\best_weed_10sku_YOLOV10s_800.pt'
    detection_mode_path = r'.\model\best_weed_10sku_YOLOV10s_800.pt'
    model_paths = {
        'track': detection_mode_path,
        'detection': detection_mode_path
    }

else:
    detection_mode_path = '/home/weeding/WeedRobot/farmng_amigacontrol/model/best_weed_10sku_YOLOV10s_800.pt'
    model_paths = {
        'track': detection_mode_path,
        'detection': detection_mode_path
    }

valve_idx_to_text_dict = {
    1: '1',
    2: '2',
    3: '3',
    4: '4',
    5: '5',
    6: '6',
    7: '7',
    8: '8',
    9: '9',
    10: '10',
    11: '11',
    12: '12',
    13: '13',
    14: '14',
    15: '15',
    16: '16',
    17: '17',
    18: '18',
    19: '19',
    20: '20',
    21: '21',
    22: '22',
    23: '23',
    24: '24',
}

log_path = './log/log.txt'
def log_xalg(*info, log_path=log_path, show=True, end=None):
    from datetime import datetime
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S.%f")
    if show:
        if end is not None:
            print(current_time, *info, end=end)
        else:
            print(current_time, *info)
    if log_path:
        f_log = open(log_path, 'a')
        print(current_time, *info, file=f_log)
        f_log.close()


def list_dir(path, list_name, extension, return_names=False):
    import os
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            list_dir(file_path, list_name, extension)
        else:
            if file_path.endswith(extension):
                if return_names:
                    list_name.append(file)
                else:
                    list_name.append(file_path)
    try:
        list_name = sorted(list_name, key=lambda k: int(os.path.split(k)[1].split(extension)[0].split('_')[-1]))
    except Exception as e:
        print(e)
    return list_name
