#!/usr/bin/env python3
from __future__ import print_function
import PySimpleGUI as sg
import socket
import time
from datetime import datetime
import mercury
import select
import re
import pickle
reader = "undefined"
reader_status = "disconnected"
reader_power = 1000
epc_to_update = "None"
item_dictionary = {}
epcs_to_update = []
prev_read = []
reading_status = False
client_socket = None
server_status = False
server_address = "undefined"
client_msg = None
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


def clientPower(power_level):
    global reader_power
    global reader
    global window
    
    reader_power = int(power_level)

    if(reader_status == "disconnected"):
        window["-EventLog-"].print(f"Please connect to reader first!\n")
        return
    try:
        #Set the reader power, protocol, and number of antennas
        reader.set_read_plan([1], "GEN2", read_power=int(power_level))
    except:
        window["-EventLog-"].print(f"Failed to set reader power!\n")
        return
    window["-EventLog-"].print(f"Reader power set to {reader_power}\n")

def clientFind():
    global reader_power
    global reader
    global window
    global client_socket
    global server_address

    if(reader_status == "disconnected"):
        window["-EventLog-"].print(f"Please connect to reader first!\n")
        return
    
    try:
        reader.set_read_plan([1], "GEN2", read_power=reader_power)
        epcs = map(lambda tag: tag.epc, reader.read())
        epc_list = list(epcs)
        if len(epc_list) > 0:
            epc_to_update_server = epc_list[0].decode("utf-8")
        
        window["-EventLog-"].print(f"Server Found Items: {epc_list}\n")
        print(epc_to_update_server)
        client_socket.sendto(bytes(epc_to_update_server, encoding="utf-8"), server_address)
        client_socket.sendto(b'Table Reader Find', server_address)
       
        print("Fart")
        return
    except:
        window["-EventLog-"].print(f"Failed to start reading!\n")
        client_socket.sendto(b'Failed to start reading!', server_address)
        return



# Event loop
while True:
    event, values = window.read(timeout=500)
    

    

    if event == sg.WINDOW_CLOSED:
        break
    elif event == "Connect to Reader":
        #Connect to reader using usb 
        reader_port = values["connect-reader"]
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
    elif event == "server-btn" and server_status == False:
        try:
            # Connect to the server (change the server address and port as needed)
            server_address = (str(values["server-addr"]), int(values["server-port"]))
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.connect(server_address)
            server_status = True
            window[event].update("Disconnect from Server")

            client_msg = bytes(values['client-id'] + ' Reader Connected', encoding='utf-8')
            if(client_msg == None):
                window["-EventLog-"].print(f"Please provide a client identifier like Table or Cabinet\n")
            else:
                client_socket.sendto(client_msg, server_address)
            window["-EventLog-"].print(f"Connected to the server:\n")
        except Exception as e:
            window["-EventLog-"].print(f"Failed to connect to the server: {str(e)}\n")
    elif event == "server-btn" and server_status:
        try:
            client_socket.close()
            server_status = False
            window[event].update("Connect to Server")
            window["-EventLog-"].print(f"Disconnected from the server:\n")
        except Exception as e:
            window["-EventLog-"].print(f"Failed to connect to the server: {str(e)}\n")    
    elif event == "Set Power":
        #Grabbing power value from input box
        #Could add some logic to make sure input values are correct but will save for later if have time...
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue
        if values["reader-power"] == "":
            window["-EventLog-"].print(f"Please type in a power value between 0 and 2700!\n")
            continue
        reader_power = int(values["reader-power"])
        try:
            #Set the reader power, protocol, and number of antennas
            reader.set_read_plan([1], "GEN2", read_power=reader_power)
        except:
            window["-EventLog-"].print(f"Failed to set reader power!\n")
            continue
        window["-EventLog-"].print(f"Reader power set to {reader_power} \n")
    elif event == "Find Item":
        if(reader_status == "disconnected"):
            window["-EventLog-"].print(f"Please connect to reader first!\n")
            continue

        try:
            reader.set_read_plan([1], "GEN2", read_power=reader_power)
            epcs = map(lambda tag: tag.epc, reader.read())
            epc_list = list(epcs)
            window["-EventLog-"].print(f"Found Items: {epc_list}\n")
            if len(epc_list) > 0:
                epc_to_update = epc_list[0].decode("utf-8")
                window["epc"].update(value=str(epc_to_update), values=epc_list)
                selected_item = item_dictionary.get(epc_to_update)
                
                if(selected_item != None):
                    epc_to_update = selected_item
                window["-EventLog-"].print(f"Selecting item: {epc_to_update}\n")
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
    elif event == "read-btn" and reading_status == False:
        window[event].update("Stop Reading")
        reading_status = True
    elif event == "read-btn" and reading_status:
        window[event].update("Start Reading")
        reading_status = False

    

    if reading_status:
        #make a read
        current_tags = list(map(lambda t: t.epc, reader.read()))
    
        #combine
        all_tags = current_tags + prev_read
        #remove duplicates
        all_tags = list(set(all_tags))

        
        for tag in all_tags:
            if tag in prev_read and tag in current_tags:
                if tag.decode("utf-8") in item_dictionary:
                    window["-EventLog-"].print(item_dictionary[tag.decode("utf-8")] + " stayed in field\n")
                    if server_status:
                        try:
                            msg = item_dictionary[tag.decode("utf-8")] + " stayed in field\n"
                            client_socket.sendto(msg, server_address)
                        except Exception as e:
                            window["-EventLog-"].print(f"Failed to send tag data to the server: {str(e)}\n") 
                else:
                    window["-EventLog-"].print(str(tag) + " stayed in field\n")
                 
            elif tag in prev_read and tag not in current_tags:
                window["-EventLog-"].print(str(tag) + " has left field\n")
                #send to server here             
            elif tag in current_tags and tag not in prev_read:
                window["-EventLog-"].print(str(tag) + " has entered field\n")
                #send to server here
            
                
        
        prev_read = current_tags[:]
    
        #time.sleep(1)

    
    if server_status:
            readable, _, _ = select.select([client_socket], [], [], 0)
            if client_socket in readable:
                try:
                    server_msg = client_socket.recv(1024).decode('utf-8')    
                    if server_msg:
                        pattern = r"Power (\d+)"
                        power = re.match(pattern, server_msg)
                        if power:
                            clientPower(power.group(1))
                        elif server_msg == "Find":
                            clientFind()
                    else:
                        print("Invalid message")
                        # Handle the server's message as needed
                except Exception as e:
                    window["-EventLog-"].print(f"Error while receiving from server: {str(e)}\n")
# Close the window
window.close()
