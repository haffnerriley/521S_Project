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
import copy
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

#Function to initilize the kitchen using the items saved in the kitchen.json file 
def initializeKitchen():
    global item_dictionary

    #Check if the kitchen.json file exisits and extract its contents
    old_data = {}
    if os.path.isfile('kitchen.json'):
        old_data = readJSONFile("kitchen.json")
    #Set the list of kitchen items in the dropdown to be the contents of the json file
    if(len(old_data) > 0):
        item_dictionary = old_data
        epc_in_kitchen = list(item_dictionary.values())[0]
        window["epc-inventory"].update(value=str(epc_in_kitchen), values=list(item_dictionary.values()))

#Function to find the IP address of computer running the server program
def findIP():
    global ipaddr
    global server_address

    #Loop through network interfaces on the server to get server IP address 
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

#Function to handle announcing all items that are found including the distractors and recipe items
def announceItems(cause):
    global recipe_map
    global recipe_table_set
    global distactor_table_set

    #build string for items that need to be removed
    remove_items = ""
    for item in distactor_table_set:
        if remove_items == "":
            remove_items = "Remove "
        remove_items += (" " + item) 

    #Message for the voice buffer
    messages = ["You have " + str(len(recipe_table_set)) + "required items and " +  str(len(distactor_table_set)) +  " distractors on the table, " + remove_items,
        "All required items found with no distractors",
    ]

    #Speak using the voice buffer. Note: We had a strange bug that we figured out was caused by the main gui event loop. Adding a while true that immediately returns fixed the timing priority bug
    while 1 == 1:
        Print_Buffer.__post_message_async__(messages[cause])
        return

#Function to handle the reader find reponse sent to the server
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

    #Check if the region is open already and close it
    if region_bool:
       shm.close()
       region_bool = not region_bool
    else:
        #Otherwise, open the shared memory region if CV isn't connected already
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
        
        #Loop through the items in the kitchen and add all EPCs to the recipe map that match
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

    #Check if there are items in the recipe list first
    if item == "None":
        window["-EventLog-"].print(f"Please add items to kitchen using the Update button first!\n")
    else:
        #Remove the item from the recipe list
        items_in_recipe.remove(default_item)
        for key, value in item_dictionary.items():
            if default_item == value:
                recipe_map.remove(key)
        
        #Change the default recipe item to be the first item in the list
        if(len(items_in_recipe) > 0):
            default_item = items_in_recipe[0]
        else:
            default_item = "None"
        
        window["recipe-items"].update(value=str(default_item), values=items_in_recipe)

#Handles the read response from the clients to the server
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
        #Return the extracted EPC
        return extracted_epc
    else:
        window["-EventLog-"].print(f"{data_read}\n")
    
    return None


#Handles the confidence intervals sent from the cabinet client to the server. Note: Again, we hadn't realized the timing bug at this point so we duplicated the CI response functions to work for both clients
def CABINEThandleCIResponse(regex): 
    global window
   
    #Extract all values after the initial three characters marking the type of packet
    data_ci = regex.group(1)
    
    #Grab all EPC values and confidence intervals using regular expressions
    split_pattern = re.compile(r"b'([0-9A-Fa-f]{24})': \[([0-9.]+), ([0-9.]+), ([0-9.]+)\]")
    
    #This is a list with arrays of EPCs and their CI values and last read time in seconds with the format [EPC,lower_conf_val, upper_conf_val, last_read_time]
    epc_ci_list = split_pattern.findall(data_ci)
    window["-EventLog-"].print(f"{epc_ci_list}\n")

    #Go through all the tags in the list returned from the client
    ci_avg_tags = {}
    for item in epc_ci_list:
        # avg the upper and lower ci values
        ci_avg = (float(item[1]) + float(item[2]))/2
        
        #Extract the last read time
        last_read_time = float(item[-1])
        
        #Grab the EPC value
        epc_val = item[0]

        #Check if the item is in the kitchen's inventory or if it should be ignored
        if item_dictionary.get(epc_val) != None:
        #Creating a map of epc values read from the table and their average ci value + last read time 
            ci_avg_tags.update({epc_val : [ci_avg, last_read_time]})
    
    return ci_avg_tags


