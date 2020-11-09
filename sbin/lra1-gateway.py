#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

HTTP_POST_URL = os.environ.get('HTTP_POST_URL')
LRA1_SERIAL_DEV = os.environ.get('LRA1_SERIAL_DEV', '/dev/ttyAMA0')
LRA1_SERIAL_BAUD = int(os.environ.get('LRA1_SERIAL_BAUD', '115200'))
LRA1_SERIAL_TIMEOUT = int(os.environ.get('LRA1_SERIAL_TIMEOUT', '70'))
LRA1_ENABLE_DISPLAY = True if int(os.environ.get('LRA1_ENABLE_DISPLAY', '0')) != 0 else False
SAVEPATH_SEND_FAIL = '/var/spool/lra1-gateway'

work = True
send_buffer_list = []

class LRA1():
    def __init__(self, dev, baudrate, timeout):
        self.ser = None
        self.dev = dev
        self.baudrate = baudrate
        self.timeout = timeout
        self._open()

    def __del__(self):
        if (self.ser is not None):
            self.ser.close()

    def _open(self):
        if (self.ser is not None):
            return

        try:
            self.ser = serial.Serial(
                port=self.dev,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                timeout=self.timeout,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
        except (serial.SerialException) as e:
            syslog.syslog(syslog.LOG_WARNING, 'Failed to open serial device ' + self.dev + ' - ' + e.strerror)
            self.ser = None

    def _send(self, message):
        self._open()
        if (self.ser is None):
            return

        self.ser.write(message)

    def receive(self):
        data = ''
        begin = time.time()
        while(time.time() - begin < LRA1_SERIAL_TIMEOUT):
            if (self.ser is not None):
                try:
                    data = self.ser.readline().strip()
                    if (len(data) > 0):
                        break
                except (serial.SerialException) as e:
                    self.ser.close()
                    self.ser = None
            else:
                self._open()
            time.sleep(3)

        return data

    def set_display(self, flag):
        self.display = flag

    def _wait_for_ok(self):
        get = ''
        while (self.ser is not None and get != 'OK'):
            get = self.ser.readline().strip()
            time.sleep(0.01)
        time.sleep(0.1)  # prevent for dropping first character

    def _display_message(self, message1='', message2='', clear=False):
        if (self.display == False):
            return
        if (clear == True):
            self._send('LCLR\r\n')
            self._wait_for_ok()
        if (message1):
            self._send('LPOS=0:LPRINT "' + message1 + '"\r\n')
            self._wait_for_ok()
        if (message2):
            self._send('LPOS=64:LPRINT "' + message2 + '"\r\n')
            self._wait_for_ok()

    def break_ctrl(self):
        self._send('\x03')  # Ctrl + C
        self._wait_for_ok()

    def set_recv(self):
        self._display_message('Gateway ', '   Ready')
        self._send('RECV\r\n')

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
        r = http.request('POST', HTTP_POST_URL, fields={'data': buffer})
        if (r.status == 200 or r.status == 400):
            remove_miss_send()
        else:
            syslog.syslog(syslog.LOG_WARNING, 'failed to POST by http status=' + str(r.status))
            save_miss_send(buffer)
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

    lra1 = LRA1(LRA1_SERIAL_DEV, LRA1_SERIAL_BAUD, LRA1_SERIAL_TIMEOUT)
    lra1.set_display(LRA1_ENABLE_DISPLAY)
    lra1.break_ctrl()
    lra1.set_recv()

    while work == True:
        try:
            data = lra1.receive()
            if(data.endswith('>') or len(data) == 0):
                #syslog.syslog(syslog.LOG_INFO, 'received data -> [' + data + ']')
                lra1.break_ctrl()
                lra1.set_recv()
            else:
                push_buffer(data, lock)
        except KeyboardInterrupt:
            sys.exit()
    del lra1
    send_thread.join()

if __name__ == '__main__':
    main()