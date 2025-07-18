# First import the library
from camera_abstract import CameraBase
import cv2

class CameraOpenCV(CameraBase):
    def __init__(self) -> None:
        super().__init__()
        # cap = cv2.VideoCapture('test.mp4')
        #cap = cv2.VideoCapture(r"C:\Users\AFSALab\OneDrive - Michigan State University\Project\SweetPotatoSorting\video\13.avi")
        self.cap = cv2.VideoCapture(0)

    def capture(self):
        success, img = self.cap.read()
        # depth = frames.get_depth_frame()
        # if not depth: 
        #     continue
        return success, img

    def end(self):
        self.cap.release()

def demo():
    pass


def main():
    demo

if __name__ =='__main__':
    main()

# import numpy as np
# depth = frames.get_depth_frame()
# depth_data = depth.as_frame().get_data()
# np_image = np.asanyarray(depth_data)