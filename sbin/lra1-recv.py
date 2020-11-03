import atexit
import base64
import urllib3
import serial
import shutil
import sys
import syslog
import threading
import time
import os

HTTP_POST_URL = 'http://localhost/upload.php'
LRA1_SERIAL_DEV = '/dev/ttyAMA0'
LRA1_SERIAL_BAUD = 115200
LRA1_SERIAL_TIMEOUT = 70
SAVEPATH_SEND_FAIL = '/var/spool/lra1-recv'

work = True
send_buffer_list = []

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

def get_miss_send():
    path = os.path.join(SAVEPATH_SEND_FAIL, 'send.data')
    if not os.path.exists(path):
        return ''

    read = ''
    try:
        with open(path, mode='r') as f:
            read = f.read()
    except (OSError, IOError) as e:
        syslog.syslog(syslog.LOG_WARNING, 'failed to get spool [' + path + '] - ' + e.strerror)

    return read

def save_miss_send(data):
    path = os.path.join(SAVEPATH_SEND_FAIL, 'send.data')
    try:
        if not os.path.exists(SAVEPATH_SEND_FAIL):
            os.makedirs(SAVEPATH_SEND_FAIL)

        with open(path, mode='w') as f:
            f.write(data)
    except (OSError, IOError) as e:
        syslog.syslog(syslog.LOG_WARNING, 'failed to save spool [' + path + '] - ' + e.strerror)

def remove_miss_send():
    if os.path.exists(SAVEPATH_SEND_FAIL):
        shutil.rmtree(SAVEPATH_SEND_FAIL, True)

def authorization_header():
    if ('HTTP_POST_USER' not in os.environ) or ('HTTP_POST_PASSWORD' not in os.environ):
        return {}

    post_user = os.environ.get('HTTP_POST_USER')
    post_password = os.environ.get('HTTP_POST_PASSWORD')

    basic_user_and_pasword = base64.b64encode('{}:{}'.format(post_user, post_password).encode('utf-8'))
    return {"Authorization": "Basic " + basic_user_and_pasword.decode('utf-8')}

def send_data(data):
    buffer = get_miss_send() + data
    if len(buffer) == 0:
        return

    try:
        http = urllib3.PoolManager(headers=authorization_header())
        http.request('POST', HTTP_POST_URL, fields={'data': buffer})
        remove_miss_send()
    except urllib3.exceptions.HTTPError as e:
        syslog.syslog(syslog.LOG_WARNING, 'http exception - ' + e.message)
        save_miss_send(buffer)

def send_work(lock):
    while work == True:
        buffer = ''
        lock.acquire()
        for i in range(len(send_buffer_list)):
            buffer += send_buffer_list.pop(0) + '\n'
        lock.release()
        send_data(buffer)
        time.sleep(10)

def push_buffer(data, lock):
    lock.acquire()
    send_buffer_list.append(data)
    lock.release()

def on_exit():
    syslog.syslog(syslog.LOG_INFO, "terminating...")
    work = False

def main():
    atexit.register(on_exit)
    lock = threading.Lock()
    send_thread = threading.Thread(target=send_work, args=(lock, ))
    send_thread.start()

    while work == True:
        try:
            data = lra1_receive()
            if(data.startswith('>') or len(data) == 0):
                lra1_break_ctrl()
                lra1_set_recv()
            else:
                push_buffer(data, lock)
        except KeyboardInterrupt:
            sys.exit()
    send_thread.join()

if __name__ == '__main__':
    main()