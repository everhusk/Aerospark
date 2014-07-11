import serial
from serial.tools import list_ports
from optparse import OptionParser
import time

def list_serial_ports():
    return [port[0] for port in list_ports.comports()]

def open_port(dev,baudrate):
    ser = serial.Serial(dev, 19200, timeout=0, parity=serial.PARITY_NONE)
    return ser
    
def main():
    
    global ser
    
    global user
    global password

    parser = OptionParser()
    parser.add_option("-d", "--dev", dest="dev", action="store", help="tty dev(ex. '/dev/ttyUSB0'", metavar="DEV")
    parser.add_option("-u", "--user", dest="user", action="store", help="Your Rock 7 Core Username", metavar="USER")
    parser.add_option("-p", "--passwd", dest="passwd", action="store", help="Your Rock 7 Core Password", metavar="PASSWD")
   
    (options, args) = parser.parse_args()
    
    try:
        ser = open_port(options.dev,19200)
    except:
        print "Could not open serial port.  Exiting."
        print "FYI - Here's a list of ports on your system."
        print list_serial_ports()
        sys.exit()
    
    command = "AT+CGMI\r"
    ser.write(command)
    out = ''
    # Wait one second before reading the output to give device time to answer
    time.sleep(3)
    # If there are characters left in the buffer, store them to out
    while ser.inWaiting() > 0:
	out += ser.read(1)
    #Print the full response
    print out
                
if __name__ == '__main__':
    main()