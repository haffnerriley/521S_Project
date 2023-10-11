#!/usr/bin/env python3
from __future__ import print_function
import PySimpleGUI as sg
import time
from datetime import datetime
import mercury
import socket
import threading
import requests
from netifaces import interfaces, ifaddresses, AF_INET
import re

#Get the IP address of the computer that the server is running on
ipaddr = None
for ifaceName in interfaces():
    addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
    
    #Using wireless by default for the raspberry pi but this can be changed to use a different interface
    if ifaceName == 'wlan0':
        ipaddr = addresses[0]


# Configure the server address and port
server_address = (ipaddr, 12345)

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

#Dictionary of items that the server maintains 
item_dictionary = {}

#List of EPCS that the server found using the Find button
epcs_to_update = []

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

# Define the GUI layout
layout = [
    [sg.Text("Set Read Power (0-2700):"), sg.InputText(key="reader-power"), sg.Combo(connected_readers, default_value=selected_reader, key="cur-reader",size=(25,1), enable_events=True)],
    [sg.Text("EPC to Update:"), sg.Combo(epcs_to_update, default_value=epc_to_update, key="epc",size=(25,1), enable_events=True)],
    [sg.Text("New Item Name:"), sg.InputText(key="item-name")],
    [sg.Button("Set Power"), sg.Button("Find Item"), sg.Button("Update Item"), sg.Button("Start Server", key="server-btn"), sg.Button("Start Reading", key="server-read")],
    [sg.Multiline("", size=(50, 10), key="-EventLog-", disabled=True)]
]

# Create the window
window = sg.Window("Smart Kitchen Server Application", layout, resizable=True, finalize=True)




# Event loop
while True:
    event, values = window.read(timeout=500)
    
    if event == sg.WINDOW_CLOSED:
        break
    
    elif event == "Set Power":
        #Grabbing power value from input box
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        if values["reader-power"] == "":
            window["-EventLog-"].print(f"Please type in a power value between 0 and 2700!\n")
            continue
        reader_power = int(values["reader-power"])
        try:
            #Grab the current client reader selected in the dropdown
            client_socket = values["cur-reader"]
            
            for ip in client_socket:
                client_selected= client_socket[ip] 
            
            client_power = "Power " + str(reader_power)
            server_socket.sendto(client_power.encode('utf-8'), client_selected)
        except:
            window["-EventLog-"].print(f"Failed to set reader power!\n")
            continue
        
        window["-EventLog-"].print(f"Reader power set to {reader_power}\n")
    elif event == "Find Item":
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue

        try:
            client_socket = values["cur-reader"]
            for ip in client_socket:
                client_selected= client_socket[ip]  
            server_socket.sendto(b'Find', client_selected)
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
    elif event == "Update Item":
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        if(values["epc"] == "None"):
            window["-EventLog-"].print(f"Please click Find Item button and pick an EPC to update! \n")
            continue
        if(values["item-name"] == ""):
            window["-EventLog-"].print(f"Please input a new Item name!\n")
            continue
        item_dictionary.update({values["epc"] : values["item-name"]})
        window["-EventLog-"].print(f"Item Updated! Items in inventory: {item_dictionary}\n")
    elif event == "server-btn" and server_status == False:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(server_address)
        server_socket.settimeout(0.5)
        server_status = True
        window["-EventLog-"].print(f"RFID Server listening on {server_address}")
        window[event].update("Stop Server")
    elif event == "server-btn" and server_status:
        window[event].update("Start Server")
        server_socket.close()
        server_status = False
    elif event == "server-read" and server_read_status == False:
        if len(connected_readers) == 0:
            window["-EventLog-"].print(f"Please connect clients first!\n")
            continue
        try:
            client_socket = values["cur-reader"]
            for client_addr in client_addrs:
                
                client_selected= client_addr
                server_socket.sendto(b'Read', client_selected)
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
        server_read_status = True
        window[event].update("Stop Reading")
    elif event == "server-read" and server_read_status:
        if len(connected_readers) == 0:
            window["-EventLog-"].print(f"Please connect clients first!\n")
            continue
        
        try:
            client_socket = values["cur-reader"]
            for client_addr in client_addrs:
                client_selected= client_addr
                server_socket.sendto(b'Read', client_selected)
        except:
            window["-EventLog-"].print(f"Failed to stop reading!\n")
            continue
        window[event].update("Start Reading")
        server_read_status = False
    

    if server_status:
        try:
            data, client_address = server_socket.recvfrom(1024)
            #Logic for handling connections for the RFID reader clients
            table_find_regex = re.match(r'.*TRF(.*)', data.decode('utf-8')) #TRF denotes a Table Reader Find packet
            table_read_regex = re.match(r'.*TRR(.*)', data.decode('utf-8')) #TRR denotes a Table Reader Read packet
            if(table_find_regex):
                
                
                data_find = table_find_regex.group(1)
                split_pattern = re.compile(r'.{1,24}')

                epc_list = split_pattern.findall(data_find)
                window["-EventLog-"].print(f"Found Items: {epc_list}\n")
                if len(epc_list) > 0:
                    epc_to_update = epc_list[0]
                    window["epc"].update(value=str(epc_to_update), values=epc_list)
                    selected_item = item_dictionary.get(epc_to_update)
                    
                    if(selected_item != None):
                        epc_to_update = selected_item
                    window["-EventLog-"].print(f"Selecting item: {epc_to_update}\n")
            elif(table_read_regex):
                
                #data, client_address = server_socket.recvfrom(1024)
                data_read = table_read_regex.group(1)
                epc_read = re.compile(r'^(.{24})')
                
                # Use re.match to find the match at the beginning of the string
                extracted_epc = re.match(epc_read, data_read)

                if extracted_epc:
                    # Extract the first 24 bytes
                    extracted_epc = extracted_epc.group(1)
                    
                    # The rest of the string after the first 24 bytes
                    rest_of_string = data_read[len(extracted_epc):]
                    item_read = item_dictionary.get(extracted_epc)
                    if(item_read != None):
                        window["-EventLog-"].print(f"{item_read}{rest_of_string}\n")
                    else:
                        window["-EventLog-"].print(f"{data_read}\n")
                else:
                    window["-EventLog-"].print(f"{data_read}\n")
            elif data.decode('utf-8') == "Table Reader Connected":
                window["-EventLog-"].print(f"Connected to Table Reader @ {client_address}")
                reader_info = {"table-reader" : client_address}
                client_addrs.append(client_address)
                connected_readers.append(reader_info)    
                window["cur-reader"].update(value=str(reader_info), values=connected_readers)
                reader_status = True
            elif data.decode('utf-8') == "Cabinet Reader Connected":
                window["-EventLog-"].print(f"Connected to Cabinet Reader @ {client_address}")
                reader_info = {"cabinet-reader" : client_address}
                connected_readers.append({"cabinet-reader" : client_address})
                client_addrs.append(client_address)
                window["cur-reader"].update(value=str(reader_info), values=connected_readers)
                reader_status = True
            elif data.decode('utf-8') == "Client Disconnected":
                client_addrs.remove(client_address)
                for client in connected_readers:
                    connected_readers.remove(client)
                window["cur-reader"].update(values=connected_readers)
            else:
                window["-EventLog-"].print(f"Client says: {data.decode('utf-8')}") 
        except:
            continue

        

    

# Close the window
window.close()
