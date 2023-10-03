#!/usr/bin/env python3
from __future__ import print_function
import PySimpleGUI as sg



import time
from datetime import datetime
import mercury


reader = "undefined"
reader_status = "disconnected"
epc_to_update = "None"
item_dictionary = {}
epcs_to_update = []

# Define the GUI layout
layout = [
    [sg.Text("Device URI:"), sg.InputText("tmr:///dev/ttyUSB0", key="connect-reader")],
    [sg.Text("Set Read Power (0-2700):"), sg.InputText(key="reader-power")],
    [sg.Text("EPC to Update:"), sg.Combo(epcs_to_update,default_value = epc_to_update, key="epc",size=(25,1), enable_events=True)],
    [sg.Text("New Item Name:"), sg.InputText(key="item-name")],
    [sg.Button("Connect"), sg.Button("Set Power"), sg.Button("Find Item"), sg.Button("Update Item")],
    [sg.Multiline("", size=(50, 10), key="-EventLog-", disabled=True)]
]

# Create the window
window = sg.Window("Smart Kitchen Application", layout, finalize=True)


# Event loop
while True:
    event, values = window.read()
    

    
    if event == sg.WINDOW_CLOSED:
        break
    elif event == "Connect":
        #Connect to reader using usb 
        reader_port = values["connect-reader"]
        try:
            reader = mercury.Reader(reader_port, baudrate=115200)
        except:
            reader_status = "disconnected"
            window["-EventLog-"].print(f"Falied to connect to Reader! Please check device URI!\n")
            continue
        
        
        #Printing reader model and region to console
        window["-EventLog-"].print(f"Reader Connected: Model {reader.get_model()}\n")
        window["-EventLog-"].print(f"Supported Regions: {reader.get_supported_regions()}\n")
        
        #Set the reader region and default power
        reader.set_region("NA2")
        reader.set_read_plan([1], "GEN2", read_power=1900)
        reader_status = "connected"
    elif event == "Set Power":
        #Grabbing power value from input box
        #Could add some logic to make sure input values are correct but will save for later if have time...
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
            reader.set_read_plan([1], "GEN2", read_power=1000)
            epcs = map(lambda tag: tag.epc, reader.read())
            window["-EventLog-"].print(f"Found Items: {list(epcs)}!\n")
            if len(list(epcs)) > 0:
                epcs_to_update = list(epcs)
                values["epc"].update(value=epc_to_update[0], values= epcs_to_update)
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
        item_dictionary.update(values["epc"], values["item-name"])
        window["-EventLog-"].print(f"Item Updated! Items in inventory: {item_dictionary}\n")

# Close the window
window.close()
