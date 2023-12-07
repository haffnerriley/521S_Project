#!/usr/bin/env python3
from __future__ import print_function
import PySimpleGUI as sg
import time
from datetime import datetime
import socket
import threading
import requests
from netifaces import interfaces, ifaddresses, AF_INET
import re
import sys
import numpy as np
from multiprocessing import shared_memory
from shared_memory_dict import SharedMemoryDict
import json
from PIL import Image, ImageTk

#import the class
sys.path.append('Voice-Buffer/')
from voiceClass import *

#Initializing global vars


last_announcement_time = 0

#Storing the reader turn
table_read = False
cabinet_read = False

#Variable that stores CI values from both readers 
client_ci_list = {}

#empty frame for shape
current_frame = np.zeros((720, 1280, 3), np.uint8)

#Shared memory region
shm = None 
shm_dict = SharedMemoryDict(name='cvConfidenceDict', size=1024)
shm_cam = shared_memory.SharedMemory(name="shcamseg", create=False, size=current_frame.nbytes)

#Tracks if shared memory region is open or not 
region_bool = False

#Keeps track of the last read from the CV shared memory region
cv_timer = 0

#Keeps track of ip address 
ipaddr = None

# Configure the server address and port
server_address = None

# Create a socket and bind it to the server address
server_socket = None

#RFID reader object
reader = "undefined"

#RFID reader connection status
reader_status = "disconnected"

#RFID reader power
reader_power = 1000

#Selected EPC to update through the find button 
epc_to_update = "None"

#Default selected item in kitchen
epc_in_kitchen = "None"

#Dictionary of items that the server maintains 
item_dictionary = {}

#Set of items that the table detects 
table_set = set()

#Set of items that the table detects with CI values
table_ci_set = set()

#Set of items that the cabinet detects 
cabinet_set = set()

#Set of items that the cabinet detects with CI values
cabinet_ci_set = set()

#List of EPCS that the server found using the Find button
epcs_to_update = []

#List of items in the recipe
items_in_recipe = []

#Map of items in the recipe 
recipe_map = []

#Default item name in recipe dropdown
default_item = "None"

#Previous RFID reads 
prev_read = []

#List of connected RFID reader clients 
connected_readers = []

#List of client Addresses 
client_addrs = []

#Reader currently selected in the GUI
selected_reader = "None"

#Status of server (Running or Not)
server_status = False

#Status of server reading from RFID modules 
server_read_status = False

#voice sets
recipe_table_set = set()
recipe_cabinet_set = set()
distactor_table_set = set()



#Booleans to track if the initial CI values for the table and cabinet are being recieved
initial_cabinet = False
initial_table = False
# Define the GUI layout
layout = [
    [sg.Text("Set Read Power (0-2700):"), sg.InputText(key="reader-power", size=(15,1)),sg.Text("Connected Clients:"), sg.Combo(connected_readers, default_value=selected_reader, key="cur-reader",size=(35,1), enable_events=True)],
    [sg.Text("EPC(s) to Update:"), sg.Combo(epcs_to_update, default_value=epc_to_update, key="epc",size=(25,1), enable_events=True), sg.Text("Items in Kitchen:"), sg.Combo(item_dictionary, default_value=epc_in_kitchen, key="epc-inventory",size=(25,1), enable_events=True)],
    [sg.Text("New Item Name:"), sg.InputText(key="item-name", size=(20,1)), sg.Text("Items in Recipe:"), sg.Combo(items_in_recipe, default_value=default_item, key="recipe-items", size=(25,1))],
    [sg.Button("Connect CV", key="cv-btn"), sg.Button("Set Power"), sg.Button("Find Item"), sg.Button("Update Item"), sg.Button("Start Server", key="server-btn"), sg.Button("Start Reading", key="server-read"),sg.Button("Add Item", key="add-item"), sg.Button("Remove Item", key="remove-item")],
    [sg.Multiline("", size=(50, 10), key="-EventLog-", disabled=True), sg.Image(key="image")]
]

# Create the window
window = sg.Window("Smart Kitchen Server Application", layout, resizable=True, finalize=True)



def initializeKitchen():
    global item_dictionary

    old_data = {}
    if os.path.isfile('kitchen.json'):
        old_data = readJSONFile("kitchen.json")
    if(len(old_data) > 0):
        item_dictionary = old_data
        epc_in_kitchen = list(item_dictionary.values())[0]
        window["epc-inventory"].update(value=str(epc_in_kitchen), values=list(item_dictionary.values()))

