import serial
from serial.tools import list_ports
from optparse import OptionParser
import time

def run_AT_command(command):
    ser.write(command)
    out = ser.readlines()
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
    
def list_serial_ports():
    return [port[0] for port in list_ports.comports()]

def open_port(dev,baudrate):
    ser = serial.Serial(dev, 19200, timeout=7, parity=serial.PARITY_NONE)
    return ser
    
def main():
    
    global ser
    parser = OptionParser()
    parser.add_option("-d", "--dev", dest="dev", action="store", help="tty dev(ex. '/dev/ttyUSB0'", metavar="DEV")
    (options, args) = parser.parse_args()
    
    try:
        ser = open_port(options.dev,19200)
    except:
        print "Could not open serial port.  Exiting."
        print "FYI - Here's a list of ports on your system."
        print list_serial_ports()
        sys.exit()
    
    # Check if there is a signal
    #bars = signal_strength()
    if bars >= 0:
	print "The RockBLOCK currently has "+str(bars)+" bar(s)!"
	print "Clearing the MO and MT buffers..."
    	response = clear_buffer(2)
        if response == 0:
	    print "Buffers cleared.  Writing message to MO buffer..."
	    response = write_buffer("HelloWorld!")
	    if response == 'OK':
		print "Message written to buffer, initiating SBD session with Iridium..."
		#response = initiate_SBD() WARNING - THIS CALL WILL COST CREDITS
	    else:
	        print "Message failed to write to buffer."
	else:
	    print "Buffer failed to clear."
    else:
	print "The RockBLOCK has no signal."
                
if __name__ == '__main__':
    main()