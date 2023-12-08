import cv2
import io
import socket
import struct
import time
import pickle
import zlib

#code for receiving camera frames from a wireless camera
#
#code modified from the code provided by:
#https://gist.github.com/kittinan/e7ecefddda5616eab2765fdb2affed1b

#set to server ip
ip_addr = '127.0.0.1'

#override cam size
cam = cv2.VideoCapture(0)
cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

#parameters to control how many frames
#we send. At 20 fps, we send a frame every 1/2
#second
img_counter = 0
frame_counter = 0

encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

#keep running no matter what
while True:

    #shortcut way to ensure that when the socket closes on the server
    #we keep looping until we can reconnect to that socket
    try:

        #try to connect. will throw if socket is not found
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip_addr, 54321))
        connection = client_socket.makefile('wb')

        while True:

            #store frame in shared memory
            if frame_counter == 10:
                frame_counter = 0

                ret, frame = cam.read()
                result, frame = cv2.imencode('.jpg', frame, encode_param)
                data = pickle.dumps(frame, 0)
                size = len(data)

                print("{}: {}".format(img_counter, size))
                client_socket.sendall(struct.pack(">L", size) + data)
                img_counter += 1
            
            frame_counter += 1

    except Exception as e:
        print("main receiver turned off....\nlooping until needed.....")

cam.release()
