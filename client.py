#!/usr/bin/env python3
from __future__ import print_function
from queue import Queue
import PySimpleGUI as sg
import socket
import time
from datetime import datetime
import mercury
import select
import re
import json
import math
from collections import deque
import statistics

#RFID reader object
reader = "undefined"

#RFID Reader connection Status
reader_status = "disconnected"

#RFID reader power that can be changed by the user
reader_power = 1000

#Selected EPC to update through the find button 
epc_to_update = "None"

#Dictionary of items that the server maintains. Contains all the items the user has in their kitchen.
item_dictionary = {}

#Dictionary of items and the last time it was read 
item_read_times = {}

#List of EPCS that the server found using the Find button
epcs_to_update = []

#List of all client epcs to maintain while reading
epc_ci_list = []

#Previous RFID reads 
prev_read = []

#Previously read item for CI buffer clear 
prev_item_read = None

#Dictionary of EPC's, the read count, time-stamp, and other data stored here for client algo
item_confidence_vals = {}

#Checks if the server requested the client to read
reading_status = False

#Socket of RFID client
client_socket = None

#Status of server connection
server_status = False

#Address of server 
server_address = "undefined"

#Client message used in functions
client_msg = None

#Client identifier (Table, Cabinet). Can change in UI
client_id = None

#List of all EPC's the client has ever read 
client_epc_list = []

# Define the GUI layout for the client
layout = [
    [sg.Text("Server IP Address:"), sg.InputText("192.168.1.11", key="server-addr"),sg.Text("Server Port: "), sg.InputText("12345", key="server-port"), sg.Text("Client ID(Table, Cabinet...):"), sg.InputText("Table", key="client-id")],
    [sg.Text("Device URI:"), sg.InputText("tmr:///dev/ttyUSB0", key="connect-reader")],
    [sg.Text("Set Read Power (0-2700):"), sg.InputText(key="reader-power")],
    [sg.Text("EPC to Update:"), sg.Combo(epcs_to_update, default_value=epc_to_update, key="epc",size=(25,1), enable_events=True)],
    [sg.Text("New Item Name:"), sg.InputText(key="item-name")],
    [[sg.Button("Connect to Server", key="server-btn"), sg.Button("Connect to Reader"), sg.Button("Set Power"), sg.Button("Find Item"), sg.Button("Update Item"), sg.Button("Start Reading", key="read-btn")]],
    [sg.Multiline("", size=(50, 10), key="-EventLog-", disabled=True)]
]

# Create the window for the GUI
window = sg.Window("Smart Kitchen Client Application", layout,resizable=True, finalize=True)

