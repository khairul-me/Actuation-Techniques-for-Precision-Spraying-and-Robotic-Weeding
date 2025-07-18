
from camera_realsense import RealSense
from camera_opencv import CameraOpenCV
import os
from os.path import join


class Camera:
    def __init__(self) -> None:
        self.camera = RealSense()

    def capture(self):
        res, color = self.camera.capture()
        return res, color

    def end(self):
        self.camera.end()


def main():
    import cv2
    cam = Camera()
    img = None
    save_dir = r'C:\Users\E-ITX\Desktop\BoyangDeng\image'
    cnt = 0
    while True:
        k = cv2.waitKey(50)
        if k == ord('q'):
            break
        elif k == ord('s'):
            if img is not None:
                save_path = join(save_dir, str(cnt)+'.jpg')
                cnt += 1
                cv2.imwrite(save_path, img)
                print(save_path)
        else:
            success, img = cam.capture()
        if success:
            cv2.namedWindow('x', 0)
            cv2.imshow('x', img)
    cam.end()


if __name__ == '__main__':
    main()
