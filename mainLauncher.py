import os
import subprocess
import threading
import sys
from multiprocessing import shared_memory
from subprocess import Popen, PIPE
import time
import signal
import numpy as np

#change to fit platform python version desired
pythonEnv="3"
pythonVenvPath = "NULL"

#pid list
pids = [0,0,0]

#add current dirs
sys.path.insert(0, os.getcwd() + "/Voice-Buffer")
sys.path.insert(0, os.getcwd() + "/CV-Runner")
sys.path.insert(0, os.getcwd() + "/helpers")
from voiceClass import *

def launch_process(pythonEnv, Path, i):

    #if we want to use a venv
    if pythonVenvPath != "NULL":
        hold = subprocess.Popen([pythonVenvPath, Path])
        pids[i] = hold.pid
    else:
        hold = subprocess.Popen([pythonEnv, Path])
        pids[i] = hold.pid

venv = input("Are you using a venv? (Y/N): ")

if venv == "Y":
    pythonVenvPath = input("please enter the venv path (absolute): ")

option = input("Do you want to launch the (C)ooking processes or the object (E)ntry processes or (Q)uit (C/E/Q): ")

#try to launch all core processes
try:
    
    if (option == "C"):
        #launch Voice process
        launch_process('python'+pythonEnv, "Voice-Buffer/main.py", 1)

        #launch CV Process
        time.sleep(5)
        launch_process('python'+pythonEnv, "CV-Runner/cv.py",2)

        #launch server process
        time.sleep(5)
        launch_process('python'+pythonEnv, "server.py",0)

    elif (option == "E"):
        #launch Voice process
        launch_process('python'+pythonEnv, "Voice-Buffer/main.py", 1)

        #launch Entry Process
        time.sleep(5)
        launch_process('python'+pythonEnv, "Entry/Entry_Process.py",2)
    else:
        print("exiting.... Goodbye")
        exit(0)

except:
    print(f"Could not launch a core process")
    exit(-1)

#make sure their mem segments stay open and kill if they don't
time.sleep(5)
while True:

    items = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    current_frame = np.zeros((720, 1280, 3), np.uint8)

    if (option == "C"):
        try:
            shm_voice_buffer = shared_memory.SharedMemory(name=Print_Buffer.voicesegmentkey, create=False, size=sys.getsizeof(Print_Buffer.tempVoicebuffer))
            shm_buffer_ptr = shared_memory.SharedMemory(name=Print_Buffer.pointerbufferkey, create=False, size=sys.getsizeof(Print_Buffer.tempBufferPointer))
            shm_server = shared_memory.SharedMemory(name="shmemseg", create=False, size=items.nbytes)
            shm_cam = shared_memory.SharedMemory(name="shcamseg", create=False, size=current_frame.nbytes)
        except Exception as e:
            print("Something went wrong checking up on the shared memory: " +  str(e))
            print("Closing all segments and killing all running sub-processes.....")
            for pid in pids:
                os.kill(pid, signal.SIGINT)
            exit(-1)
    else:
        try:
            shm_voice_buffer = shared_memory.SharedMemory(name=Print_Buffer.voicesegmentkey, create=False, size=sys.getsizeof(Print_Buffer.tempVoicebuffer))
            shm_buffer_ptr = shared_memory.SharedMemory(name=Print_Buffer.pointerbufferkey, create=False, size=sys.getsizeof(Print_Buffer.tempBufferPointer))
        except Exception as e:
            print("Something went wrong checking up on the shared memory: " +  str(e))
            print("Closing all segments and killing all running sub-processes.....")
            for pid in pids:
                os.kill(pid, signal.SIGINT)
            exit(-1)