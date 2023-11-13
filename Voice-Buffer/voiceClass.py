import os
from multiprocessing import shared_memory
from multiprocessing.resource_tracker import unregister
import numpy as np
import signal
import sys
import fcntl
from gtts import gTTS 

class Print_Buffer:

    #string queue structure
    voicesegmentkey = "voicebufferseg"
    pointerbufferkey = "voicebufferptrseg"

    #buffer objects to represent shared memory
    tempVoicebuffer = np.ndarray(31, dtype = "|S256")
    tempBufferPointer = np.ndarray(2, dtype = int)

    default_str = "This string is still completely empty and should be skipped for now. If we need to put something here in the future, we will replace this string with a new 255-byte string and the buffer will read out the string before removing this."
    print_from_buffer = 0

    #barrier entry
    @staticmethod
    def __enter__ (fp):
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX)

    #barrier exit
    @staticmethod
    def __exit__ (fp):
        fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
        fp.close()

    #this is what we call when we want to post a message to the buffer
    @staticmethod
    def __post_message__(input_string_):

        #lock
        fp = open("./lockfile.lck")

        Print_Buffer.__enter__(fp)

        #make local copies of shared memory segments in class
        tempVoicebuffer = Print_Buffer.tempVoicebuffer
        tempBufferPointer = Print_Buffer.tempBufferPointer

        #open the shared memory segments
        shm_voice_buffer = shared_memory.SharedMemory(name=Print_Buffer.voicesegmentkey, create=False, size=sys.getsizeof(Print_Buffer.tempVoicebuffer))
        shm_buffer_ptr = shared_memory.SharedMemory(name=Print_Buffer.pointerbufferkey, create=False, size=sys.getsizeof(Print_Buffer.tempBufferPointer))

        #tell os to not manage
        #unregister(shm_voice_buffer.name, 'shared_memory')
        #unregister(shm_buffer_ptr.name, 'shared_memory')

        #fetch local representations of the segments
        shared_voice_buffer_segment = np.ndarray(tempVoicebuffer.shape, dtype=tempVoicebuffer.dtype, buffer=shm_voice_buffer.buf)
        shared_voice_buffer_pointer = np.ndarray(tempBufferPointer.shape, dtype=tempBufferPointer.dtype, buffer=shm_buffer_ptr.buf)

        #make a local copy of the shared segments
        tempVoicebuffer[:] = shared_voice_buffer_segment[:] 
        tempBufferPointer[:] = shared_voice_buffer_pointer[:] 

        #duplicate buffer
        dup_buffer_pos = tempBufferPointer[0]
        
        #find the first open slot
        while shared_voice_buffer_segment[dup_buffer_pos] != tempVoicebuffer[0]:
            dup_buffer_pos = (dup_buffer_pos % 30) + 1

        #temp solution to fill string
        while(len(input_string_) < 255):
            input_string_ += " "

        #fill it    
        tempVoicebuffer[dup_buffer_pos] = input_string_
        
        #make sure we increase the buffer count
        tempBufferPointer[1] += 1

        #update the shared memory segments
        shared_voice_buffer_segment[:] = tempVoicebuffer[:]
        shared_voice_buffer_pointer[:] = tempBufferPointer[:]

        Print_Buffer.__exit__(fp)

        #exit the mem segments
        
        shm_voice_buffer.close()
        shm_buffer_ptr.close()

    #grab a message from the queue each time we are ready to speak
    @staticmethod
    def __grab_message__():

        #lock
        fp = open("./lockfile.lck")

        Print_Buffer.__enter__(fp)

        #make local copies of shared memory segments in class
        tempVoicebuffer = Print_Buffer.tempVoicebuffer
        tempBufferPointer = Print_Buffer.tempBufferPointer

        #open the shared memory segments
        shm_voice_buffer = shared_memory.SharedMemory(name=Print_Buffer.voicesegmentkey, create=False, size=sys.getsizeof(Print_Buffer.tempVoicebuffer))
        shm_buffer_ptr = shared_memory.SharedMemory(name=Print_Buffer.pointerbufferkey, create=False, size=sys.getsizeof(Print_Buffer.tempBufferPointer))

        #tell os to not manage
        #unregister(shm_voice_buffer.name, 'shared_memory')
        #unregister(shm_buffer_ptr.name, 'shared_memory')

        #fetch local representations of the segments
        shared_voice_buffer_segment = np.ndarray(tempVoicebuffer.shape, dtype=tempVoicebuffer.dtype, buffer=shm_voice_buffer.buf)
        shared_voice_buffer_pointer = np.ndarray(tempBufferPointer.shape, dtype=tempBufferPointer.dtype, buffer=shm_buffer_ptr.buf)

        #make a local copy of the shared segments
        tempVoicebuffer[:] = shared_voice_buffer_segment[:] 
        tempBufferPointer[:] = shared_voice_buffer_pointer[:] 

        #skip initial run if nothing in buffer
        tempBufferPointer[:] = shared_voice_buffer_pointer[:] 
        print_from_buffer = tempBufferPointer[1]

        print(str(tempVoicebuffer[1] == tempVoicebuffer[0]))

        if print_from_buffer:

            #make sure we decrement the buffer count
            tempBufferPointer[1] -= 1

            buff_pos = tempBufferPointer[0]

            #find the first non-open slot
            while tempVoicebuffer[buff_pos] == tempVoicebuffer[0]:
                buff_pos = (buff_pos % 30) + 1
            tempBufferPointer[0] = buff_pos

            #grab the message and "speak" it before replacing it
            myobj = gTTS(text=tempVoicebuffer[buff_pos].decode("utf-8"), lang='en', slow=False) 
    
            # Saving the converted audio in a mp3 file named 
            # welcome  
            myobj.save("speech.mp3") 
            
            # Playing the converted file 

            if (sys.platform == "linux"):
                os.system("mpg321 speech.mp3") 
            if (sys.platform == "darwin"):
                os.system("afplay speech.mp3") 
            os.system("rm speech.mp3")

            #refill area
            tempVoicebuffer[buff_pos] = tempVoicebuffer[0]
            
            #update the shared memory segments
            shared_voice_buffer_segment[:] = tempVoicebuffer[:]
            shared_voice_buffer_pointer[:] = tempBufferPointer[:]

        Print_Buffer.__exit__(fp)

        #wait for new buffer push
        print("waiting for message to be entered to buffer")
        while(print_from_buffer == 0):
            tempBufferPointer[:] = shared_voice_buffer_pointer[:] 
            print_from_buffer = tempBufferPointer[1]
        print("message entered into buffer")

        #exit the mem segments
        shm_voice_buffer.close()
        shm_buffer_ptr.close()

        #recurse
        Print_Buffer.__grab_message__()