####################################################################
#
# This process acts as the reader for the voice commands, listening
# for any mesage to be pushed to the shared queue, and opening 
# it. It can be called from any process which includes the python
# class Print_Buffer included from voiceClass.py
#
####################################################################

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

#open the shared memory segments
shm_voice_buffer = shared_memory.SharedMemory(name=Print_Buffer.voicesegmentkey, create=True, size=sys.getsizeof(Print_Buffer.tempVoicebuffer))
shm_buffer_ptr = shared_memory.SharedMemory(name=Print_Buffer.pointerbufferkey, create=True, size=sys.getsizeof(Print_Buffer.tempBufferPointer))

#create local representations of the segments
shared_voice_buffer_segment = np.ndarray(Print_Buffer.tempVoicebuffer.shape, dtype=Print_Buffer.tempVoicebuffer.dtype, buffer=shm_voice_buffer.buf)
shared_voice_buffer_pointer = np.ndarray(Print_Buffer.tempBufferPointer.shape, dtype=Print_Buffer.tempBufferPointer.dtype, buffer=shm_buffer_ptr.buf)

#make a local copy of the shared segments
tempVoicebuffer = Print_Buffer.tempVoicebuffer
tempBufferPointer = Print_Buffer.tempBufferPointer
tempVoicebuffer[:] = shared_voice_buffer_segment[:] 
tempBufferPointer[:] = shared_voice_buffer_pointer[:] 

#initialize them
for i in range(31):
    tempVoicebuffer[i] = Print_Buffer.default_str

tempBufferPointer[0] = 1
tempBufferPointer[1] = 0

shared_voice_buffer_segment[:] = tempVoicebuffer[:]
shared_voice_buffer_pointer[:] = tempBufferPointer[:]

#make the lock file
os.system("touch ./lockfile.lck")

#register handler
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

#start waiting for messages to grab
Print_Buffer.__grab_message__()