#Function to find the IP address of computer running the server program
def findIP():
    global ipaddr
    global server_address

    #Loop through network interfaces on server to get server IP address 
    for ifaceName in interfaces():
        addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]

        #Using wireless by default to allow for more portability
        if ifaceName == 'wlan0':
           
            #Configuring global ipaddr and server address
            ipaddr = addresses[0]
            server_address = (ipaddr, 12345)

        elif ifaceName == 'en0':

            #Configuring global ipaddr and server address
            ipaddr = addresses[0]
            server_address = (ipaddr, 12345)

def testSpeech(cause):

    global recipe_map
    global recipe_table_set
    global distactor_table_set

    #build string for removal
    remove_items = "Remove "
    for item in distactor_table_set:
        remove_items += (" " + item) 


    messages = ["You have " + str(len(recipe_table_set)) + "required items and " +  str(len(distactor_table_set)) +  " distractors on the table, " + remove_items,
        "All required items found with no distractors",
    ]

    while 1 == 1:
        Print_Buffer.__post_message_async__(messages[cause])
        return

def handleFindResponse(regex):
    global epc_to_update
    global window
    global item_dictionary
    global epcs_to_update
    #Splitting the response up from the client find command 
    data_find = regex.group(1)
    
    #Grab all EPC values send from client as a response to find command 
    split_pattern = re.compile(r'.{1,24}')

    #Finding all occurences of 24 byte EPCS in the client response
    epc_list = split_pattern.findall(data_find)
    epcs_to_update = epc_list
    window["-EventLog-"].print(f"Found Items: {epc_list}\n")
    
    #Set a default EPC in the dropdown menu 
    if len(epc_list) > 0:
        epc_to_update = epc_list[0]
        window["epc"].update(value=str(epc_to_update), values=epc_list)
        selected_item = item_dictionary.get(epc_to_update)
        
        #Check if the item found was already in the user's inventory
        if(selected_item != None):
            epc_to_update = selected_item
        window["-EventLog-"].print(f"Selecting item: {epc_to_update}\n")
    
    return epc_list

#Function that handles connecting to the shared memory region 
def connectCV():
    global shm
    global region_bool
    global cv_timer

    if region_bool:
       shm.close()
       region_bool = not region_bool
    else:
        
        shm = shared_memory.SharedMemory(name="shmemseg", create=False, size=np.zeros(8, dtype=np.float64).nbytes)
        region_bool = not region_bool
        cv_timer = 0

#Function that will add the selected item in the Items in Kitchen dropdown to the Recipe being monitored 
def addItemToRecipe(item):
    global items_in_recipe
    global default_item
    global window
    global recipe_map

    if item == "None":
        window["-EventLog-"].print(f"Please add items to kitchen using the Update button first!\n")
    else:
        default_item = item 
        items_in_recipe.append(default_item)

        #FIXME: this loop will add any item tag epcs that match the value of the key
        #AKA: we have been adding each item n*n times where n is the number of tags
        #could cause weirdness, should fix
        for key, value in item_dictionary.items():
            if default_item == value:
                recipe_map.append(key) 
                #assume items start in cabinet, add the string name of them to the recipe
                recipe_cabinet_set.add(value) 

        window["recipe-items"].update(value=str(default_item), values=items_in_recipe)

#Function that will remove the selected item in the Items in Recipe dropdown from the Recipe being monitored 
def removeItemFromRecipe(item):
    global items_in_recipe
    global default_item
    global window

    if item == "None":
        window["-EventLog-"].print(f"Please add items to kitchen using the Update button first!\n")
    else:
        
        items_in_recipe.remove(default_item)
        for key, value in item_dictionary.items():
            if default_item == value:
                recipe_map.remove(key)
        
        if(len(items_in_recipe) > 0):
            default_item = items_in_recipe[0]
        else:
            default_item = "None"
        
        window["recipe-items"].update(value=str(default_item), values=items_in_recipe)

def handleReadResponse(regex): 
    global window
    global item_dictionary

    #Grab the EPC value sent from the client
    data_read = regex.group(1)
    epc_read = re.compile(r'^(.{24})')
    extracted_epc = re.match(epc_read, data_read)

    if extracted_epc:
        # Extract the first 24 bytes
        extracted_epc = extracted_epc.group(1)
        
        # Grab the message sent with the EPC 
        rest_of_string = data_read[len(extracted_epc):]
        
        #Check if the item exists in our dictionary 
        item_read = item_dictionary.get(extracted_epc)
        if(item_read != None):
            window["-EventLog-"].print(f"{item_read}{rest_of_string}\n")
        else:
            window["-EventLog-"].print(f"{data_read}\n")

        return extracted_epc
    else:
        window["-EventLog-"].print(f"{data_read}\n")
    
    return None


