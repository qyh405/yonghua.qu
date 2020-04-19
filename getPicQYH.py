#!/usr/bin/python3

# -*- coding: utf-8 -*-
from datetime import datetime
import time
import os
import numpy as np
from fractions import Fraction

import RPi.GPIO as GPIO
from apscheduler.schedulers.background import BackgroundScheduler
from picamera import PiCamera
import picamera.array
import configparser

from ftplib import FTP
import shutil
import socket
import logging
Soft_Version = 10
Smart_Photo_Type = 2
Cmd_Type = 0x40
CMD_SEARCH_DEVICE = 0x00

DeviceType = 'SmartPhoto'

USB_MOUNT_PATH = '/home/pi/SMARTPHOTO'
PARAM_PATH = '/home/pi/SMARTPHOTO/Param/Param.ini'

imgDir = '/home/pi/SMARTPHOTO/Pictures/unsend/'
sended_path = '/home/pi/SMARTPHOTO/Pictures/sended'

heart = bytearray([0xAA, 0x55, 0, 16, 0x00, 0x00, Smart_Photo_Type, Cmd_Type, CMD_SEARCH_DEVICE, 00, 00, Smart_Photo_Type, Soft_Version, 0x07, 0xE2, 6, 6, 21,50,00,0x68,0x86])    

global sockLocal
sockLocal = None

