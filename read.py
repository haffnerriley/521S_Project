#!/usr/bin/env python3
from __future__ import print_function
import time
from datetime import datetime
import mercury
reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=115200)

print(reader.get_model())
# print(reader.get_supported_regions())
## print get reader power!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
reader.set_region("NA2")
reader.set_read_plan([1], "GEN2", read_power=1900) #upper lower bounds?????
print(reader.get_temperature())


read_count = 5

prev_read = []

loop_count = 0
#for i in range(read_count) :
while True:
     print("Count:" + str(loop_count))
     #make a read
     current_tags = map(lambda t: t.epc, reader.read())
     #print("current: ", end="")
     #print(current_tags)
     #print("prev: ", end="")
     #print(prev_read)
     
     #combine
     all_tags = current_tags + prev_read
     #remove duplicates
     all_tags = list(set(all_tags))
     #print("all: ", end="")
     #print(all_tags)
     
     for tag in all_tags:
         if tag in prev_read and tag in current_tags:
             print(tag + " stayed in field")
             #send to server here  
         elif tag in prev_read and tag not in current_tags:
             print(tag + " has left field")
             #send to server here             
         elif tag in current_tags and tag not in prev_read:
             print(tag + " has entered field")
             #send to server here
         
             
     
     prev_read = current_tags[:]
    
     time.sleep(1)
     loop_count += 1

#finally print all tags in field at last read
# print("current: ", end="")
# print(current_tags)    
# print("DONE")


