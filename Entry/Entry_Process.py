import os, os.path
from multiprocessing import shared_memory
import numpy as np
import signal
import sys
import fcntl
import random
import threading
import time
import json
from gtts import gTTS 


#import the class
sys.path.append('Voice-Buffer/')
from voiceClass import *

#open the shared memory segments
vector_of_tags = np.array(["NULL" * 10] * 100)
shm_server = shared_memory.SharedMemory(name="shmemseg", create=True, size=vector_of_tags.nbytes)
buffer = np.ndarray(vector_of_tags.shape, dtype=vector_of_tags.dtype, buffer=shm_server.buf)
buffer[:] = vector_of_tags[:]

def signal_handler(sig, frame):

    print("cleaning voice buffer shared memory....")
    shm_voice_buffer.close()
    shm_voice_buffer.unlink()

    print("exiting voice buffer..")
    exit(0)

#stubbed entry method
def scan_side(tags):

    #send a request to read
    #STUB

    #give it 2 seconds to get values
    time.sleep(2)

    #enter the found tag into the set
    vector_of_tags[:] = buffer[:]
    for item in vector_of_tags:
        if item[0:4] != "NULL":
            tags.add(item)

    return tags

#JSON Writers/Readers
def writeJSONFile(fileName, data):
    with open(fileName, 'w') as fp:
        json.dump(data, fp)
 
def readJSONFile(fileName):
    f = open(fileName)
    return json.load(f)

#stubbed save method
def save_to_database(tags):
    
    old_data = {}

    if os.path.isfile('data.json'):
        old_data = readJSONFile("data.json")
        
    old_data.update(tags)

    writeJSONFile("data.json", old_data)

    print("Save_To_Database: data.json")
    

#enter the buffer object to print
while(True):

    tags = set()

    Print_Buffer.__post_message__("Entring object entry mode. Please place tracking stickers on the desired item and place the item in front of the sensor.")
    
    time.sleep(5)

    tags = scan_side(tags)

    Print_Buffer.__post_message__("Rotate object so a different tag is facing the sensor again and wait 5 seconds")

    time.sleep(5)

    tags = scan_side(tags)

    Print_Buffer.__post_message__("Rotate object again so a different tag is facing the sensor again and wait 5 seconds")

    time.sleep(5)

    tags = scan_side(tags)

    Print_Buffer.__post_message__("Rotate object one last time so a different tag is facing the sensor again and wait 5 seconds")

    time.sleep(5)

    tags = scan_side(tags)

    Print_Buffer.__post_message__(str(len(tags)) + " tags were found. Please Enter a name to associate with these tags")

    name = input("Enter name to associate with tags:")
    ret_dict = {}
    ret_dict[name] = list(tags)

    Print_Buffer.__post_message__("these " + str(len(tags)) + " tags are now associated with " + name)

    save_to_database(ret_dict)

    Print_Buffer.__post_message__("Object successfully saved. Do you want to enter another object?")

    name = input("Y/N:")

    if name != "Y":
        exit(0)