def Connect_Server(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try :

        sock.connect((host,port))
    except :
        return None
    return sock

def Send_Data(host, port, data):
    global sockLocal
    try:
        sockLocal.send(data)
    except socket.error:
        print('Sock Error, Reconnect')
        sockLocal = Connect_Server(host,port)
    except:
        print('Send Error')

def Send_Heart_To_Server():
    global sockLocal #qyh
    if(False == os.path.exists(USB_MOUNT_PATH) or False == os.path.exists(PARAM_PATH)):
        print('No Param file, or No usb Disk ...')
        sockLocal.close()
        sockLocal = None
        return
    #Get Param
    logging.basicConfig()
    conf = configparser.ConfigParser()
    try:
        conf.read(PARAM_PATH)
    except(NameError, IOError) as result:
        print('Read Server Param Error:', result)
        return;
    try:
        Server_IP = conf.get("SERVER","SERVER_IP").strip()
        Server_Port = conf.get("SERVER","SERVER_PORT").strip()
        Photo_ID = conf.get("SMARTPHOTO", "PHOTO_ID").strip()

    except:
        print('Server Param Error, Please Check.')
        return
    if(Photo_ID.isdigit() and Server_Port.isdigit()):
        pass
    else:
        print('Param Error')
        return
    global sockLocal
    if(sockLocal == None):
        print('Connect First')
        sockLocal = Connect_Server(Server_IP, int(Server_Port))
    heart[4] = heart[9] = (int(Photo_ID) >> 8)
    heart[5] = heart[10] = int(Photo_ID) & 0xff
    GetTime = time.localtime()
    GetYear = GetTime.tm_year
    heart[13] = GetYear >> 8
    heart[14] = GetYear & 0xff
    heart[15] = GetTime.tm_mon
    heart[16] = GetTime.tm_mday
    heart[17] = GetTime.tm_hour
    heart[18] = GetTime.tm_min
    heart[19] = GetTime.tm_sec
    Send_Data(Server_IP, int(Server_Port), heart)

def IsWorkTime( a, b, c):
    if(a==b):
        return True
    if(a<b):
        if(a<=c and c<b):
            return True
        else:
            return False
    else:
        if(c>=b and c<a):
            return False
        else:
            return True

def SmartPhotoRun():
    #Check USB and Param

    #Get Time.
    fmt = '%Y_%m_%d_%H%M%S'
    curTime = time.localtime()
    curHour = curTime.tm_hour
    curMin = curTime.tm_min
    curTime = time.strftime(fmt,curTime)
    print(curTime)
    if(False == os.path.exists(USB_MOUNT_PATH) or False == os.path.exists(PARAM_PATH)):
        print('No Param file, or No usb Disk ...')
        return
    if not os.path.exists(sended_path):
        os.makedirs(sended_path)
    if not os.path.exists(imgDir):
        os.makedirs(imgDir)

    #Get Param
    logging.basicConfig()
    conf = configparser.ConfigParser()
    try:
        conf.read(PARAM_PATH)
    except(NameError, IOError) as result:
        print('Read Param Error:', result)
        return
    try:
        Ftp_Host = conf.get("FTP","FTP_HOST").strip()
        Ftp_Port = conf.get("FTP","FTP_PORT").strip()
        Ftp_User = conf.get("FTP","FTP_USRNAME").strip()
        Ftp_Pwd = conf.get("FTP","FTP_PWD").strip()
        Ftp_Pasv = conf.get("FTP", "FTP_PASVMODE").strip()

        Photo_ID = conf.get("SMARTPHOTO", "PHOTO_ID").strip()
        Photo_Net_Mode = conf.get("SMARTPHOTO", "NET_MODE").strip()
        Photo_Acq_Cycle = conf.get("SMARTPHOTO", "ACQ_CYCLE").strip()
        Photo_Start_Hour = conf.get("SMARTPHOTO", "START_HOUR").strip()
        Photo_End_Hour = conf.get("SMARTPHOTO", "END_HOUR").strip()
    except:
        print('Param Error, Please Check.')
        return
    if(Photo_ID.isdigit() and Photo_Acq_Cycle.isdigit() and Photo_Start_Hour.isdigit() and Photo_End_Hour.isdigit()):
        pass
    else:
        print('Acq Param Error')
        return

    if((Photo_Net_Mode.lower() != 'true') and (Photo_Net_Mode.lower() !='false')):
        print('Net Mode Param Error')
        return

    #Check Param
    if(int(Photo_Start_Hour) < 0 or int(Photo_Start_Hour)>23 or int(Photo_End_Hour)<0 or int(Photo_End_Hour)>23):
        print('Warning: Photo Start and End Working Hour Parm Error, Device will not Sleep')
        Photo_Start_Hour = 0
        Photo_End_Hour = 0

    if(int(Photo_Acq_Cycle)<1 or int(Photo_Acq_Cycle)>60):
        print('The collection cycle should be from 1 to 60 minutes')
        return
    print('Ftp_Host:', Ftp_Host)
    print('Ftp_Port:', Ftp_Port)
    if(Ftp_Port.isdigit()):
        pass
    else:
        print('Param Error')
        return
    print('Ftp_User:', Ftp_User)
    print('Ftp_Pwd:', Ftp_Pwd)
    print('Ftp_Passive:', Ftp_Pasv)

    print('Photo_ID:', Photo_ID)
    print('Photo_Net_Mode:', Photo_Net_Mode)
    print('Photo_Acq_Cycle:', Photo_Acq_Cycle)
    print('Photo_Start_Hour:', Photo_Start_Hour)
    print('Photo_End_Hour:', Photo_End_Hour)

    WorkStatus = IsWorkTime(int(Photo_Start_Hour), int(Photo_End_Hour), curHour)

    if(WorkStatus == False):
        print('Status : Sleep')
        return
    else:
        if((curHour*60+curMin)%int(Photo_Acq_Cycle) != 0):
            print('Sleep')
            return
    print('Start Capture Pic')
    capturePI(imgDir, Photo_ID,curTime)
    if(Photo_Net_Mode.lower() == 'true'):
        print('Send Pictures')
        try:
            os.system('sudo ifconfig tun0 down')
        except:
            print('No tun0')
        sendFiles(Ftp_Host, Ftp_Port, Ftp_User, Ftp_Pwd, imgDir, sended_path, Photo_ID)
        print('Send Over')
        try:
            os.system('sudo ifconfig tun0 up')
        except:
            print('No tun0')
def shootTwoPictures(siteID, camera, imgDir, cameraID, curTime, filterFlag):
        """
        Shoot two pictures, the first one is common jpeg, the second is RAW
        parameter: filterFlag = 1: the RGB image, filterFlag = 2: RED-NIR filter
        """
        
#        siteID = 'Mark'
        
        # use the auto awb mode
        if filterFlag == 1:
            GPIO.output(21, True)
        else:
            GPIO.output(21, False)
        # Set ISO accroding to curtime
        strTime = curTime.split('_')[-1]
        hh = int(strTime[0:2])
        if hh > 7 and hh < 17:
            iso = 100 # set a lower iso for the day time
        else:
            iso = 500 #set higher value for the morning or night time
        camera.iso = iso
        # Wait for the automatic gain control to settle
        time.sleep(2)
        # Now fix the values
        camera.shutter_speed = camera.exposure_speed
        camera.exposure_mode = 'off'
        g = camera.awb_gains
        camera.awb_mode = 'off'
        camera.awb_gains = g
        time.sleep(2)
        # use the default filter (NoIR) for the common jpeg image
        
        strList = [imgDir,'/',cameraID, '_', str(filterFlag), '_',curTime,'.jpeg']
        imgFile = ''.join(strList) # file name as :cameraID_YYYY_mm_dd_HHMMSS
        camera.awb_mode = 'auto'
        camera.capture(imgFile, format='jpeg', bayer=False)
        paramText = [imgDir,'/',cameraID,'_',str(filterflag), '_', curTime, '.txt']
        paramText = ''.join(paramText)
        
        camera.annotate_text = 'site:' + siteID + ' Camera:' + cameraID + ' Time:' + curTime
        
        # switch the filter to RED-NIR filter
        
        time.sleep(5)
        camera.raw_format = 'rgb'
        strList = [imgDir,'/',cameraID, '_', str(filterFlag), '_',curTime,'.npy']
        imgFile = ''.join(strList) # file name as :cameraID_YYYY_mm_dd_HHMMSS'
        with picamera.array.PiBayerArray(camera) as stream:
            camera.capture(stream, 'jpeg', bayer = True)
            rawing = stream.demosaic()
            np.save(imgFile, rawing)
        f1 = open(paramText, 'w')
        f1.write('awbmode:'+camera.awb_mode+'\n')
        f1.write('awb_gains:')
        f1.write(str(g)+'\n')
        f1.write('analog_gain:'+str(camera.analog_gain)+'\n')
        f1.write('digital_gain:'+str(camera.digital_gain)+'\n')
        f1.write('drc_strength:'+str(camera.drc_strength)+'\n')
        f1.close()
        camera.awb_mode = 'auto'
        
        
def capturePI(imgDir, cameraID, curTime):
    os.system('sudo systemctl stop mjpg-streamer.service')
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(21, GPIO.OUT)
    camera = PiCamera()
    camera.resolution = (2560,1920)
    #camera.iso = 100
    time.sleep(2)
    siteID = 'Mark '
    # time.sleep(5) # give the camera 5 seconds before capturing
    try:
        for filterFlag in range(1,3):
            shootTwoPictures(siteID, camera, imgDir, cameraID, curTime, filterFlag)
            time.sleep(2)
        time.sleep(2)

    finally:
       camera.close()
    #GPIO.cleanup()
    time.sleep(1)
    os.system('sudo systemctl start mjpg-streamer.service')

def ftpconnect(host, port, username, password):
    try:
    	ftp = FTP()
    	socket.setdefaulttimeout(50)
    	# ftp.set_debuglevel(2)
    	ftp.connect(host, int(port))
    except (socket.error, socket.gaierror):
        print ('Error: cannot connect %s' % host)
        return None
    try:
        ftp.login(username, password)
    except ftplib.error_perm:
        print ('Error: Can not login')
        ftp.quit()
        return None
    return ftp


def downloadfile(ftp, remotepath, localpath):
    bufsize = 1024
    fp = open(localpath, 'wb')
    ftp.retrbinary('RETR ' + remotepath, fp.write, bufsize)
    ftp.set_debuglevel(0)
    fp.close()

def uploadfile(ftp, localpath, remotepath, file):
    bufsize = 1024
    try:
        ftp.mkd(remotepath)
    except:
        print(remotepath)
    try:
        ftp.cwd(remotepath)
    except:
        print('change dir:'+remotepath)
    fp = open(localpath, 'rb')
    ftp.storbinary('STOR ' + file, fp, bufsize)
    ftp.set_debuglevel(0)
    fp.close()

def sendFiles(Ftp_Host, Ftp_Port, Ftp_User, Ftp_Pwd, PhotoDir, Bak_path, Photo_ID):
    ftp = ftpconnect(Ftp_Host, Ftp_Port, Ftp_User, Ftp_Pwd)
    if not ftp:
        return
    logging.basicConfig()
    conf = configparser.ConfigParser()
    try:
        conf.read(PARAM_PATH)
    except(NameError, IOError) as result:
        print('Read FTP Param Error:', result)
        #return;
    Ftp_Pasv = conf.get("FTP", "FTP_PASVMODE").strip()
    Ftp_Pasv = 'false'
    if(Ftp_Pasv.lower() == 'true'):
        ftp.set_pasv(1)
    else:
        ftp.set_pasv(0)
    f_list = os.listdir(imgDir)
    for i in f_list:
        uploadfile(ftp,  PhotoDir+i, DeviceType+'/'+Photo_ID, i)
        shutil.move(PhotoDir+i, Bak_path)
    ftp.quit()

def tick():
    if(False == os.path.exists('/home/pi/SMARTPHOTO')):
        print('No usb Disk.\n')
        return
    print('Tick! The time is: %s' % datetime.now())

if __name__ == '__main__':

    #os.system('sudo killall wpa_supplicant')
    #time.sleep(2)
    #os.system("sudo wpa_supplicant -Dnl80211 -iwlan0 -c /media/pi/SMARTPHOTO/Param/wpa_supplicant.conf -B")
    scheduler = BackgroundScheduler()
    scheduler.add_job(SmartPhotoRun, 'cron', minute='*/1')
    scheduler.add_job(Send_Heart_To_Server, 'cron', minute='*/1')
    scheduler.start()
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    try:
        while(True):
            # This is here to simulate application activity (which keeps the main thread alive).
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
            # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()
