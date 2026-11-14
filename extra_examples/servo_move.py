#!/usr/bin/env python
#
#This code moves your arm based on angle inputs in the terminal, adhere to the limits of the arm.
#The code stores position, velocity and acceleration data for each servo in a CSV file.

import sys
import os
import time
import csv

if os.name == 'nt':
    import msvcrt
    def getch():
        return msvcrt.getch().decode()
else:
    import sys, tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

sys.path.append("..")
from scservo_sdk import *                   # Uses SC Servo SDK library

# Control table address

# Default setting
BAUDRATE                    = 1000000           # SC Servo default baudrate : 1000000
DEVICENAME                  = 'COM11'    # Check which port is being used on your controller
                                                # ex) Windows: "COM1"   Linux: "/dev/ttyUSB0" Mac: "/dev/tty.usbserial-*"

SCS_MINIMUM_POSITION_VALUE  = 0             # SC Servo will rotate between this value
SCS_MAXIMUM_POSITION_VALUE  = 4095              
SCS_MOVING_SPEED            = 500          # SC Servo moving speed
SCS_MOVING_ACC              = 50            # SC Servo moving acc


scs_goal_position = [2048, 2048, 2048]         # Goal position

# Initialize PortHandler instance
# Set the port path
# Get methods and members of PortHandlerLinux or PortHandlerWindows
portHandler = PortHandler(DEVICENAME)

# Initialize PacketHandler instance
# Get methods and members of Protocol
packetHandler = sms_sts(portHandler)

# Open port
if portHandler.openPort():
    print("Succeeded to open the port")
else:
    print("Failed to open the port")
    print("Press any key to terminate...")
    getch()
    quit()


# Set port baudrate
if portHandler.setBaudRate(BAUDRATE):
    print("Succeeded to change the baudrate")
else:
    print("Failed to change the baudrate")
    print("Press any key to terminate...")
    getch()
    quit()

groupSyncRead = GroupSyncRead(packetHandler, SMS_STS_PRESENT_POSITION_L, 11) #reads the relevant bytes for the read data

#creating the csv file
os.makedirs("logs", exist_ok=True)
log_name = os.path.join("logs", "servo_log_%s.csv" % time.strftime("%Y%m%d_%H%M%S")) #creates new log file each run
log_file = open(log_name, "w", newline="")
log_writer = csv.writer(log_file)
log_writer.writerow(["time_ms", "servo_id", "goal_position", "position", "speed", "load"])
t0 = time.perf_counter()
print("Logging to", log_name)

while 1:
    print("Press any key to continue! (or press ESC to quit!)")
    if getch() == chr(0x1b):
        break

    for scs_id in range(1, 4):
        
        scs_goal_position[scs_id-1] = int(int(input("Enter the target position for servo no.%d (in degrees): " %scs_id))*4096/360)
        scs_addparam_result = packetHandler.SyncWritePosEx(scs_id, scs_goal_position[scs_id-1], SCS_MOVING_SPEED, SCS_MOVING_ACC)
        if scs_addparam_result != True:
            print("[ID:%03d] groupSyncWrite addparam failed" % scs_id)

    # Syncwrite goal position
    scs_comm_result = packetHandler.groupSyncWrite.txPacket()
    if scs_comm_result != COMM_SUCCESS:
        print("%s" % packetHandler.getTxRxResult(scs_comm_result))

    # Clear syncwrite parameter storage
    packetHandler.groupSyncWrite.clearParam()
    time.sleep(0.002) #wait for servo status moving=1
    while 1:
        # Add parameter storage for SC Servo#1~10 present position value
        for scs_id in range(1, 5):
            scs_addparam_result = groupSyncRead.addParam(scs_id)
            if scs_addparam_result != True:
                print("[ID:%03d] groupSyncRead addparam failed" % scs_id)

        scs_comm_result = groupSyncRead.txRxPacket()
        if scs_comm_result != COMM_SUCCESS:
            print("%s" % packetHandler.getTxRxResult(scs_comm_result))

        scs_last_moving = 0;
        for scs_id in range(1, 5):
            # Check if groupsyncread data of SC Servo#1~10 is available
            scs_data_result, scs_error = groupSyncRead.isAvailable(scs_id, SMS_STS_PRESENT_POSITION_L, 11)
            if scs_data_result == True:
                # Get SC Servo#scs_id present position moving value
                t_ms = (time.perf_counter() - t0) * 1000.0
                scs_present_position = groupSyncRead.getData(scs_id, SMS_STS_PRESENT_POSITION_L, 2)
                scs_present_speed = groupSyncRead.getData(scs_id, SMS_STS_PRESENT_SPEED_L, 2)
                scs_present_load = groupSyncRead.getData(scs_id, SMS_STS_PRESENT_LOAD_L, 2)
                scs_present_moving = groupSyncRead.getData(scs_id, SMS_STS_MOVING, 1)
                # print(scs_present_moving)

                log_writer.writerow([f"{t_ms:.2f}", scs_id, scs_goal_position[scs_id-1], scs_present_position, packetHandler.scs_tohost(scs_present_speed, 15), packetHandler.scs_tohost(scs_present_load, 10) / 10.0 ])

                print("[ID:%03d] PresPos:%d PresSpd:%d PresLoad:%d " % (scs_id, scs_present_position, packetHandler.scs_tohost(scs_present_speed, 15), packetHandler.scs_tohost(scs_present_load, 10) / 10.0))
                if scs_present_moving==1:
                    scs_last_moving = 1;
            else:
                print("[ID:%03d] groupSyncRead getdata failed" % scs_id)
                continue
            if scs_error:
                print(packetHandler.getRxPacketError(scs_error))            
        print("---")

        # Clear syncread parameter storage
        groupSyncRead.clearParam()
        if scs_last_moving==0:
            break
    # Change goal position
    '''if index == 0:
        index = 1
    else:
        index = 0'''

# Close port
portHandler.closePort()
