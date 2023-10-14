from transformers import AutoImageProcessor, AutoModelForObjectDetection
from ultralytics import YOLO
from PIL import Image
import torch
import requests
import cv2
from matplotlib import pyplot as plt
import os
  
# Opening image
video_capture_device_index = 0
webcam = cv2.VideoCapture(video_capture_device_index)

#change camera resolution
webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

#loading a given model
model = YOLO("yolov8x.pt")

#main loop
while True:

    #read from webcam
    ret, image = webcam.read()
    pil_image = Image.fromarray(image)

    #show the image for now
    cv2.imshow("frame", image)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

    #use yolo to detect
    outputs = model.predict(pil_image)

    #Scalable for multiple images to be processed at the same time (AKA more cameras = more better)
    os.system('clear')
    for output in outputs:

        #get boxes
        for box in output.boxes:

            #cheating the poison classes
            if output.names[box.cls[0].item()] == "sink":
                continue

            #final score for comparison
            item_label = box.cls[0].item()
            confidence = box.conf[0].item()

            #Only for coco trained things
            classname = output.names[item_label]

            #print for now, replace later with comparison
            if confidence > .4:
                print("Found ", classname, " with confidence of ", confidence)