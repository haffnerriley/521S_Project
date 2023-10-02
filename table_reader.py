
from __future__ import print_function
import PySimpleGUI as sg

#!/usr/bin/env python3

import time
from datetime import datetime
import mercury



# Define the GUI layout
layout = [
    [sg.Text("Reader Path:"), sg.InputText( key="connect-reader")],
    [sg.Text("Set Read Power (0-2700):"), sg.InputText(key="reader-power")]
    [sg.Text("EPC to Update:"), sg.InputText(key="epc")],
    [sg.Text("New Item Name":), sg.InputText(key="item-name")],
    [sg.Button("Connect"), sg.Button("Set Power"), sg.Button("Find EPC"), sg.Button("Update Item")],
    [sg.Multiline("", size=(40, 10), key="-EventLog-", disabled=True)]
]

# Create the window
window = sg.Window("Smart Kitchen Application", layout, finalize=True)

reader = "undefined"

# Event loop
while True:
    event, values = window.read()
    

    
    if event == sg.WINDOW_CLOSED:
        break
    elif event == "Connect":
        #Connect to reader using usb 
        reader_port = values["connect-reader"]
        reader = mercury.Reader(reader_port, baudrate=115200)

        #Printing reader model and region to console
        window["-EventLog-"].print(f"Reader Connected: Model {reader.get_model()}\n")
        window["-EventLog-"].print(f"Supported Regions: {reader.get_supported_regions()}\n")
        
        #Set the reader region
        reader.set_region("NA2")
        reader.set_read_plan([1], "GEN2", read_power=1900)
    elif event == "Set Power":
        reader_power = values["reader-power"]
        reader.set_read_plan([1], "GEN2", read_power=reader_power)
        window["-EventLog-"].print(f"Button 2 clicked. Input 2 value: {input2_value}\n")
    elif event == "button 1":
        input1_value = values["epc-write-id"] 
        reader.read()
        window["-EventLog-"].print(f"Button 1 clicked. Input 1 value: {input1_value}\n")

# Close the window
window.close()
