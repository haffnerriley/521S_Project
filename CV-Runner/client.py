import cv2
import io
import socket
import struct
import time
import pickle
import zlib

#172.27.17.35
#
#

cam = cv2.VideoCapture(0)

cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

img_counter = 0
frame_counter = 0

encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

while True:

    try:

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('172.27.47.22', 54321))
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