#Handles the confidence intervals sent from the clients
def CABINEThandleCIResponse(regex): 
    global window
   
    #Extract all values after the initial three characters marking the type of packet
    data_ci = regex.group(1)
    
    #Grab all EPC values and confidence intervals 
   
    split_pattern = re.compile(r"b'([0-9A-Fa-f]{24})': \[([0-9.]+), ([0-9.]+), ([0-9.]+)\]")
    
    #Grabbing all EPC's and confidence intervals
    #This is a list with arrays of EPCs and their CI values and last read time in seconds with the format [EPC,lower_conf_val, upper_conf_val, last_read_time]
    epc_ci_list = split_pattern.findall(data_ci)
    window["-EventLog-"].print(f"{epc_ci_list}\n")
    #################-Erics code to check time and ci values-#####################
    ## Only return the values that have low time to read and high CI value (meaning they are likely in the location)
   # confident_tags = []

    ci_avg_tags = {}
    for item in epc_ci_list:
    #     # avg the upper and lower ci values
        ci_avg = (float(item[1]) + float(item[2]))/2

        last_read_time = float(item[-1])
        epc_val = item[0]
        if item_dictionary.get(epc_val) != None:
        #Creating a map of epc values read from the table and their average ci value + last read time 
            ci_avg_tags.update({epc_val : [ci_avg, last_read_time]})
    #     ##if the read time is less than 2 (tag was just read)
    #     if(last_read_time < 2 or ci_avg > .75): # and epc_val[-3:] not in table_list:
    #         ##if the avg CI is high 
    #         confident_tags.append(item[0])
                #table_list.append(item[0][-3:]) #add last 3 chars of each epc to the list
        
        # ##otherwise remove from list 
        # elif(last_read_time > 2 or ci_avg < .8) and epc_val[-3:] in table_list:
        #     table_list.remove(epc_val[-3:])
    return ci_avg_tags
    #return epc_ci_list
    # return confident_tags


#Going to refactor this back to returning the list of EPCS + CI values to be able to use for comparing with the cabinet
def TABLEhandleCIResponse(regex): 
    global window
    
    #Extract all values after the initial three characters marking the type of packet
    data_ci = regex.group(1)

    split_pattern = re.compile(r"b'([0-9A-Fa-f]{24})': \[([0-9.]+), ([0-9.]+), ([0-9.]+)\]")

    #Grabbing all EPC's and confidence intervals
    #This is a list with arrays of EPCs and their CI values and last read time in seconds with the format [EPC,lower_conf_val, upper_conf_val, last_read_time]
    epc_ci_list = split_pattern.findall(data_ci)
    #print(epc_ci_list)
    #window["-EventLog-"].print(f"{epc_ci_list}\n")
    #################-Erics code to check time and ci values-#####################
    ## Only return the values that have low time to read and high CI value (meaning they are likely in the location)
    ci_avg_tags = {}
    for item in epc_ci_list:
    #     # avg the upper and lower ci values
        ci_avg = (float(item[1]) + float(item[2]))/2

        last_read_time = float(item[-1])
        epc_val = item[0]
        if item_dictionary.get(epc_val) != None:
        #Creating a map of epc values read from the table and their average ci value + last read time 
            ci_avg_tags.update({epc_val : [ci_avg, last_read_time]})
    #     ##if the read time is less than 2 (tag was just read)
    #     if(last_read_time < 4 or ci_avg > .5): # and epc_val[-3:] not in table_list:
    #         ##if the avg CI is high 
    #         confident_tags.append(item[0])
                #table_list.append(item[0][-3:]) #add last 3 chars of each epc to the list
        
        # ##otherwise remove from list 
        # elif(last_read_time > 2 or ci_avg < .8) and epc_val[-3:] in table_list:
        #     table_list.remove(epc_val[-3:])


    return ci_avg_tags
    #return epc_ci_list
    # return confident_tags


