import os
from multiprocessing import shared_memory
import numpy as np
import signal
import sys
import fcntl

def signal_handler(sig, frame):

    print("cleaning voice buffer shared memory....")
    shm_voice_buffer.close()
    shm_voice_buffer.unlink()

    print("exiting voice buffer..")
    exit(0)

class Print_Buffer:

    #string queue structure
    default_str = "This string is still completely empty and should be skipped for now. If we need to put something here in the future, we will replace this string with a new 255-byte string and the buffer will read out the string before removing this."
    string_queue = [default_str] * 31
    buff_pos = 1
    print_from_buffer = 0

    #barrier entry
    def __enter__ (self):
        self.fp = open("./lockfile.lck")
        fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)

    #barrier exit
    def __exit__ (self, _type, value, tb):
        fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
        self.fp.close()

    #this is what we call when we want to post a message to the buffer
    def __post_message__(input_string_):

        self.__enter__()

        #duplicate buffer
        dup_buffer_pos = self.buff_pos

        #find the first open slot
        while self.string_queue[dup_buffer_pos] != self.default_str:
            dup_buffer_pos = (dup_buffer_pos % 30) + 1

        #temp solution to fill string
        while(len(input_string_) < 255):
            input_string_ += " "

        #fill it    
        self.string_queue[dup_buffer_pos] = input_string_
        
        #make sure we increase the buffer count
        self.print_from_buffer += 1

        self.__exit__()

    #grab a message from the queue each time we are ready to speak
    def __grab_message__(self):

        self.__enter__()

        #decrement the count
        self.print_from_buffer -= 1

        #find the first non-open slot
        while self.string_queue[self.buff_pos] == self.default_str:
            self.buff_pos = (self.buff_pos % 30) + 1

        #grab the message and "print" it before replacing it
        print(self.string_queue[self.buff_pos])

        #refill area
        self.string_queue[self.buff_pos] = self.default_str

        self.__exit__()

        #wait for new buffer push
        while(not self.print_from_buffer):
            1 == 1


#make a buffer object in shared memory
tempObj = np.ndarray(1, dtype = Print_Buffer)
tempObj[0] = Print_Buffer()
shm_voice_buffer = shared_memory.SharedMemory(name="voicebufferseg", create=False, size=sys.getsizeof(tempObj))
shared_mem_segment = np.ndarray(tempObj.shape, dtype=tempObj.dtype, buffer=shm_voice_buffer.buf)
shared_mem_segment[:] = tempObj[:]

#enter the buffer object to print
shared_mem_segment[0].__post_message__("Hello world")

#disconnect
shared_mem_segment.close()

