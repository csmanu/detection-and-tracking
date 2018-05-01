# ********************
# * Module: Detector *
# *                  *
# ********************

import numpy as np 
import os
import cv2
import tensorflow as tf 
import threading
import copy

from object_detection.utils import ops as utils_ops

if tf.__version__ < '1.4.0':
    raise ImportError('Please upgrade your tensorflow installation to v1.4.* or later!')

# * TensorFlow Object Detection API
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util 

class Detector:
    def __init__(self, cap='', model_name='', label_name='', num_classes=0):
        self.graph = load_tf_graph(model_name)
        self.category_index = get_label_index(label_name, num_classes)
        self.cap = cap
        self.frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.frame_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.detections = {}
        self.running = False
        self.new_detection = threading.Event()
        self.read_lock = threading.Lock()
    
    def start(self):
        if self.running:
            print('[!] Detection is already started.')
            return None
        print('[d] Starting.')
        self.running = True
        self.thread = threading.Thread(name='Detection', target=self.run, args=())
        self.thread.start()
        return self
    
    def isRunning(self):
        return self.running
    
    def wait(self):
        self.new_detection.wait()
    
    def stop(self):
        print('[d] Stopping.')
        if self.running:
            self.running = False
            self.thread.join()
    
    def run(self):
        with self.graph.as_default():
            with tf.Session() as sess:
                # Get handles to input and output tensors
                tensor_dict = get_handles()
                image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

                while( self.running ):
                    # Get frame
                    ok, image_np = self.cap.read()
                    if not ok:
                        break

                    # Expand dimension. Model expects shape: [1, None, None, 3]
                    image_expanded = np.expand_dims(image_np, axis=0)
                    # Run inference
                    output_dict = sess.run(
                        tensor_dict,
                        feed_dict={image_tensor: image_expanded}
                    )    

                    # All outputs are float32 numpy arrays, so convert types to appropriate
                    output_dict = convert_appropriate(output_dict)

                    # Update detection
                    with self.read_lock:
                        self.detections = output_dict
                    self.new_detection.set()
        self.running = False
    
    def get_detections(self):
        with self.read_lock:
            detections = copy.deepcopy(self.detections)
            self.new_detection.clear()
        num = int(detections['num_detections'])
        return num, detections
    
    def get_bboxes(self):
        with self.read_lock:
            detections = copy.deepcopy(self.detections)
        bboxes = []
        if detections:
            num = int(detections['num_detections'])
            for i in range(num):
                ymin, xmin, ymax, xmax = detections['detection_boxes'][i]
                bboxes.append([(int(xmin*self.frame_width), int(ymin*self.frame_height)), (int(xmax*self.frame_width), int(ymax*self.frame_height))])
        return bboxes



# * Load frozen TF model
def load_tf_graph(model_name):
    cwd_path = os.getcwd()
    path_to_ckpt = os.path.join(cwd_path, 'models', model_name, 'frozen_inference_graph.pb')
    
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(path_to_ckpt, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')
    return detection_graph

# * Load label map
def get_label_index(label_name, num_classes):
    cwd_path = os.getcwd()
    path_to_labels = os.path.join(cwd_path, 'object_detection', 'data', label_name + '.pbtxt')

    label_map = label_map_util.load_labelmap(path_to_labels)
    categories = label_map_util.convert_label_map_to_categories(
        label_map, 
        max_num_classes=num_classes, 
        use_display_name=True
    )
    category_index = label_map_util.create_category_index(categories)
    return category_index

def get_handles():
    ops = tf.get_default_graph().get_operations()
    all_tensor_names = {output.name for op in ops for output in op.outputs}
    tensor_dict = {}
    for key in [
        'num_detections', 'detection_boxes', 'detection_scores',
        'detection_classes', 'detection_masks'
    ]:
        tensor_name = key + ':0'
        if tensor_name in all_tensor_names:
            tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(tensor_name)
    
    if 'detection_masks' in tensor_dict:
        # The following process is only for single image
        detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
        detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
        # Reframe required. Translate mask from box coordinates to image coordinates, and fit the image size
        real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
        detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
        detection_masks = tf.slice(detection_masks, [0, 0], [real_num_detection, -1, -1])
        detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
            detection_masks, detection_boxes, image.shape[0], image.shape[1]
        )
        detection_masks_reframed = tf.cast(
            tf.greater(detection_masks_reframed, 0.5), tf.uint8
        )
        # Follow the convention by adding back the batch dimension
        tensor_dict['detection_masks'] = tf.expand_dims(
            detection_masks_reframed, 0
        )

    return tensor_dict

def convert_appropriate(output_dict):
    output_dict['num_detections']       = int(output_dict['num_detections'][0])
    output_dict['detection_classes']    = output_dict['detection_classes'][0].astype(np.uint8)
    output_dict['detection_boxes']      = output_dict['detection_boxes'][0]
    output_dict['detection_scores']     = output_dict['detection_scores'][0]
    if 'detection_masks' in output_dict:
        output_dict['detection_masks'] = output_dict['detection_masks'][0]
    return output_dict 