#Helper function to check if valid IP address is provided by user.
def is_valid_ip(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

#Helper function to check if valid port number provided
def is_valid_port(port):
    try:
        port = int(port)
        return 0 < port <= 65535
    except ValueError:
        return False

#Function to handle setting the reader power from the server
def clientPower(power_level):
    global reader_power
    global reader
    global window
    
    #Grab the power value sent from the server (0-2700)
    reader_power = int(power_level)

    #Make sure the reader is actually connected 
    if(reader_status == "disconnected"):
        window["-EventLog-"].print(f"Please connect to reader first!\n")
        client_socket.sendto(b'Please connect to reader first!', server_address)
        return

    try:
        #Set the reader power, protocol, and number of antennas
        reader.set_read_plan([1], "GEN2", read_power=int(power_level))
    except:
        window["-EventLog-"].print(f"Failed to set reader power!\n")
        client_socket.sendto(b'Failed to set reader power!', server_address)
        return
    
    #Send the response to the server 
    window["-EventLog-"].print(f"Reader power set to {reader_power}\n")
    client_power_res = "Reader Power Set to " +str(reader_power)
    client_socket.sendto(client_power_res.encode("utf-8"), server_address)

#Function to handle server find commands sent to the reader
def clientFind():
    global reader_power
    global reader
    global window
    global client_socket
    global server_address

    #Check that the reader is actually connected
    if(reader_status == "disconnected"):
        window["-EventLog-"].print(f"Please connect to reader first!\n")
        client_socket.sendto(b"Please connect to reader first!\n", server_address)
        return
    
    try:
        #Use whatever power the user wants/last used power setting
        reader.set_read_plan([1], "GEN2", read_power=reader_power)
        
        #Trigger a read and return a list of all EPCs found
        epcs = map(lambda tag: tag.epc, reader.read())
        
        #Create a list of EPCS from the map
        epc_list = list(epcs)

        #Initialize an empty list of EPCs to send to the server 
        epc_list_for_server = []

        #This is hardcoded but can be improved to use whatever client names
        if(client_id == "Table"):
            #Create a bytearray of all EPCS to send to server 
            #Start with the string *TRF so that server can distinguish between table and cabinet find responses
            epc_list_for_server = bytearray("*TRF", 'utf-8')
        elif(client_id == "Cabinet"):
            epc_list_for_server = bytearray("*CRF", 'utf-8')
       
       #Checking if there are EPCS to add to our server payload 
        if len(epc_list) > 0:

            #Extending the buffer used to send to server
            for epc in epc_list:
                epc_list_for_server.extend(epc)

        #Send the list of EPCs to the server
        window["-EventLog-"].print(f"Server Found Items: {epc_list}\n")
        client_socket.sendto(epc_list_for_server, server_address)
        return
    except:
        window["-EventLog-"].print(f"Failed to start reading!\n")
        client_socket.sendto(b'Failed to start reading!', server_address)
        return


#Function that initializes all EPCs in the recipe that the readers should maintain confidence values and time stamps for 
def initializeEPCS(reader_recipe_update_regex):
    global epc_ci_list
    
    #Grab the matched expression of the EPCs sent from the server
    recipe_epcs = reader_recipe_update_regex.group(1)

    #Grab all EPC values send from client as a response to initilize recipe list command 
    split_pattern = re.compile(r"'([A-Fa-f0-9]{24})'")

    #Finding all occurences of 24 byte EPCS in the client response
    recipe_epc_list = split_pattern.findall(recipe_epcs)
    epc_ci_list = {}

    #update the list of EPCs to include all epcs in recipe to allow server + client algorithm to initilize CI values 
    for item in recipe_epc_list:
        #Initialize the confidence values for the recipe items 
        item = bytes(item, encoding="utf-8")
        epc_q = client_read(item, 0, True)
        ci_val = client_calc_confidence(epc_q, 0, item) #Calculate the confidence value here 
        epc_ci_list.update({item : ci_val})
    try:
        #Constructing payload for the server based on the client (Table, Cabinet) with EPC confidence values
        msg ="*" +client_id[0] +"CI*"+ str(epc_ci_list) +'\n'
        
        #Send the payload to the server for the client reads
        client_socket.sendto(bytes(msg, encoding="utf-8"), server_address)
    except Exception as e:
        window["-EventLog-"].print(f"Failed to send tag data to the server: {str(e)}\n") 

#Handles the queues that each EPC has associated with it for caluclating the hit/miss ratio. The read value should be 1 if a hit 0 if a miss
def client_read(EPC, read_val, first_read):
    global item_confidence_vals
    global client_epc_list
    global item_read_times
    global prev_item_read
   
    #If the item is being read for the first time add it to the dictionary and create a new entry for it
    if(item_confidence_vals.get(EPC) == None):
        
        #Add the new epc to the client list to use for updating each queue associated with the EPC
        client_epc_list.append(EPC) 
        epc_queue = Queue()
        epc_queue.put(read_val)
        epc_queue.put(read_val) #Adding a second read value to calculate stdev for initial read
        item_confidence_vals.update({EPC : epc_queue}) #Updating the item confidence values
        
        #If this is the recipe list being sent over (or the first read), then set the last read time to be a large number such that the item isn't immediately detected
        if(first_read):
            item_read_times.update({EPC : 500.0})
        else:
            item_read_times.update({EPC : time.time()})
        
        #Update the previous read time and return the epc queue 
        prev_item_read = read_val
        return epc_queue
    else:
        #Get the exisiting queue for the EPC
        epc_queue = item_confidence_vals.get(EPC)
        
        #Create a new queue to make sure that confidence values don't lag
        if(epc_queue.qsize() == 25): 
             
            #Clearing the entire queue to address CI values lagging 
            epc_queue = Queue()

            #Adding the last state read for this item to avoid divide by zero errors in CI calculation
            epc_queue.put(prev_item_read)
            epc_queue.put(read_val)
            
        else:
            epc_queue.put(read_val)
        
        #Update the confidence values for the current EPC
        item_confidence_vals.update({EPC : epc_queue})
        
        #If the item was just read, than update the last read time
        if(read_val == 1):
            item_read_times.update({EPC : time.time()})
        
        #Updating the last read time and returning the EPC queue 
        prev_item_read = read_val
        return epc_queue

#Calculate the number of hits (reads)
def calc_hits(EPC_QUEUE):
    
    #Create a new queue to store queue values while iterating 
    number_hits = 0
    temp_queue = Queue()
    
    #Loop through each epc read value (0,1) and add it up to calculate the number of hits 
    for epc in EPC_QUEUE.queue:
       num_str = epc 
       temp_queue.put(num_str)
       number_hits += num_str

    #Return the Queue and the number of hits
    return number_hits, temp_queue



#Function that returns a confidence interval for the given EPC based on the number of hits and misses
def client_calc_confidence(EPC_QUEUE, read_val, EPC):
    global item_read_times
   
    #Get the total number of reads, hits and the queue containing the hits/misses 
    num_reads = EPC_QUEUE.qsize()
    num_hits, EPC_QUEUE = calc_hits(EPC_QUEUE)
    
    #Calculate the hit miss ratio
    hit_miss_ratio = num_hits/num_reads
    temp_list = list(EPC_QUEUE.queue)

    #Calculate the Z-Score
    z_score = (read_val-hit_miss_ratio)/(1 if statistics.stdev(temp_list) == 0 else statistics.stdev(temp_list)) 
    
    #Calculate the Margin of Error 
    margin_of_error = abs(z_score*(math.sqrt(hit_miss_ratio*(1-hit_miss_ratio))/num_reads))
    
    #Get the time since this item was read 
    time_since_read = time.time() - item_read_times.get(EPC)
    
    #Calculate the Confidence Interval and include the last time the item was read 
    confidence_interval = [hit_miss_ratio - margin_of_error, hit_miss_ratio + margin_of_error, time_since_read]
    return confidence_interval


# Event loop to handle GUI & Client/Server Communication
while True:
    #Handles the window timeout and reads all events and values from the window
    event, values = window.read(timeout=100) 

    #Close the client socket if exit button pressed and client socket still open
    if event == sg.WINDOW_CLOSED:
        if server_status:
            client_socket.close()
        break
    #Handles the connect to reader button 
    elif event == "Connect to Reader":
        
        #Connect to reader using the path specified in the reader port input
        reader_port = values["connect-reader"]
        
        #Using the Mercury Python API, connect to the M6E nano reader 
        try:
            reader = mercury.Reader(reader_port, baudrate=115200)
        except:
            reader_status = "disconnected"
            window["-EventLog-"].print(f'Falied to connect to Reader! Please check device URI!\n')
            continue
        
        #Printing reader model and region to console
        window["-EventLog-"].print(f'Reader Connected: Model {reader.get_model()}\n')
        window["-EventLog-"].print(f'Supported Regions: {reader.get_supported_regions()}\n')
        
        #Set the reader region and default power
        reader.set_region("NA2")
        reader.set_read_plan([1], "GEN2", read_power=reader_power)
        reader_status = "connected"
    #Handles connecting to the server and the server button
    elif event == "server-btn" and server_status == False:
        
        try:
            # Connect to the server using given address and port in the input boxes
            server_address_input = str(values["server-addr"])
            server_port_input = str(values["server-port"])
            
            #Check that user input contains valid IP address and port number
            if is_valid_ip(server_address_input) and is_valid_port(server_port_input):
                server_address = (server_address_input, int(server_port_input))
            else:
                window["-EventLog-"].print(f"Please provide a valid Server IP and Port\n")
                continue

            #Create a client socket and connect to ther server address using the inputted values
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.connect(server_address)
            
            #Updating server connection status and button
            server_status = True
            window[event].update("Disconnect from Server")

            #Constructing the client connection message using the user specified client id (Table, Cabinet...)
            client_msg = bytes(values['client-id'] + ' Reader Connected', encoding='utf-8')
            
            #Checking user input
            if(client_msg == None):
                window["-EventLog-"].print(f"Please provide a client identifier like Table or Cabinet\n")
                continue
            else:
                #Send message to server that client connected
                client_socket.sendto(client_msg, server_address)
            
            #Saving client ID
            client_id = values['client-id']
            window["-EventLog-"].print(f"Connected to the server:\n")
        except Exception as e:
            window["-EventLog-"].print(f"Failed to connect to the server: {str(e)}\n")
    #Handles disconnecting from server
    elif event == "server-btn" and server_status:
        try:
            #Send message to server that disconnecting
            client_socket.sendto(b"Client Disconnected", server_address)
            
            #Close client socket and update server connection status and button
            client_socket.close()
            server_status = False
            window[event].update("Connect to Server")
            window["-EventLog-"].print(f"Disconnected from the server:\n")
        except Exception as e:
            window["-EventLog-"].print(f"Failed to connect to the server: {str(e)}\n")    
    #Handles setting the power on the client GUI
    elif event == "Set Power":
        
        #Check that the RFID reader is connected before setting power
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        #Check that power input is not empty
        if values["reader-power"] == "":
            window["-EventLog-"].print(f"Please type in a power value between 0 and 2700!\n")
            continue
        
        #Grab the value for the power from the reader power input box
        reader_power = int(values["reader-power"])
        
        #Making sure the reader power input is between 0-2700 which is the supported range for our M6E Nano Chip
        if(reader_power < 0 or reader_power > 2700):
            window["-EventLog-"].print(f"Please type in a power value between 0 and 2700!\n")
            continue
        
        try:
            #Set the reader power, protocol, and number of antennas
            reader.set_read_plan([1], "GEN2", read_power=reader_power)
        except:
            window["-EventLog-"].print(f"Failed to set reader power!\n")
            continue
        window["-EventLog-"].print(f"Reader power set to {reader_power} \n")
    #Handles finding items from the client GUI using the find button
    elif event == "Find Item":
        
        #Check if the reader is connected first
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue

        try:
            #Set the reader power, protocol, and number of antennas
            reader.set_read_plan([1], "GEN2", read_power=reader_power)
            
            #Grab the epcs from the reader response 
            epcs = map(lambda tag: tag.epc, reader.read())

            #Create a list of EPCS
            epc_list = list(epcs)

            window["-EventLog-"].print(f"Found Items: {epc_list}\n")
            
            #Check for number of EPCs found  
            if len(epc_list) > 0:
                #Grab the first EPC from the array
                epc_to_update = epc_list[0].decode("utf-8")
                
                #Set first value in array as default value in EPC dropdown and update dropdown list
                window["epc"].update(value=str(epc_to_update), values=epc_list)
                selected_item = item_dictionary.get(epc_to_update)
                
                #Check if the first item is in the dictionary
                if(selected_item != None):
                    epc_to_update = selected_item
                window["-EventLog-"].print(f"Selecting item: {epc_to_update}\n")
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
    #Handles updating items from the Client GUI. Note: This is just for testing as the server implements this feature.
    elif event == "Update Item":
        
        #Check that the reader is connected first
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        #Check that the EPC selected is in our list
        if(values["epc"] == "None"):
            window["-EventLog-"].print(f"Please click Find Item button and pick an EPC to update! \n")
            continue
        
        #Check that item name is given by user 
        if(values["item-name"] == ""):
            window["-EventLog-"].print(f"Please input a new Item name!\n")
            continue
        
        #Update the value of the EPC's name in the dictionary or add it
        item_dictionary.update({values["epc"].decode("utf-8") : values["item-name"]})
        window["-EventLog-"].print(f"Item Updated! Items in inventory: {item_dictionary}\n")
    #Used for setting the reading status on the GUI
    elif event == "read-btn" and reading_status == False:
        window[event].update("Stop Reading")
        reading_status = True
    #Used for setting the reading status on the GUI
    elif event == "read-btn" and reading_status:
        window[event].update("Start Reading")
        reading_status = False

    
    #Main client GUI reading loop that is also used by the server read command
    if reading_status:
        #Read from the connected RFID reader and return the list of tags
        current_tags = list(map(lambda t: t.epc, reader.read())) #Play around with the read rate to get more samples. Or shorten the window/queue
        
        #Create dictionary of EPC's with their confidence intervals to send to server all at once 
        epc_ci_list = {}
        
        #For all scanned tags, mark the item as read 
        for item in current_tags:
            epc_q = client_read(item, 1, False)
            ci_val = client_calc_confidence(epc_q, 1, item)#Calculate the confidence value here 
            epc_ci_list.update({item : ci_val})
        
        #Find the symmetric difference between the current tags read and all tags that the client has ever read 
        #These are the items that need to be marked as a miss by this client
        items_not_read = set(current_tags).symmetric_difference(client_epc_list)

        #For any items not read, add a value of zero. 
        for item in items_not_read:
            epc_q = client_read(item, 0, False)
            ci_val = client_calc_confidence(epc_q, 0, item) #Calculate the confidence value here 
            epc_ci_list.update({item : ci_val})
        
        #Send the list of EPC CI values to the server
        if server_status:
            try:
                #Constructing payload for the server based on the client (Table, Cabinet) by using the first letter of the client name
                msg ="*" +client_id[0] +"CI*"+ str(epc_ci_list) +'\n'
                
                #Send the payload to the server for the client reads
                client_socket.sendto(bytes(msg, encoding="utf-8"), server_address)
            except Exception as e:
                window["-EventLog-"].print(f"Failed to send tag data to the server: {str(e)}\n") 
    
    #Checking if the client is connected to the server
    if server_status:
            #Check if there is anything that was sent from the server
            readable, _, _ = select.select([client_socket], [], [], 0)
            if client_socket in readable:
                try:
                    #Grab the server message
                    server_msg = client_socket.recv(1024).decode('utf-8')    
                    if server_msg:

                        #Creating a regular expression to check for power command and extract value 
                        pattern = r"Power (\d+)"
                        power = re.match(pattern, server_msg)

                        #Handles the recipe epc list sent from the server to initialize the EPC list
                        reader_recipe_update_regex = re.match( r'.*RRU(.*)', server_msg)
                        
                        if power:
                            #Server power command 
                            clientPower(power.group(1))
                        elif server_msg == "Find":
                            #Server find command 
                            clientFind()
                        elif reader_recipe_update_regex:
                            #Initilizing EPCs for clients to create CI values for 
                            initializeEPCS(reader_recipe_update_regex)
                        elif server_msg == "Read":
                            #Checks if reader is connected before changing the reading status
                            if(reader_status == "disconnected"):
                                window["-EventLog-"].print(f"Please connect to reader first!\n")
                                client_socket.sendto(b"Please connect to reader first!\n", server_address)
                                continue
                            reading_status = not reading_status
                    else:
                        print("Invalid message")
                except Exception as e:
                    window["-EventLog-"].print(f"Error while receiving from server: {str(e)}\n")
# Close the window
window.close()