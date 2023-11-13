import os
from multiprocessing import shared_memory
import numpy as np
import signal
import sys
import fcntl
import threading
from gtts import gTTS 

#import the class
from voiceClass import *

def signal_handler(sig, frame):

    print("cleaning voice buffer shared memory....")
    shm_voice_buffer.close()
    shm_voice_buffer.unlink()

    print("exiting voice buffer..")
    exit(0)

#enter the buffer object to print
while(True):
    message = input("Enter message to print:")
    
    #blocking
    #Print_Buffer.__post_message__(message)

    #non-blocking
    threading.Thread(target=Print_Buffer.__post_message__, args=(message,)).start()