#Function to ultimately compare the RFID values from both readers + the CV and return the set of items on the table that were detected 
def compareRfidCi():
    global client_ci_list
    global table_set
    global cabinet_set
    global recipe_cabinet_set
    global recipe_table_set
    global distactor_table_set

    #make 3 seperate lists for table, cabinet, and CV
    table_tags = client_ci_list['Table']
    cabinet_tags= client_ci_list['Cabinet']
    
    #Use this as a last resort if don't see any Ci value?
    # CV TURNED OFF!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # cv_list = client_ci_list['CV']

    #Looping through items in the recipe, then removing them from the table/cabinet tag lists to determine the distractors left over
    
    #First loop through and check for all recipe items 
    recipe_set = set(list(recipe_map))
    print("Before recipe loop, set: " + str((recipe_set)))


    for epc in recipe_set:

        #FIXME: assume it is possible to have an epc not in either
        if not epc in table_tags and not epc in cabinet_tags:
            continue

        #FIXME: assume possible to get item in the cabinet but not table, so do the inverse of what we do below
        if not epc in table_tags:
            table_analog = copy.deepcopy(cabinet_tags[epc])
            table_analog[0] = 0.0
            table_analog[1] = 100
            table_tags[epc] = table_analog
        
        #Should already be in the table tag list bc we send all recipe epcs when server starts reading 
        #print("EPC value " + str(epc))
        table_read_vals = table_tags[epc]

        #FIXME: I am 90% sure the "should" above is not right... I don't think we ever ensure the recipe items have an analog in the reader lists
        #to patch this, I am adding a bypass and value fill since we will remove it anyway
        if not epc in cabinet_tags:
            cabinet_analog = copy.deepcopy(table_read_vals)
            cabinet_analog[0] = 0.0
            cabinet_analog[1] = 100
            cabinet_tags[epc] = cabinet_analog
        
        cabinet_read_vals = cabinet_tags[epc]

        #Getting the two CI values and last read times to compare 
        table_epc_ci = table_read_vals[0]
        table_read_time = table_read_vals[1]
        cabinet_epc_ci = cabinet_read_vals[0]
        cabinet_read_time = cabinet_read_vals[1]

        #Compare the CI values + remove items from table_tags and cabinet_tags found 
        if (table_epc_ci > 0.25 or table_read_time < 3) and (cabinet_epc_ci < 0.25 or cabinet_read_time > 3):
            
            #If the table epc ci value is at least 25% confident and read time within last 4s and cabinet reader doesn't detect 
            table_set.add(item_dictionary.get(epc))
            # print("printing table_tags[epc]: ")
            # print(table_tags[epc])
            del table_tags[epc]
            del cabinet_tags[epc]
            #cabinet_tags.remove(epc)

            item = str(item_dictionary.get(epc))

            if item in recipe_cabinet_set:
                recipe_cabinet_set.remove(item)
                recipe_table_set.add(item)
            recipe_table_set.add(item)

            #Print_Buffer.__post_message_async__("Item " + str(item_dictionary.get(epc))+ " found on table")
            print("Item: " + item + " found on table! YAY!")
        elif (cabinet_epc_ci > 0.25 or cabinet_read_time < 3) and (table_epc_ci < 0.25 or table_read_time > 3):
            #If the cabinet epc ci value is at least 25% confident and read time within last 4s and table reader doesn't detect 
            #cabinet_set.add(recipe_map[epc])
            #table_tags.remove(epc)

            #FIXME: We have to remove these if the tags are assumed to be in both the table list and the cabinet list
            del table_tags[epc]
            del cabinet_tags[epc]
            
            #cabinet_tags.remove(epc)
            item = str(item_dictionary.get(epc))

            if item in recipe_table_set:
                recipe_table_set.remove(item)
                recipe_cabinet_set.add(item)

            recipe_cabinet_set.add(item)

            #Tell the user that the item is in their cabinet 
            #Print_Buffer.__post_message_async__("Item " + str(item_dictionary.get(epc))+ " found in cabinet")
            print("Recipe item: " + item + " found in cabinet!")
            #Return or break
            break
        else:
            print("CV handling")
            
            #Check the CV here to see if possible readers are not reading 
            #Then if the item isn't detected by the CV, output a message saying its missing and break or continue?
            #Get the item name from the epc

            #Boolean for tracking if an item is missing or not for the CV
            missing = True
            item_name = item_dictionary.get(epc)
            #print(item_name)
            if shm_dict[item_name] > 0.0:
                print("CV Detected Item! ")
                table_set.add(item_dictionary.get(epc))
                #table_tags.remove(epc)
                #cabinet_tags.remove(epc)
                del table_tags[epc]
                del cabinet_tags[epc]
                missing = False

            #FIXME: If we make it down here, the table doesn't see it, the cabinet doesn't see it, and the CV doesn't see it. That means that it can't be a distractor
            #no idea where it is, but we also shouldn't give a shit about that right now
            del table_tags[epc]
            del cabinet_tags[epc]
           
           
            #Loop through the items that the CV sees 
            # for cv_item in cv_list:
            #     print('CV Item CI: ' + str(cv_item))

            #     #IF the CV detects the item at this point, mark it as there...
            #     if cv_item[0] == item_name and cv_item[1] > 0.0:
            #         print("CV Detected Item! ")
            #         table_set.add(item_dictionary.get(epc))
            #         table_tags.remove(epc)
            #         cabinet_tags.remove(epc)
            #         missing = False
            #         break

            #Have the speaker tell the user that the item is missing 
            if missing:
                print("missing item?")
                return
            #return or break?
    
    #Go through the leftover's (distractors) and figure out what items remain and where 
    if (len(table_tags) != 0):
        #Notify the user that a distractor was detected on the table 
        print("Distractors detected!")
        
        for epc in list(table_tags):
            
            #Should already be in the table tag list bc we send all recipe epcs when server starts reading 
            table_read_vals = table_tags[epc]
            

            #Getting the two CI values and last read times to compare 
            table_epc_ci = table_read_vals[0]
            table_read_time = table_read_vals[1]
            
            #Compare the CI values + remove items from table_tags and cabinet_tags found 
            if (table_epc_ci > 0.33 and table_read_time < 2):
                #Tell the user that a distractor item is here
                print("Distractor item: " + str(epc) +" found on table")
                distactor_table_set.add(item_dictionary.get(epc))
                #Probably want to break here or something to get the process started again?
                #Return or break?
                return

            elif (table_epc_ci < 0.33 or table_read_time > 2):
                #Continue as usual. Item maybe moved?
                if item_dictionary.get(epc) in distactor_table_set:
                    distactor_table_set.remove(item_dictionary.get(epc))
                    
                continue
                

        
        
    print("All items found!")


