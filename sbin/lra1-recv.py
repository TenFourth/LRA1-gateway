import urllib3
import serial
import time

HTTP_POST_URL = 'http://localhost/upload.php'
LRA1_SERIAL_DEV = '/dev/ttyAMA0'
LRA1_SERIAL_BAUD = 115200
LRA1_SERIAL_TIMEOUT = 60

def lra1_receive():
    ser = serial.Serial(LRA1_SERIAL_DEV, LRA1_SERIAL_BAUD)
    ser.timeout = LRA1_SERIAL_TIMEOUT
    str = ser.readline().strip()
    ser.close()
    return str

def lra1_break_ctrl():
    ser = serial.Serial(LRA1_SERIAL_DEV, LRA1_SERIAL_BAUD)
    ser.write('\x03')  # Ctrl + C
    time.sleep(1)
    ser.close()

def lra1_set_recv():
    ser = serial.Serial(LRA1_SERIAL_DEV, LRA1_SERIAL_BAUD)
    ser.write('RECV\r\n')
    ser.close()

def send_data(data):
    http = urllib3.PoolManager()
    http.request('POST', HTTP_POST_URL, fields={'data': data})

while True:
    data = lra1_receive()
    if(data.startswith('>') or len(data) == 0):
        lra1_break_ctrl()
        lra1_set_recv()
    else:
        send_data(data)