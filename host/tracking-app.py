import os
import cv2
import time

import detector.ascii_art as art 

from detector.detector import Detector
from detector.videocapture import VideoCaptureAsync
from tracker.tracker import Tracker

MODEL_NAMES = [
    'ssd_inception_v2_coco_2017_11_17',
    'ssd_mobilenet_v2_coco_2018_03_29',
    'faster_rcnn_inception_v2_coco_2018_01_28'
]
LABEL_NAME = 'mscoco_label_map'
NUM_CLASSES = 90
VIDEO_FILE = '../videos/HobbyKing.mp4'
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

BGR = {'green':(0,255,0), 'orange':(0,153,255), 'white':(255,255,255), 'red':(0,0,255)}

def test():
    cwd = os.getcwd()
    # Path to checkpoint (ckpt)
    model_path = os.path.join(cwd, 'detector', 'models', MODEL_NAMES[1], 'frozen_inference_graph.pb')
    # Path to label names
    labels_path = os.path.join(cwd, 'detector', 'object_detection', 'data', LABEL_NAME + '.pbtxt')

    print('[i] Init.')
    cap = VideoCaptureAsync(VIDEO_FILE, FRAME_WIDTH, FRAME_HEIGHT, FPS)
    detector = Detector(cap, model_path, labels_path, NUM_CLASSES)
    tracker = Tracker()

    detector.start()
    detector.wait() # First detection is slow
    cap.start()

    t_start = False
    lost_count = 0

    while True:
        # Read frame
        ok, frame = cap.read()
        if not ok:
            break

        # Get detection
        new_detection, detections = detector.get_detections()
        bbox_d = format_bbox(detections)

        if not tracker.isInit():
            tracker = Tracker()
            tracker.init(frame, bbox_d)

        # Tracker update
        if new_detection:
            if (detections['num_detections'] == 0) or (detections['detection_classes'][0] != 5):
                cap.clear_frame_buffer()
            else:
                buffer = cap.read_frame_buffer()
                if buffer:
                    tracker = Tracker()
                    tracker.init(buffer.pop(0), bbox_d)
                    for f in buffer:
                        tracker.update(f)
        tracker.update(frame)
        bbox_t = tracker.get_bbox()

        # Get FPS
        FPS_d = detections['FPS']
        FPS_t = tracker.get_fps()

        # Frame overlay
        draw_bbox(frame, bbox_d, BGR['green']) # Detection - green
        draw_bbox(frame, bbox_t, BGR['orange']) # Tracking - orange
        draw_header(frame, detections['detection_classes'], detections['num_detections'])
        draw_footer(frame, FPS_d, FPS_t)

        # Display frame
        cv2.imshow('Frame', frame)
        if cv2.waitKey(1) == 27:
            break
    
    detector.stop()
    cap.stop()
    cv2.destroyAllWindows()


def draw_bbox(frame, bbox, color):
    if bbox:
        cv2.rectangle(frame,(bbox[0],bbox[1]),(bbox[0]+bbox[2],bbox[1]+bbox[3]),color,2)

def draw_header(img, classes, n):
    l_space = 15
    for i in range(n):
        cv2.putText(img,str(classes[i]),(10,(20+i*l_space)), cv2.FONT_HERSHEY_PLAIN, 1,BGR['white'],1,cv2.LINE_AA)

def draw_footer(img, fps_d, fps_t): 
    cv2.putText(img,( 'FPS: ' + ('%d'%fps_d).rjust(3) ),(10,FRAME_HEIGHT-25), cv2.FONT_HERSHEY_PLAIN, 1,BGR['green'],1,cv2.LINE_AA)
    cv2.putText(img,( 'FPS: ' + ('%d'%fps_t).rjust(3) ),(10,FRAME_HEIGHT-10), cv2.FONT_HERSHEY_PLAIN, 1,BGR['orange'],1,cv2.LINE_AA)
    cv2.putText(img,( 'Lost track:   0' ),(FRAME_WIDTH-135,FRAME_HEIGHT-10), cv2.FONT_HERSHEY_PLAIN, 1,BGR['white'],1,cv2.LINE_AA)

def format_bbox(det_dict):
    ymin, xmin, ymax, xmax = det_dict['detection_boxes'][0]
    x = int(xmin*FRAME_WIDTH)
    y = int(ymin*FRAME_HEIGHT)
    w = int(xmax*FRAME_WIDTH) - int(xmin*FRAME_WIDTH)
    h = int(ymax*FRAME_HEIGHT) - int(ymin*FRAME_HEIGHT)
    return (x,y,w,h)

def iou(box1, box2):
    # Box 1
    xmin1, ymin1, xmax1, ymax1 = box1[0], box1[1], (box1[0]+box1[2]), (box1[1]+box1[3])
    area_1 = box1[2]*box1[3]
    # Box 2
    xmin2, ymin2, xmax2, ymax2 = box2[0], box2[1], (box2[0]+box2[2]), (box2[1]+box2[3])
    area_2 = box2[2]*box2[3]
    # Check zero-division
    if ( (area_1 + area_2) == 0):
        return 0.00
    # Intersection
    xmin_i, ymin_i = max(xmin1, xmin2), max(ymin1, ymin2)
    xmax_i, ymax_i = min(xmax1, xmax2), min(ymax1, ymax2)
    area_i = (xmax_i-xmin_i)*(ymax_i-ymin_i)
    # IoU
    iou = (area_i / float(area_1+area_2-area_i))
    if iou < 0:
        return 0.00
    return iou

def bbox_scale(box1, box2, factor):
    box_s = box2
    a1 = box1[2]*box1[3]
    a2 = box2[2]*box2[3]
    if a2 == 0:
        return box_s
    scale_diff = a1/float(a2)
    # Remove jitter:
    if 0.9 < scale_diff < 1.1:
        cx, cy = (box2[0]+(box2[2]/2), box2[1]+(box2[3]/2))
        box_s[0] = int(cx-(box1[2]/2))
        box_s[1] = int(cy-(box1[3]/2))
        box_s[2], box_s[3] = box1[2], box1[3]
    return box_s

if __name__ == '__main__':
    os.system('clear')
    art.printAsciiArt('Tracking')
    print('Tracker v0.0.1 (c) weedle1912')
    test()