def writeJSONFile(fileName, data):
    with open(fileName, 'w') as fp:
        json.dump(data, fp)
 
def readJSONFile(fileName):
    f = open(fileName)
    return json.load(f)

def draw_img():
    #grab image from shared mem and convert
    current_frame_grabbed = np.ndarray(current_frame.shape, dtype=current_frame.dtype, buffer=shm_cam.buf)
    image = Image.fromarray(current_frame_grabbed)

    #override image in sg
    image.thumbnail((400, 400))
    photo_img = ImageTk.PhotoImage(image)
    window["image"].update(data=photo_img)

def jump_to_entry():
    messages = [
        "Entring object entry mode. Please place tracking stickers on the desired item and place the item in front of the sensor.",
        "Rotate object so a different tag is facing the sensor again and wait 5 seconds",
        "Rotate object again so a different tag is facing the sensor again and wait 5 seconds",
        "Rotate object one last time so a different tag is facing the sensor again and wait 5 seconds",
        "Object successfully saved."
    ]

    tags = set()

    for message in messages:
        
        #speak
        Print_Buffer.__post_message__(message)

        #wait 
        time.sleep(1)

        #Check that a client is connected
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
    
        #Attempting to send the selected client from the dropdown the Find command
        try:
            client_socket = values["cur-reader"]

            #Grab the IP from the dictionary entry
            for ip in client_socket:
                client_selected= client_socket[ip]  
            
            #Send the command to the selected client
            server_socket.sendto(b'Find', client_selected)
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
        
        time.sleep(2)
        try:
            data, client_address = server_socket.recvfrom(1024)
            
            #TRF denotes a Table Reader Find Response packet
            table_find_regex = re.match(r'.*TRF(.*)', data.decode('utf-8'))

            if(table_find_regex):
                epc = handleFindResponse(table_find_regex)
            
            tags = tags.union(epc)
        except:
            continue
    
    #done write to file
    print(tags)
    for epc in tags:
        tags_dict = {}
        tags_dict[epc] = values["item-name"]
        save_to_database(tags_dict)
        item_dictionary.update({epc : values["item-name"]})
    
    epc_in_kitchen = values["item-name"]
    window["epc-inventory"].update(value=str(epc_in_kitchen), values=list(item_dictionary.values()))
    window["-EventLog-"].print(f"Item Updated! Items in inventory: {item_dictionary}\n")