#Handles the Confidence interval responses from the Table reader
def TABLEhandleCIResponse(regex): 
    global window
    
    #Extract all values after the initial three characters marking the type of packet
    data_ci = regex.group(1)

    #Grab the EPC value, Confidence interval and the last read time
    split_pattern = re.compile(r"b'([0-9A-Fa-f]{24})': \[([0-9.]+), ([0-9.]+), ([0-9.]+)\]")

    #This is a list with arrays of EPCs and their CI values and last read time in seconds with the format [EPC,lower_conf_val, upper_conf_val, last_read_time]
    epc_ci_list = split_pattern.findall(data_ci)
    
    ## Only return the values that have low time to read and high CI value (meaning they are likely in the location)
    ci_avg_tags = {}
    for item in epc_ci_list:
        # avg the upper and lower ci values
        ci_avg = (float(item[1]) + float(item[2]))/2

        #Get the last read time and the EPC value
        last_read_time = float(item[-1])
        epc_val = item[0]
        
        if item_dictionary.get(epc_val) != None:
        #Creating a map of epc values read from the table and their average ci value + last read time 
            ci_avg_tags.update({epc_val : [ci_avg, last_read_time]})

    return ci_avg_tags


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
    #Note the CV was turned off in the demo so this line was commented out
    cv_list = client_ci_list['CV']

    #Looping through items in the recipe, then removing them from the table/cabinet tag lists to determine the distractors left over
    #First loop through and check for all recipe items 
    recipe_set = set(list(recipe_map))
    for epc in recipe_set:

        #Assume it is possible to have an epc not in either
        if not epc in table_tags.keys() and not epc in cabinet_tags.keys():
            continue

        #Assume possible to get item in the cabinet but not table, so do the inverse of what we do below
        if not epc in table_tags.keys():
            table_analog = copy.deepcopy(cabinet_tags[epc])
            table_analog[0] = 0.0
            table_analog[1] = 100
            table_tags[epc] = table_analog
        
        #Should already be in the table tag list bc we send all recipe epcs when server starts reading 
        table_read_vals = table_tags[epc]

        #I am 90% sure the "should" above is not right... I don't think we ever ensure the recipe items have an analog in the reader lists
        #to patch this, I am adding a bypass and value fill since we will remove it anyway
        if not epc in cabinet_tags.keys():
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
            
            #If the table epc ci value is at least 25% confident and read time within last 3s and cabinet reader doesn't detect 
            table_set.add(item_dictionary.get(epc))
            del table_tags[epc]
            del cabinet_tags[epc]

            #Grab the item name
            item = str(item_dictionary.get(epc))

            #Remove the item found from the cabinet set and add it to the table set
            if item in recipe_cabinet_set:
                recipe_cabinet_set.remove(item)
                recipe_table_set.add(item)
            recipe_table_set.add(item)

        elif (cabinet_epc_ci > 0.25 or cabinet_read_time < 3) and (table_epc_ci < 0.25 or table_read_time > 3):
            #If the cabinet epc ci value is at least 25% confident and read time within last 3s and table reader doesn't detect 

            #We have to remove these if the tags are assumed to be in both the table list and the cabinet list
            del table_tags[epc]
            del cabinet_tags[epc]

            #Get the tiem name
            item = str(item_dictionary.get(epc))

            #Remove the item from the table set and add it to the cabinet set
            if item in recipe_table_set:
                recipe_table_set.remove(item)
                recipe_cabinet_set.add(item)
            #Adding again due to bug... Shouldn't break things because using a set
            recipe_cabinet_set.add(item)

        else:
            #Check the CV here to see if possible readers are not reading 
            #Then if the item isn't detected by the CV, output a message saying its missing and continue

            #Boolean for tracking if an item is missing or not for the CV
            missing = True
            item_name = item_dictionary.get(epc)
            
            #Check if the CV found any items in the recipe list that have high confidence values
            if shm_dict[item_name] > 0.0:
                
                #Remove the tags from the tabe and cabinet tags lists
                table_set.add(item_dictionary.get(epc))
                del table_tags[epc]
                del cabinet_tags[epc]
                missing = False

            #If we make it down here, the table doesn't see it, the cabinet doesn't see it, and the CV doesn't see it. That means that it can't be a distractor
            #no idea where it is, but we also shouldn't give a shit about that right now
            del table_tags[epc]
            del cabinet_tags[epc]

    #Checking if tags were not properly deleted if found
    for epc in recipe_set:
        if epc in table_tags.keys():
            del table_tags[epc]
        if epc in cabinet_tags.keys():
            del cabinet_tags[epc]
    
    #Go through the leftover's (distractors) and figure out what items remain and where 
    if (len(table_tags) != 0):
        #Notify the user that a distractor was detected on the table 
        
        for epc in list(table_tags):
            
            #Should already be in the table tag list bc we send all recipe epcs when server starts reading 
            table_read_vals = table_tags[epc]
            
            #Getting the two CI values and last read times to compare 
            table_epc_ci = table_read_vals[0]
            table_read_time = table_read_vals[1]
            
            #Compare the CI values + remove items from table_tags and cabinet_tags found 
            if (table_epc_ci > 0.33 and table_read_time < 2):
                #Tell the user that a distractor item is here
                distactor_table_set.add(item_dictionary.get(epc))
                return

            elif (table_epc_ci < 0.33 or table_read_time > 2):
                #Continue as usual.
                if item_dictionary.get(epc) in distactor_table_set:
                    distactor_table_set.remove(item_dictionary.get(epc))
                    
                continue

