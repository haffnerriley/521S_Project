# 521S Kitchen Object Detection Project

Created by: Eric Biernacki, Riley Haffner, Tyler Martin

This project utilizes RFID and Computer Vision to facilitate cooking recipes. For installation instructions and required packages, refer to the [Install file](Install.md). Additionally, detailed instructions for running the program can be found in the [How-to-Run file](HOW-TO-RUN.md).

## Project Components

### Main Launcher Program
This serves as the primary file initiating the program and all the components of it.

### CV-Runner
Responsible for managing Computer Vision and is invoked by the main launcher file.

### Entry
Primarily used for Object Entry into the program. While the server GUI handles object entry, this program was utilized during prototyping.

### Helpers
A collection of helper functions aiding in Computer Vision training.

### Model
Houses the model utilized for our Computer Vision.

### Voice-Buffer
Manages all speech functionality within the program.

### YOLO-Training
Contains the training program for the YOLO model.

### Client
A client program designed for a Raspberry Pi connected to the Sparkfun Thingmagic RFID reader. This file incorporates a GUI enabling user interaction and allowing the user to connect to the reader, configure reader power, locate objects, update item names, and connect to the server.

### Server
The server program allows users to connect multiple client readers as required. It permits users to configure reader power remotely, locate items, update items, add items to the kitchen for storage, designate specific items tracked in a recipe, remove recipe items, initiate/terminate client reading, provide speech output to aid cooking, connect to the computer vision program, and display a live camera feed utilized for the CV.

### Table Reader
The table_reader program served as our initial demo, showcasing the rudimentary GUI that laid the foundation for the rest of the program. This program demonstrates the essential components needed for item detection, reader connectivity, and GUI management.

---
Feel free to explore each component for more detailed insights into their functionalities and usage.
