import os
import subprocess
import threading
import sys
from multiprocessing import shared_memory

#change to fit platform python version desired
pythonEnv="3"

def launch_process(pythonEnv, Path):
    subprocess.run([pythonEnv, Path], capture_output=False, text=False)

#try to launch all core processes
try:
    
    #launch Voice process
    threading.Thread(target=launch_process, args=('python'+pythonEnv, "Voice-Buffer/main.py",)).start()

    #launch CV Process
    threading.Thread(target=launch_process, args=('python'+pythonEnv, "CV Runner/cv.py",)).start()

    #launch server process
    threading.Thread(target=launch_process, args=('python'+pythonEnv, "server.py",)).start()

except:
    print(f"Could not launch a core process")
    exit(-1)

#make sure their mem segments stay open and kill if they don't
while True:
    try:
        shm_voice_buffer = shared_memory.SharedMemory(name=Print_Buffer.voicesegmentkey, create=False, size=sys.getsizeof(Print_Buffer.tempVoicebuffer))
        shm_buffer_ptr = shared_memory.SharedMemory(name=Print_Buffer.pointerbufferkey, create=False, size=sys.getsizeof(Print_Buffer.tempBufferPointer))
        items = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
        current_frame = np.zeros((720, 1280, 3), np.uint8)
        shm_server = shared_memory.SharedMemory(name="shmemseg", create=False, size=items.nbytes)
        shm_cam = shared_memory.SharedMemory(name="shcamseg", create=False, size=current_frame.nbytes)
    except:
        print("Something went wrong checking up on the shared memory. Closing all segments and killing all running sub-processes.....")
        exit(-1)