#Function to write to the json file
def writeJSONFile(fileName, data):
    with open(fileName, 'w') as fp:
        json.dump(data, fp)

#Function to read the json file 
def readJSONFile(fileName):
    f = open(fileName)
    return json.load(f)

#Function to handle displaying the CV image in the GUI
def draw_img():
    #grab image from shared mem and convert
    current_frame_grabbed = np.ndarray(current_frame.shape, dtype=current_frame.dtype, buffer=shm_cam.buf)
    image = Image.fromarray(current_frame_grabbed)

    #override image in sg
    image.thumbnail((400, 400))
    photo_img = ImageTk.PhotoImage(image)
    window["image"].update(data=photo_img)

#Function to handle the speech timing bug we found. This function handles Item entry and directs the user to scan in a new item
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
        
        #speak to the user using the messages above
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
    
    #Write to the kitchen.json file to save the new item entered
    for epc in tags:
        tags_dict = {}
        tags_dict[epc] = values["item-name"]
        save_to_database(tags_dict)
        item_dictionary.update({epc : values["item-name"]})
    
    epc_in_kitchen = values["item-name"]
    window["epc-inventory"].update(value=str(epc_in_kitchen), values=list(item_dictionary.values()))
    window["-EventLog-"].print(f"Item Updated! Items in inventory: {item_dictionary}\n")

#Function that will save all tags provided to the database (Just a JSON file...)
def save_to_database(tags):
    
    old_data = {}
    #Check if the file exists and read from it before updating the entries
    if os.path.isfile('kitchen.json'):
        old_data = readJSONFile("kitchen.json")
        
    old_data.update(tags)

    #Write to the JSON file and update it
    writeJSONFile("kitchen.json", old_data)

#Calling the initialize kitchen function to update the GUI with saved kitchen items
initializeKitchen()
# Event loop to handle GUI Client/Server Communication
while True:
    
    #Main event loop that handles all window events and values
    event, values = window.read(timeout=250)

    #update image on GUI
    draw_img()

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
    #Handles disconnecting from the CV
    elif event == "cv-btn" and region_bool:
        connectCV()
        window[event].update("Connect CV")
    #handles the add item to recipe button
    elif event == "add-item":
        item_to_add = values["epc-inventory"]
        addItemToRecipe(item_to_add)
    #Handles the remove item from recipe button
    elif event == "remove-item":
        item_to_remove = values["recipe-items"]
        removeItemFromRecipe(item_to_remove)
    #Requests that all connected clients start reading and pushing data to the server
    elif event == "server-read" and server_read_status == False:
        
        #Check if there are any clients connected 
        if len(connected_readers) == 0:
            window["-EventLog-"].print(f"Please connect clients first!\n")
            continue
        
        #Send Read command to all connected clients to get them to start reading
        try:
            epc_bytes_list = []
            for epc_str in list(recipe_map):
                epc_bytes = bytes.fromhex(epc_str)
                epc_bytes_list.append(bytes(epc_str, encoding="utf-8"))  # Prepend b to create byte literal
            
            #Send the initial recipe list to all connected clients to initilize their EPC CI values
            for client_addr in client_addrs:
                client_selected= client_addr
                msg ="*RRU*"+ str(epc_bytes_list) +'\n'
            
                #Send the payload to the server for the client reads
                #First payload contains all EPCs in recipe 
                server_socket.sendto(bytes(msg, encoding="utf-8"), client_selected)
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
    #Updates the most recent CV confidence values
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
        
    #If the server is up and running allow clients to connect and handle interaction
    if server_status:
        
        #Read from the clients
        try:
            
            #every 10 seconds (could change to number of reads)
            if time.time() - last_announcement_time >= 10 and server_read_status:
                # Reset the timer
                last_announcement_time = time.time()

                #Speak to the user and let them know what items were detected 
                announceItems(len(recipe_table_set) == len(set(items_in_recipe)) and len(distactor_table_set) == 0) #just check the set that has names in it

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
           
            #Handle client reponses. Note: This would be changed to JSON formated data in the future
            if(table_find_regex):
                epc = handleFindResponse(table_find_regex)
            elif(table_read_regex):
                epc = handleReadResponse(table_read_regex)
            elif(cabinet_find_regex):
                epc = handleFindResponse(cabinet_find_regex)
            elif(cabinet_read_regex):
                epc = handleReadResponse(cabinet_read_regex)
            elif(table_ci_regex and table_read==False):
                #Should return a map of EPC's and their CI avg and last read time {EPC : [CI_AVG, LAST_READ_TIME]}
                epcs = TABLEhandleCIResponse(table_ci_regex)
                client_ci_list.update({'Table' : epcs})
                table_read = True
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
