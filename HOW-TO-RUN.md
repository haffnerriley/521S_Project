# How to Run

## Materials Needed
- 2x ThingMagic RFID Readers
- 2x Raspberry Pi 4B's
- 2x USB Serial Cables
- 2x External Antennas (Optional)
- 1x USB Camera
- UHF RFID Tags

## Client Setup
1. **Optional: Connect External Antennas:**
   - If using antennas, connect the coax cables to the RFID Readers.
2. **Connect RFID Readers to Raspberry Pis:**
   - Serially connect the RFID Readers to the Raspberry Pis.



3. **Power On:**
   - Plug in the external power supply.

4. **Boot Up Raspberry Pis:**
   - Power on the Raspberry Pis.

5. **Run Client Program:**
   - Execute `client.py` using Python 3.
   - Wait for the program to load into the GUI.

6. **Connect to Readers:**
   - On each GUI, click "Connect to Reader." and wait for response.
   - Input the desired read power and click "Set Power" to confirm connection to the readers.

## CV Setup
- Attach and connect a USB camera with a 45-degree angle to the surface you are trying to observe.

## Server Setup
1. **Run MainLauncher.py:**
   - On a Raspberry Pi or another computer, execute `MainLauncher.py` using Python 3.

2. **Wait for GUI Loading:**
   - Allow the program to load into the GUI. This could take a while as the program has to start the voice buffer and CV program.

**Note:** Ensure all connections are secure and follow the optional steps only if external antennas are being used.


## Client-Server Connection and Starting to Read
- Once both the clients' GUIs and the Server GUI have appeared, click the "Start Server" button on the Server GUI.
- Once the server has started, the server IP and port will be displayed on the Server Program output.
- Connect both clients by entering the Server IP, port, and the name of the reader(Table, Cabinet, etc), then click the "Connect to Server" button on both servers.

## Entering Items
- Place a single item on the cooking area.
- On the server GUI, input the name of the object in the "New Item Name" box.
- Click the "Find Item" button and follow the voice prompts.
- Repeat this process for each item you want to track in the kitchen.

## Adding Items to the Recipe
- Once items are entered, select the required items for the recipe from the "Items in Kitchen" dropdown.
- Click the "Add Item" button for each item in the recipe.
- Check the "Items in Recipe" dropdown to ensure all items were added.
- If an item was added by mistake, select it and click "Remove Item."

## Reading
- Once the items are added to the kitchen and the desired items are added to the recipe, click "Start Reading."
- The program will monitor the locations of the objects and repeatedly announce the number of distractors and required items.
- Ensure the volume is up on the server device.
- Once all the required items are found with 0 distractors, the program will announce a unique message alerting you.
