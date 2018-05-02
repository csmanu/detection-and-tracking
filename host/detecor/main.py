import numpy as np
import cv2
import os
import time

from detector import Detector
from videocapture import VideoCaptureAsync
import ascii_art as art

MODEL_NAMES = [
    'ssd_inception_v2_coco_2017_11_17',
    'ssd_mobilenet_v2_coco_2018_03_29',
    'faster_rcnn_inception_v2_coco_2018_01_28'
]
LABEL_NAME = 'mscoco_label_map'
NUM_CLASSES = 90
VIDEO_FILE = '../../videos/HobbyKing.mp4'
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

def app():
    print('[i] Init.')
    cap = VideoCaptureAsync(VIDEO_FILE, FRAME_WIDTH, FRAME_HEIGHT)
    detector = Detector(cap, MODEL_NAMES[1], LABEL_NAME, NUM_CLASSES)

    detector.start()
    detector.wait() # First detection is slow
    cap.start()

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        
        num, detections = detector.get_detections()
        draw_detections(frame, detections, num)
        
        #cv2.putText(frame,'fps: %d'%fps,(10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,(255,255,255),2,cv2.LINE_AA)
        
        cv2.imshow('Frame', frame)
        if cv2.waitKey(1) == 27:
            break
    
    detector.stop()
    cap.stop()
    cv2.destroyAllWindows()

def draw_detections(img, det_dict, n):
    for i in range(n):
        #[ymin, xmin, ymax, xmax]
        ymin, xmin, ymax, xmax = det_dict['detection_boxes'][i]
        bbox = [(int(xmin*FRAME_WIDTH), int(ymin*FRAME_HEIGHT)), (int(xmax*FRAME_WIDTH), int(ymax*FRAME_HEIGHT))]
        cv2.rectangle(img,bbox[0],bbox[1],(255,0,0),2)

if __name__ == '__main__':
    os.system('clear')
    art.printAsciiArt('Detection')
    print('v1.0.0 (C) weedle1912')
    app()
