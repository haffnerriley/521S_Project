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


ipaddr = None
for ifaceName in interfaces():
    addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
    if ifaceName == 'wlan0':
        ipaddr = addresses[0]


# Configure the server address and port
server_address = (ipaddr, 12345)

# Create a socket and bind it to the server address
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(server_address)
#server_socket.listen(1)
server_socket.settimeout(0.5)
reader = "undefined"
reader_status = "disconnected"
reader_power = 1000
epc_to_update = "None"
item_dictionary = {}
epcs_to_update = []
prev_read = []
connected_readers = []
selected_reader = "None"
server_status = False

# Define the GUI layout
layout = [
    [sg.Text("Set Read Power (0-2700):"), sg.InputText(key="reader-power"), sg.Combo(connected_readers, default_value=selected_reader, key="cur-reader",size=(25,1), enable_events=True)],
    [sg.Text("EPC to Update:"), sg.Combo(epcs_to_update, default_value=epc_to_update, key="epc",size=(25,1), enable_events=True)],
    [sg.Text("New Item Name:"), sg.InputText(key="item-name")],
    [sg.Button("Set Power"), sg.Button("Find Item"), sg.Button("Update Item"), sg.Button("Start Server", key="server-btn")],
    [sg.Multiline("", size=(50, 10), key="-EventLog-", disabled=True)]
]

# Create the window
window = sg.Window("Smart Kitchen Server Application", layout, resizable=True, finalize=True)


window["-EventLog-"].print(f"RFID Server listening on {server_address}")

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
        reader_power = int(values["reader-power"])
        try:
            #Set the reader power, protocol, and number of antennas
            reader.set_read_plan([1], "GEN2", read_power=reader_power)
        except:
            window["-EventLog-"].print(f"Failed to set reader power!\n")
            continue
        
        window["-EventLog-"].print(f"Reader power set to {reader_power}\n")
    elif event == "Find Item":
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue

        try:
            reader.set_read_plan([1], "GEN2", read_power=reader_power)
            epcs = map(lambda tag: tag.epc, reader.read())
            epc_list = list(epcs)
            window["-EventLog-"].print(f"Found Items: {epc_list}!\n")
            if len(epc_list) > 0:
                epc_to_update = epc_list[0].decode("utf-8")
                window["epc"].update(value=str(epc_to_update), values=epc_list)
                selected_item = item_dictionary.get(epc_to_update)
                
                if(selected_item != None):
                    epc_to_update = selected_item
                window["-EventLog-"].print(f"Selecting item: {epc_to_update}!\n")
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
        item_dictionary.update({values["epc"].decode("utf-8") : values["item-name"]})
        window["-EventLog-"].print(f"Item Updated! Items in inventory: {item_dictionary}\n")
    elif event == "server-btn" and server_status == False:
        window[event].update("Stop Server")
        server_status = True
    elif event == "server-btn" and server_status:
        window[event].update("Start Server")
        server_status = False

    

    if server_status:
        try:
            data, client_address = server_socket.recvfrom(1024)
            
            if data.decode('utf-8') == "Table Reader Readings":
                print("Here")
                data, client_address = server_socket.recvfrom(1024)
                if data.decode('utf-8') == "Table Reader Readings":
                    print("farts")
            else:
                print("taod")
            #Logic for handling connections for the RFID reader clients
            if data.decode('utf-8') == "Table Reader Connected":
                window["-EventLog-"].print(f"Connected to Table Reader @ {client_address}")
                connected_readers.append({"table-reader" : client_address})
                reader_status = True
            elif data.decode('utf-8') == "Cabinet Reader Connected":
                window["-EventLog-"].print(f"Connected to Cabinet Reader @ {client_address}")
                connected_readers.append({"cabinet-reader" : client_address})
                reader_status = True
            
        except:
            continue

        

    

# Close the window
window.close()
