
#!/usr/bin/env python3
from __future__ import print_function
import PySimpleGUI as sg



import time
from datetime import datetime
#import mercury



# Define the GUI layout
layout = [
    [sg.Text("Device URI:"), sg.InputText( key="connect-reader")],
    [sg.Text("Set Read Power (0-2700):"), sg.InputText(key="reader-power")],
    [sg.Text("EPC to Update:"), sg.InputText(key="epc")],
    [sg.Text("New Item Name:"), sg.InputText(key="item-name")],
    [sg.Button("Connect"), sg.Button("Set Power"), sg.Button("Find Item to Update"), sg.Button("Update Item")],
    [sg.Multiline("", size=(40, 10), key="-EventLog-", disabled=True)]
]

# Create the window
window = sg.Window("Smart Kitchen Application", layout, finalize=True)

reader = "undefined"
reader_status = "disconnected"
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
        reader_power = values["reader-power"]
        try:
            #Set the reader power, protocol, and number of antennas
            reader.set_read_plan([1], "GEN2", read_power=reader_power)
        except:
            window["-EventLog-"].print(f"Failed to set reader power!\n")
            continue
        
        window["-EventLog-"].print(f"Reader power set to {reader_power}\n")
    elif event == "Find Item to Update":
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue

        try:
             reader_start_val = reader.read()
             window["-EventLog-"].print(f"Ready to Read! {reader_start_val}\n")
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
        
        try:
            epcs = map(lambda tag: tag.epc, reader.read())
            window["-EventLog-"].print(f"Failed to start reading!\n")
            print(list(epcs))
        except:
            window["-EventLog-"].print(f"Failed to start reading!\n")
            continue
    elif event == "Update Item":


# Close the window
window.close()
