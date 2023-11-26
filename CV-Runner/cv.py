from transformers import AutoImageProcessor, AutoModelForObjectDetection
from ultralytics import YOLO
from PIL import Image
import torch
import requests
import cv2
from matplotlib import pyplot as plt
import os
from multiprocessing import shared_memory
import numpy as np
import copy
import time
import signal

#set os env for objective C
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = "1"

pid = 0

def signal_handler(sig, frame):

    print("cleaning shared memory....")

    try:
        shm_server.close()
        shm_cam.close()
        shm_server.unlink()
        shm_cam.unlink()
        os.kill(pid, signal.SIGINT)
    
    except Exception as e:
        print("shared memory segments are already closed.... skipping...")

    print("exiting..")
    exit(0)

#shared memory local segment to update and push
#each index is an item
#spoon -> 0
#bowl -> 1
#measuring cup -> 2
#spatula -> 3
#oatmeal box -> 4
#oatmeal tin ->5
#frying pan -> 6
#Salt and pepper shaker ->7
items = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
counter = 1

#empty frame for shape
current_frame = np.zeros((720, 1280, 3), np.uint8)

#open shared segments
shm_server = shared_memory.SharedMemory(name="shmemseg", create=True, size=items.nbytes)
shm_cam = shared_memory.SharedMemory(name="shcamseg", create=True, size=current_frame.nbytes)

# Create a child process 
pid = os.fork() 
  
# pid greater than 0 represents 
# the parent process  
if pid > 0 : 

    #let camera get set up
    time.sleep(5)

    #loading a given model
    model = YOLO("bestnew.pt")

    #main loop
    try:
        while True:

            #sleep
            time.sleep(1)

            #grab frame from shared memory
            current_frame_grabbed = np.ndarray(current_frame.shape, dtype=current_frame.dtype, buffer=shm_cam.buf)
            pil_image = Image.fromarray(current_frame_grabbed)

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

                    #handle cross-poisoning classes
                    match classname:
                        case "Fork":
                            classname = "Spatula"
                        case "Box":
                            classname = "Oatmeal box"
                        case "Tin can":
                            classname = "Oatmeal tin"
                        case "Frying pan":
                            classname = "Pan"

                    #print for now, replace later with comparison
                    if confidence > .4:
                        
                        #update local shmem mirror
                        match classname:
                            case "Spoon":
                                items[0] += confidence
                            case "Bowl":
                                items[1] += confidence
                            case "Measuring cup":
                                items[2] += confidence
                            case "Spatula":
                                items[3] += confidence
                            case "Oatmeal box":
                                items[4] += confidence
                            case "Oatmeal tin":
                                items[5] += confidence
                            case "Pan":
                                items[6] += confidence
                            case "Salt and pepper shakers":
                                items[7] += confidence

                        print("Found ", classname, " with confidence of ", confidence)
                    
            #push to shared memory buffer
            if counter == 1:

                #push average confidence
                buffer = np.ndarray(items.shape, dtype=items.dtype, buffer=shm_server.buf)
                buffer[:] = items[:]/counter  

                #display for testing
                print(buffer) 

                #reset local segment
                items = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
                counter = 1

    #close the memory segment on cntrl c
    except KeyboardInterrupt:

        #clean
        signal_handler(None, None)
        os.kill(pid, signal.SIGINT)

        

else:

    frame_counter = 0

    # Opening image
    video_capture_device_index = 0
    webcam = cv2.VideoCapture(video_capture_device_index)

    #change camera resolution
    webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    try:
        while shared_memory.SharedMemory(name="shmemseg", create=False, size=items.nbytes):

            #read from webcam
            ret, image = webcam.read()

            #show the image for now
            cv2.imshow("frame", image)
            
            if cv2.waitKey(1) & 0xFF == ord('q'): 
                os.kill(os.getppid(), signal.SIGINT)
                break
            
            #store frame in shared memory
            if frame_counter == 20:
                frame_counter = 0

                #load frame segment
                shm_frame = np.ndarray(current_frame.shape, dtype=current_frame.dtype, buffer=shm_cam.buf)
                shm_frame[:] = image[:]
            
            frame_counter += 1
    
    except Exception as e:
        print("Camera buffer memory segment closed... closing self....")
        shm_cam.close()
        exit(-1)
            
    shm_cam.close()