def jump_to_entry_voice():
    messages = [
        "Entring object entry mode. Please place tracking stickers on the desired item and place the item in front of the sensor.",
        "Rotate object so a different tag is facing the sensor again and wait 5 seconds",
        "Rotate object again so a different tag is facing the sensor again and wait 5 seconds",
        "Rotate object one last time so a different tag is facing the sensor again and wait 5 seconds",
        "Object successfully saved."
    ]

    tags = set()

    for message in messages:
        
        #speak
        Print_Buffer.__post_message__(message)

        #wait 
        time.sleep(1)

        #Check that a client is connected
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
    
        #Attempting to send the selected client from the dropdown the Find command
        try:
            client_socket = values["cur-reader"]

            #Grab the IP from the dictionary entry
            for ip in client_socket:
                client_selected= client_socket[ip]  
            
            #Send the command to the selected client
            server_socket.sendto(b'Find', client_selected)
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
        
        time.sleep(2)
        try:
            data, client_address = server_socket.recvfrom(1024)
            
            #TRF denotes a Table Reader Find Response packet
            table_find_regex = re.match(r'.*TRF(.*)', data.decode('utf-8'))

            if(table_find_regex):
                epc = handleFindResponse(table_find_regex)
            
            tags = tags.union(epc)
        except:
            continue
    
    #done write to file
    print(tags)
    for epc in tags:
        tags_dict = {}
        tags_dict[epc] = values["item-name"]
        save_to_database(tags_dict)
        item_dictionary.update({epc : values["item-name"]})
    
    epc_in_kitchen = values["item-name"]
    window["epc-inventory"].update(value=str(epc_in_kitchen), values=list(item_dictionary.values()))
    window["-EventLog-"].print(f"Item Updated! Items in inventory: {item_dictionary}\n")


#stubbed save method
def save_to_database(tags):
    
    old_data = {}

    if os.path.isfile('kitchen.json'):
        old_data = readJSONFile("kitchen.json")
        
    old_data.update(tags)

    writeJSONFile("kitchen.json", old_data)

    print("Save_To_Database: kitchen.json")

