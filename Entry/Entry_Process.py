import os
from multiprocessing import shared_memory
import numpy as np
import signal
import sys
import fcntl
import random
import threading
import time
from gtts import gTTS 

#import the class
sys.path.append('Voice-Buffer/')
from voiceClass import *

def signal_handler(sig, frame):

    print("cleaning voice buffer shared memory....")
    shm_voice_buffer.close()
    shm_voice_buffer.unlink()

    print("exiting voice buffer..")
    exit(0)

#stubbed entry method
def scan_side(tags):

    #enter the found tag into the set
    tags.add("Tag" + str(random.random()))

    print("Scan_Object: STUB")

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
