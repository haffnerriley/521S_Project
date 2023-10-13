#!/usr/bin/env python3
from __future__ import print_function
import PySimpleGUI as sg
import socket
import time
from datetime import datetime
import mercury
import select
import re
import json

#RFID reader object
reader = "undefined"

#RFID Reader connection Status
reader_status = "disconnected"

#RFID reader power
reader_power = 1000

#Selected EPC to update through the find button 
epc_to_update = "None"

#Dictionary of items that the server maintains 
item_dictionary = {}

#List of EPCS that the server found using the Find button
epcs_to_update = []

#Previous RFID reads 
prev_read = []

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

#Client identifier (Table, Cabinet)
client_id = None


# Define the GUI layout
layout = [
    [sg.Text("Server IP Address:"), sg.InputText("192.168.1.11", key="server-addr"),sg.Text("Server Port: "), sg.InputText("12345", key="server-port"), sg.Text("Client ID(Table, Cabinet...):"), sg.InputText("Table", key="client-id")],
    [sg.Text("Device URI:"), sg.InputText("tmr:///dev/ttyUSB0", key="connect-reader")],
    [sg.Text("Set Read Power (0-2700):"), sg.InputText(key="reader-power")],
    [sg.Text("EPC to Update:"), sg.Combo(epcs_to_update, default_value=epc_to_update, key="epc",size=(25,1), enable_events=True)],
    [sg.Text("New Item Name:"), sg.InputText(key="item-name")],
    [[sg.Button("Connect to Server", key="server-btn"), sg.Button("Connect to Reader"), sg.Button("Set Power"), sg.Button("Find Item"), sg.Button("Update Item"), sg.Button("Start Reading", key="read-btn")]],
    [sg.Multiline("", size=(50, 10), key="-EventLog-", disabled=True)]
]

# Create the window
window = sg.Window("Smart Kitchen Client Application", layout,resizable=True, finalize=True)

#Helper function to check if valid IP address.
def is_valid_ip(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

#Helper function to check if valid port number
def is_valid_port(port):
    try:
        port = int(port)
        return 0 < port <= 65535
    except ValueError:
        return False


#Function to handle power commands from server
def clientPower(power_level):
    global reader_power
    global reader
    global window
    
    #Grab the power sent from the server 
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

#Function to handle server find commands 
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
        
        #Grab the epcs from the reader response 
        epcs = map(lambda tag: tag.epc, reader.read())
        
        #Create a list of EPCS
        epc_list = list(epcs)

        #Initialize an empty list of EPCs to send to the server 
        epc_list_for_server = []

        #Eventually, try to send this as a json object and decode the bytes or something...
        if(client_id == "Table"):
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



# Event loop to handle GUI Client/Server Communication
while True:
    
    #Can change the timeout if we want to have a faster UI
    event, values = window.read(timeout=500)

    #Close the client socket if exit button pressed and client socket still open
    if event == sg.WINDOW_CLOSED:
        if server_status:
            client_socket.close()
        break
    #Handles the connection of the RFID reader
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
    #Handles connecting to the server
    elif event == "server-btn" and server_status == False:
        
        try:
            # Connect to the server using given address and port
            server_address_input = str(values["server-addr"])
            server_port_input = str(values["server-port"])
            
            #Check that user input contains valid IP address and port number
            if is_valid_ip(server_address_input) and is_valid_port(server_port_input):
                server_address = (server_address_input, int(server_port_input))
            else:
                window["-EventLog-"].print(f"Please provide a valid Server IP and Port\n")
                continue

            #Create a client socket and connect to ther server address 
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
        
        #Check that the RFID reader is connected
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        #Check that power input is not empty
        if values["reader-power"] == "":
            window["-EventLog-"].print(f"Please type in a power value between 0 and 2700!\n")
            continue
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
    #Handles finding items from the client GUI
    elif event == "Find Item":
        
        #Check if the reader is connected
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
        
        #Check that the reader is connected
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
        #make a read
        current_tags = list(map(lambda t: t.epc, reader.read()))
    
        #combine
        all_tags = current_tags + prev_read
        
        #remove duplicates
        all_tags = list(set(all_tags))

        
        for tag in all_tags:
            #Handles logic for tags that are staying in the field
            if tag in prev_read and tag in current_tags:
                if server_status:
                    try:
                        #Constructing payload for the server based on the client (Table, Cabinet)
                        msg ="*" +client_id[0] +"RR"+ tag.decode("utf-8") + " stayed in field\n"
                        
                        #Send the payload to the server for the client reads
                        client_socket.sendto(bytes(msg, encoding="utf-8"), server_address)
                    except Exception as e:
                        window["-EventLog-"].print(f"Failed to send tag data to the server: {str(e)}\n") 
            #Handles logic for tags that have left the field
            elif tag in prev_read and tag not in current_tags:
                window["-EventLog-"].print(str(tag) + " has left field\n")
                if server_status:
                    try:
                        #Constructing payload for the server based on the client (Table, Cabinet)
                        msg ="*" +client_id[0] +"RR"+ tag.decode("utf-8") + " has left field\n"
                        
                        #Send the payload to the server for the client reads
                        client_socket.sendto(bytes(msg, encoding="utf-8"), server_address)
                    except Exception as e:
                        window["-EventLog-"].print(f"Failed to send tag data to the server: {str(e)}\n") 
            #Handles logic for tags that have entered the field         
            elif tag in current_tags and tag not in prev_read:
                window["-EventLog-"].print(str(tag) + " has entered field\n")
                if server_status:
                    try:
                        #Constructing payload for the server based on the client (Table, Cabinet)
                        msg ="*" +client_id[0] +"RR"+ tag.decode("utf-8") + " has entered field\n"
                        
                        #Send the payload to the server for the client reads
                        client_socket.sendto(bytes(msg, encoding="utf-8"), server_address)
                    except Exception as e:
                        window["-EventLog-"].print(f"Failed to send tag data to the server: {str(e)}\n") 

        prev_read = current_tags[:]


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

                        if power:
                            #Server power command 
                            clientPower(power.group(1))
                        elif server_msg == "Find":
                            #Server find command 
                            clientFind()
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
