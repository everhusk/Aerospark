#! /usr/bin/python
import serial
import io 
import math
from time import sleep 
import time
import sys
import time as time_
import RPi.GPIO as GPIO
import string 
import random 
import threading
import logging
from subprocess import call

GPIO.setmode(GPIO.BOARD)
GPIO.setup(7, GPIO.OUT)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(13, GPIO.OUT) # Red LED
GPIO.setup(15, GPIO.OUT) #
GPIO.setup(22, GPIO.OUT)

# Time interval for GPS data logging to text file (seconds)
datalog_interval = 5
# Time interval for sending GPS data to Iridium network (seconds)
livetrack_interval = 60
# Altitue in meters at which you wish ignition to occur
capAlt = float(21336) 

# ----------------------- uBlox Flight Mode Setup ------------------------
uBlox = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
gps_set_sucess = False
setNav = bytearray.fromhex("B5 62 06 24 24 00 FF FF 06 03 00 00 00 00 10 27 00 00 05 00 FA 00 FA 00 64 00 2C 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 16 DC")
## Disable all NMEA strings
uBlox.write("$PUBX,40,GLL,0,0,0,0*5C\n");
uBlox.write("$PUBX,40,GGA,0,0,0,0*5A\n");
uBlox.write("$PUBX,40,GSA,0,0,0,0*4E\n");
uBlox.write("$PUBX,40,RMC,0,0,0,0*47\n");
uBlox.write("$PUBX,40,GSV,0,0,0,0*59\n");
uBlox.write("$PUBX,40,VTG,0,0,0,0*5E\n");

#create function equivalent to arduino millis();
def millis():
        return int(round(time_.time() * 1000))

#calcuate expected UBX ACK packet and parse UBX response from GPS
def getUBX_ACK(MSG):
        b = 0
        ackByteID = 0
        ackPacket = [0 for x in range(10)]
        startTime = millis()
        print "Reading ACK response: "
        #construct the expected ACK packet
        ackPacket[0] = int('0xB5', 16) #header
        ackPacket[1] = int('0x62', 16) #header
        ackPacket[2] = int('0x05', 16) #class
        ackPacket[3] = int('0x01', 16) #id
        ackPacket[4] = int('0x02', 16) #length
        ackPacket[5] = int('0x00', 16)
        ackPacket[6] = MSG[2] #ACK class
        ackPacket[7] = MSG[3] #ACK id
        ackPacket[8] = 0 #CK_A
        ackPacket[9] = 0 #CK_B
        #calculate the checksums
        for i in range(2,8):
                ackPacket[8] = ackPacket[8] + ackPacket[i]
                ackPacket[9] = ackPacket[9] + ackPacket[8]
        #print expected packet
        log("Expected ACK Response: ")
        for byt in ackPacket:
        	log(byt)
        print "Waiting for UBX ACK reply:"
        while 1:
                #test for success
                if ackByteID > 9 :
                        #all packets are in order
                        log("(SUCCESS!)")
                        return True
                #timeout if no valid response in 3 secs
                if millis() - startTime > 3000:
                        #print "(FAILED!)"
			log("FAILED!")
                        return False
                #make sure data is availible to read
                if uBlox.inWaiting() > 0:
                        b = uBlox.read(1)
                        #check that bytes arrive in the sequence as per expected ACK packet
                        if ord(b) == ackPacket[ackByteID]:
                                ackByteID += 1
                                #print ord(b)
				log(ord(b))
                        else:
                                ackByteID = 0 #reset and look again, invalid order

def sendUBX(MSG, length):
        log("Sending UBX Command: ")
        ubxcmds = ""
        for i in range(0, length):
                uBlox.write(chr(MSG[i])) #write each byte of ubx cmd to serial port
                ubxcmds = ubxcmds + str(MSG[i]) + " " # build up sent message debug output string
        uBlox.write("\r\n") #send newline to ublox
        log(ubxcmds) #print debug message
        log("UBX Command Sent...")
        
# -------------------- RockBLOCK Iridium Calls ------------------------
Iridium = serial.Serial('dev/ttyUSB0', 19200, timeout=7, parity=serial.PARITY_NONE)
def run_AT_command(command):
    Iridium.write(command)
    out = Iridium.readlines()
    return out

# Gets signal strength (returns 0-5 bars)
def signal_strength():
    response = run_AT_command("AT+CSQ\r")
    if len(response) == 4:
        signal = response[1][5]
    else:
	signal = '0'
    return int(signal)

# Clears the buffer (0 for MO, 1 for MT, 2 for both)
def clear_buffer(type):
    command = "AT+SBDD" + str(type) + "\r"
    response = run_AT_command(command)[1][0]
    return int(response)

# Writes a message to the MO buffer
def write_buffer(text):
    command = "AT+SBDWT=" + text +"\r"
    response = run_AT_command(command)[1][0:2]
    return response

# Sends MO data to GSM, and reads any GSS data queries to MT buffer
def initiate_SBD():
    command = "AT+SBDIX\r"
    response = run_AT_command(command)
    print response

# Reads a message from the MT buffer
def read_buffer():
    command = "AT+SBDRT\r"
    response = run_AT_command(command)
    print response
    
