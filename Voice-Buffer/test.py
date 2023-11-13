import os
from multiprocessing import shared_memory
import numpy as np
import signal
import sys
import fcntl
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
Print_Buffer.__post_message__("Hello world")

while(True == True):
    1 == 1