initializeKitchen()
# Event loop to handle GUI Client/Server Communication
while True:
    
    #Can change the timeout if we want to have a faster UI
    event, values = window.read(timeout=250)

    #update image
    draw_img()

    #print(np.ndarray((100,), dtype=np.float64, buffer=shm.buf))
    #Close the server socket if exit button pressed and server socket still open
    if event == sg.WINDOW_CLOSED:
        if server_status:
            server_socket.close()
        break

    #Handles setting the power of connected clients
    elif event == "Set Power":
        
        #Check if a client is connected before attempting to set the power
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        
        #Check that the reader power input isn't empty
        if values["reader-power"] == "":
            window["-EventLog-"].print(f"Please type in a power value between 0 and 2700!\n")
            continue
        
        #Grabbing power value from input box
        reader_power = int(values["reader-power"])

        #Making sure the reader power input is between 0-2700 which is the supported range for our M6E Nano Chip
        if(reader_power < 0 or reader_power > 2700):
            window["-EventLog-"].print(f"Please type in a power value between 0 and 2700!\n")
            continue

        try:
            #Grab the current client reader selected in the dropdown
            client_socket = values["cur-reader"]
            
            #Grab the IP from the dictionary entry
            for ip in client_socket:
                client_selected= client_socket[ip] 
            
            #Construct the client payload 
            client_power = "Power " + str(reader_power)
            
            #Send the Power command to the client selected
            server_socket.sendto(client_power.encode('utf-8'), client_selected)
        except:
            window["-EventLog-"].print(f"Failed to set reader power!\n")
            continue
    #Requests the selected client to read for items and return a list of the EPC values to use for updating
    elif event == "Find Item":

        jump_to_entry()

        '''
        #Check that a client is connected
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        
        #Attempting to send the selected client from the dropdown the Find command
        try:
            client_socket = values["cur-reader"]

            #Grab the IP from the dictionary entry
            for ip in client_socket:
                client_selected= client_socket[ip]  
            
            #Send the command to the selected client
            server_socket.sendto(b'Find', client_selected)
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
        '''
    #Handles the tracking of items in the User's Kitchen or Inventory by mapping tag EPC's to Item names
    elif event == "Update Item":
        
        #Check that a client is connected
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        
        #Check that the user has selected a valid EPC to update or add to their inventory
        if(values["epc"] == "None"):
            window["-EventLog-"].print(f"Please click Find Item button and pick an EPC to update! \n")
            continue
        
        #Check that the user has input a name for the Item
        if(values["item-name"] == ""):
            window["-EventLog-"].print(f"Please input a new Item name!\n")
            continue
        
        #Add the item to the dictionary with its EPCs and given name
        for epc in epcs_to_update:
            item_dictionary.update({epc : values["item-name"]})
        
        epc_in_kitchen = values["item-name"]

        save_to_database(item_dictionary)
        window["epc-inventory"].update(value=str(epc_in_kitchen), values=list(item_dictionary.values()))
        window["-EventLog-"].print(f"Item Updated! Items in inventory: {item_dictionary}\n")
    #Starts the server up
    elif event == "server-btn" and server_status == False:
        
        #Get the address of the computer the server is running on 
        try:
            findIP()

            #Create a socket for the server to accept connections on
            server_socket= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_socket.bind(server_address)
            server_socket.settimeout(0.5)
        
            #Setting the server status to True to track status
            server_status = True
            window["-EventLog-"].print(f"RFID Server listening on {server_address}")

            #Update the Start server button to Stop Server
            window[event].update("Stop Server")
        except Exception as e:
            window["-EventLog-"].print(f"Failed to start server with error: {str(e)}")
    #Stops the server
    elif event == "server-btn" and server_status:
        #Update the server button 
        window[event].update("Start Server")
        
        #Close the socket for the server and update server status boolean
        server_socket.close()
        server_status = False
    #Handles connecting to the shared memory region
    elif event == "cv-btn" and region_bool == False:
        try:
            connectCV()
            window[event].update("Disconnect CV")
        except Exception as e:
           window["-EventLog-"].print(f"Please start CV program first!: {str(e)}\n") 
    elif event == "cv-btn" and region_bool:
        connectCV()
        window[event].update("Connect CV")
    elif event == "add-item":
        item_to_add = values["epc-inventory"]
        addItemToRecipe(item_to_add)
    elif event == "remove-item":
        item_to_remove = values["recipe-items"]
        removeItemFromRecipe(item_to_remove)
    #Requests that all connected clients start reading and pushing data to the server
    elif event == "server-read" and server_read_status == False:
        
        #Check if there are any clients connected 
        if len(connected_readers) == 0:
            window["-EventLog-"].print(f"Please connect clients first!\n")
            continue
        
        #Send Read command to all connected clients
        try:
            epc_bytes_list = []
            print("Recipe Map: " + str(recipe_map))
            for epc_str in list(recipe_map):
                epc_bytes = bytes.fromhex(epc_str)
                epc_bytes_list.append(bytes(epc_str, encoding="utf-8"))  # Prepend b to create byte literal
                
            print(epc_bytes_list)
            for client_addr in client_addrs:
                client_selected= client_addr
                msg ="*RRU*"+ str(epc_bytes_list) +'\n'
            
                #Send the payload to the server for the client reads
                #First payload contains all EPCs in recipe 
                server_socket.sendto(bytes(msg, encoding="utf-8"), client_selected)

                #Maybe move this to be inside the handleCIfunctions when initial cabinet is still true?
                server_socket.sendto(b'Read', client_selected)
            last_announcement_time = time.time()
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
        
        #Set the server read status and button
        server_read_status = True
        window[event].update("Stop Reading")
    #Requests that all connected clients terminate reading
    elif event == "server-read" and server_read_status:
        
        #Check if any connected clients just in case
        if len(connected_readers) == 0:
            window["-EventLog-"].print(f"Please connect clients first!\n")
            continue
       
        #Send Read command to all connected clients
        try:
            for client_addr in client_addrs:
                client_selected= client_addr
                server_socket.sendto(b'Read', client_selected)
        except:
            window["-EventLog-"].print(f"Failed to stop reading!\n")
            continue

        #Update reading button and status
        window[event].update("Start Reading")
        server_read_status = False
    
    #Main logic to handle Client Server data exchange

    if region_bool:
        if cv_timer == 0:
            cv_timer = time.time()
            c = np.ndarray((8,), dtype=np.float64, buffer=shm.buf)
            client_ci_list.update({'CV' : c})
            window["-EventLog-"].print(f"CV values: {c}\n")
        elif time.time() - cv_timer > 1:
            cv_timer = 0
            c = np.ndarray((8,), dtype=np.float64, buffer=shm.buf)
            client_ci_list.update({'CV' : c})
            window["-EventLog-"].print(f"CV values: {c}\n")
        
    if server_status:
        
        #Read from the clients
        try:

            
            #every 10 seconds (could change to number of reads)
            if time.time() - last_announcement_time >= 10 and server_read_status:
                print("doing check for speaking")
                print(time.time())
                print(last_announcement_time)

                 # Reset the timer
                last_announcement_time = time.time()
                testSpeech(len(recipe_table_set) == len(set(items_in_recipe)) and len(distactor_table_set) == 0) #just check the set that has names in it
                

                print(",")
                print(last_announcement_time)
                #
            

                    

               


            data, client_address = server_socket.recvfrom(1024)
            
            #TRF denotes a Table Reader Find Response packet
            table_find_regex = re.match(r'.*TRF(.*)', data.decode('utf-8'))

            #TRR denotes a Table Reader Read packet
            table_read_regex = re.match(r'.*TRR(.*)', data.decode('utf-8')) 
            
            #CRF denotes a Cabinet Reader Find Response packet
            cabinet_find_regex = re.match(r'.*CRF(.*)', data.decode('utf-8'))

            #CRR denotes a Cabinet Reader Read packet
            cabinet_read_regex = re.match(r'.*CRR(.*)', data.decode('utf-8')) 

            #TCI denotes a Table reader confidence interval list
            table_ci_regex = re.match(r'.*TCI(.*)', data.decode('utf-8'))

            #CCI denotes a Cabinet reader confidence interval list
            cabinet_ci_regex = re.match(r'.*CCI(.*)', data.decode('utf-8'))
            if(table_find_regex):
                epc = handleFindResponse(table_find_regex)
            elif(table_read_regex):
                epc = handleReadResponse(table_read_regex)
                #Eventually may change format of data being sent from client to server... For now just add the epc to the clients dictionary if it isn't there already 
                #table_set.add(epc)
            elif(cabinet_find_regex):
                epc = handleFindResponse(cabinet_find_regex)
            elif(cabinet_read_regex):
                epc = handleReadResponse(cabinet_read_regex)
                #Eventually may change format of data being sent from client to server... For now just add the epc to the clients dictionary if it isn't there already 
                #cabinet_set.add(epc)
            elif(table_ci_regex and table_read==False):
                #Should return a map of EPC's and their CI avg and last read time {EPC : [CI_AVG, LAST_READ_TIME]}
                epcs = TABLEhandleCIResponse(table_ci_regex)
                client_ci_list.update({'Table' : epcs})
                table_read = True
                #Eventually may change format of data being sent from client to server... For now just add the epc to the clients dictionary if it isn't there already 
                #Need to figure out what to do with EPC's and CI values after reading them in... This should be where the server maybe makes decisions based on CI values + CV..
                #table_ci_set.add(epcs)
            elif(cabinet_ci_regex and cabinet_read==False):
                #Should return list of epcs + CI values
                epcs = CABINEThandleCIResponse(cabinet_ci_regex)
                client_ci_list.update({'Cabinet' : epcs}) 
                cabinet_read = True
            elif data.decode('utf-8') == "Table Reader Connected":
                window["-EventLog-"].print(f"Connected to Table Reader @ {client_address}")
                
                #Map the table reader name to the IP address of the client. Note this would have to change for a setup with more than two readers
                reader_info = {"table-reader" : client_address}
                
                #Append the client address to the array tracking connected readers/clients
                client_addrs.append(client_address)
                connected_readers.append(reader_info)    
                
                #Update the values in the connected readers dropdown 
                window["cur-reader"].update(value=str(reader_info), values=connected_readers)
                reader_status = True
            #Handles when the cabinet reader connects to the server
            elif data.decode('utf-8') == "Cabinet Reader Connected":
                window["-EventLog-"].print(f"Connected to Cabinet Reader @ {client_address}")
                
                #Map the cabinet reader name to the IP address of the client. Note this would have to change for a setup with more than two readers
                reader_info = {"cabinet-reader" : client_address}
                
                #Append the client address to the array tracking connected readers/clients
                connected_readers.append({"cabinet-reader" : client_address})
                client_addrs.append(client_address)
                
                #Update the values in the connected readers dropdown 
                window["cur-reader"].update(value=str(reader_info), values=connected_readers)
                reader_status = True
            #Handles Client Disconnections
            elif data.decode('utf-8') == "Client Disconnected":
                
                #Remove the client with the given address from the client address array 
                client_addrs.remove(client_address)
                
                #Remove the connected client from the list of clients 
                for client in connected_readers:
                    connected_readers.remove(client)
                window["cur-reader"].update(values=connected_readers)
            
            #Prints any messages from the client that don't fall under one of these above conditions
            else:
                window["-EventLog-"].print(f"Client says: {data.decode('utf-8')} \n") 
               
               

        except:
            continue
        
        #Checking if we have CI values from both clients 
        if table_read and cabinet_read:
            table_read = not table_read
            cabinet_read = not cabinet_read
            print("Table and cabinet read, comparing RFID stuff")
            #Function to compare CI values of clients 
            compareRfidCi()
            

            #Clearing the last two client RFID reads
            client_ci_list = {}
            table_set = set()
            cabinet_set = set()
    

# Close the window
window.close()

#close segment
shm.close()
