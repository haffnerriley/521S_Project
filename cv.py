from transformers import AutoImageProcessor, AutoModelForObjectDetection
from ultralytics import YOLO
from PIL import Image
import torch
import requests
import cv2
from matplotlib import pyplot as plt
  
# Opening image
video_capture_device_index = 0
webcam = cv2.VideoCapture(video_capture_device_index)

#loading a given model
model = YOLO("yolov8l.pt")

#main loop
while True:

    #read from webcam
    ret, image = webcam.read()
    pil_image = Image.fromarray(image)

    #use yolo to detect
    outputs = model.predict(pil_image)

    #Scalable for multiple images to be processed at the same time (AKA more cameras = more better)
    for output in outputs:

        #get boxes
        for box in output.boxes:

            #final score for comparison
            item_label = box.cls[0].item()
            confidence = box.conf[0].item()

            #Only for coco trained things
            classname = output.names[item_label]

            #print for now, replace later with comparison
            if confidence > .8:
                print("Found ", classname, " with confidence of ", confidence)