def CallIridium(lat,lon,alt,speed,sats):
    textFile.write("Calling Iridium with "+lat+" "+lon+" , "+speed+"km/h, and "+sats+" sats.")

# ------------------------ Other Functions ----------------------------
def wordGenerator(size=6, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for x in range(size))

def cam():
	try:
		log("starting Camera")
		call (["raspivid -o test2vid.h264 -t 60000 -mm matrix"], shell=True)
		return
	except(TypeError,ValueError) as err:
		log("error %s",err)

def ignition(): 
	for x in range(0,10):
		sleep(1)
		log(str(x) + " seconds")

	GPIO.output(7,True)
	sleep(120)
	GPIO.output(7,False)

# --------------------------- Main Code -------------------------------
def main():
    
    SBDtime = int(datalog_interval/livetrack_interval)
    # Set uBlox to Flight Mode
	while not gps_set_sucess:
		GPIO.output(13, True)
    	sendUBX(setNav, len(setNav))
    	gps_set_sucess = getUBX_ACK(setNav);
        
    # This logging will help keep track on which thread the message is printed out
    logging.basicConfig(level = logging.DEBUG, format = '(%(threadName)-10s) %(message)s')
    #Instantiate the log debug object for easy log type print
    log = logging.debug
    
    with open(wordGenerator()+'.txt', 'w') as textFile:
		textFile.write("Time     Latitude       Longitude     Altitude(m)    Hacc(m)      Vacc(m)     Speed(km/h)     Heading(degrees)     Climb(m/s)     Satellites\n")
		textFile.write("--------------------------------------------------------------------------------------------------------------------------------------------\n")
		count = 0
        while(1):
            
            # Call Iridium if sufficient time has passed
            if count == (SBDtime):
                t1 = threading.Thread(name="CallIridium", target = CallIridium, args=[gps_lat,gps_lon,altitude,speed,sats])
                t1.start()
                count == 0
            
			## Query uBlox
			uBlox.write("$PUBX,00*33\n");
			line = uBlox.readline()   # read a '\n' terminal
			try:
				GPIO.output(11,False)
				# print line
				fields = line.split(",")
		
				if len(fields) < 21:
					log("invalid GPS String. Too small")
					GPIO.output(13,True) # Red LED ON
					sleep(1)
					continue
	
				#GPIO.output(13,False)
				sleep(3)
				GPIO.output(11, True)

				time = int(round(float(fields[2])))
				time_hour=(time/10000);  
				time_minute=((time-(time_hour*10000))/100);  
				time_second=(time-(time_hour*10000)-(time_minute*100));
				MasterTime = str(time_hour) + ":" + str(time_minute) + ":" + str(time_second)
				log(MasterTime)

				lat_minutes=int(math.floor(float(fields[3])/100))
				lat_seconds=float(fields[3])-(lat_minutes*100)	
				gps_lat=lat_minutes+(lat_seconds/60.0)
				if(fields[4]=='S'):
					gps_lat = -gps_lat

				lon_minutes=int(math.floor(float(fields[5])/100))
				lon_seconds=float(fields[5])-(lon_minutes*100)	
				gps_lon=lon_minutes+(lon_seconds/60.0)
				if(fields[6]=='W'):
					gps_lon = -gps_lon

				altitude = float(fields[7]) # m
				fix = fields[8] # "G3" = 3D fix
				hacc = float(fields[9]) # m
				vacc = float(fields[10]) # m
				speed = float(fields[11]) # km/h
				heading = float(fields[12]) # degrees
				climb = -float(fields[13]) # m/s
				sats = int(fields[18])

				log("Latitude: %s", str(gps_lat) )
				log("Longitude %s", str(gps_lon) )
				log("Altitude: %s m", str(altitude) )
				log("Hacc: %s m", str(hacc) )
				log("Vacc: %s m", str(vacc) )
				log("Speed: %s km/h", str(speed) )
				log("Heading: %s degrees", str(heading) )
				log("Climb: %s m/s", str(climb) )
				log("Satellites: %s\n", str(sats) )
		
				longLines = [str(MasterTime) + ",   ",
						str(gps_lat) + ",   ",
						str(gps_lon) +",  ",
						str(altitude),",  ",
						str(hacc) + ",  ",
						str(vacc) + ",  ",
						str(speed) + ",   ",
						str(heading) + ",   ",	
						str(climb) + ",   ",
						str(sats)+"   "+"\n"]
			
				textFile.writelines(longLines)
				textFile.truncate()
		
				if (sats < 4) :
					GPIO.output(13,True) # Red LED ON
				else:
					GPIO.output(13,False) # Red LED OFF
		
				if (altitude > capAlt) and (sats >= 4) and (time_hour > 1) and (time_hour < 6):
					textFile.write("Started Rocket Ignition.  TO DA MOON!!!\n")
					t2 = threading.Thread(name="IgniteR", target = igniteRocket)
                    #t3 = threading.Thread(name="RasPiVid", target = cam)
		   			t2.start()
                    #t3.start()
					GPIO.output(15, True) # Open Relay Circuit
                    sleep(120)
				else:
					GPIO.output(15, False) # Close Relay Circuit

			except (TypeError, ValueError) as err:
				print "Invalid String."
				print str(err)
            
            count = count + 1

if __name__ == '__main__':
    main()