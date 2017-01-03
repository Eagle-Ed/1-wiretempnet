#!/usr/bin/env python
import os, glob, time, gspread, sys, datetime, logging, threading
import MySQLdb as mdb

#Author: Chris Baker : chris@cleverhome.co.uk
#Version: 1.00
#Descrition: This version has MySQL and Google Spreadsheet code.
#Last Proven: Stable in Dec 2016, running for over a year.

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(filename='./debug.txt',level=logging.INFO,format=FORMAT)

#Update the following values to match your environment.
email = ''
password = ''
spreadsheet = 'Temperature_Log'
sleep_time = 600
devices = list()

# My SQL Params
mysqlserver = 'localhost'
mysqldb = 'temps'
mysqluserid = 'temps'
mysqlpw = ''
mysqltable = 'temp_sensors'

logging.debug('Google Account -  %s , File Name - %s', email, spreadsheet)

#time.sleep(200)

logging.debug('Detecting devices')
os.system('sudo modprobe w1-gpio')
os.system('sudo modprobe w1-therm')

def update_db(sensor_id, date_time, temp):
	try:
		con = mdb.connect(mysqlserver, mysqluserid, mysqlpw, mysqldb);

		cur = con.cursor()
		logging.debug("INSERT INTO " + mysqltable + "(sensor_id, date_time, temp) VALUES('" + sensor_id + "','" + date_time.strftime('%Y-%m-%d %H:%M:%S')+ "'," + str(temp) + ")")
		cur.execute("INSERT INTO " + mysqltable + "(sensor_id, date_time, temp) VALUES('" + sensor_id + "','" + date_time.strftime('%Y-%m-%d %H:%M:%S') + "'," + str(temp) + ")")

		con.commit()
	except mdb.Error, e:

		logging.error("Error %d: %s" % (e.args[0],e.args[1]))

	finally:

		if con:
			con.close()

class W1Therm:
	device_path = ''
	previous_temp = 0
	current_temp = 0
	def __init__(self, device_path):
		self.device_path = device_path
	def get_device_path(self):
		return self.device_path
	def get_device(self):
		return self.device_path.replace('/sys/bus/w1/devices/','')
	def get_temp(self):
		checkforYES = False
		retrycount = 0
		while not(checkforYES) and retrycount < 4:
			lines = read_temp_raw(self.device_path)
			for x in range(len(lines)):
				if not(lines[x].find('crc=')==-1):
					if lines[x].strip()[-3:] == 'YES':
						checkforYES = True
					else:
						checkforYES = False
						time.sleep(0.2)
						retrycount = retrycount + 1
				if not(lines[x].find('t=')==-1):
					equals_pos = lines[x].find('t=')
					temp = float(lines[x][equals_pos+2:])/1000
		if checkforYES:
			self.previous_temp = self.current_temp
			self.current_temp = temp
		return self.current_temp
	def get_current_temp(self):
		return self.current_temp
	def get_previous_temp(self):
		return self.previous_temp
def get_columns():
	try:
			gc = gspread.login(email,password)
			logging.debug('Google spreadsheet connection open.')
			worksheet = gc.open(spreadsheet).sheet1
			headers = worksheet.row_values(1)
	except:
			logging.error('Could not open Google spreadsheet connection.')
			return list()
	return headers

def get_column_number():

	#Clean list to obtain device serial numbers only, stripping path.
	for x in range(len(device_folder)):
		devices.append(device_folder[x].replace('/sys/bus/w1/devices/',''))

	columns = get_columns()

	#for x in range(len(columns)):
	#	if columns[x].find

	#print ','.join(devices)

def read_temp_raw(device_path):
	f_1 = open(device_path + '/w1_slave', 'r')
	lines = f_1.readlines()
	f_1.close()
	return lines

def isodd(num):
	return num & 1 and True or False

def read_temp():
	#read all therms
	lines = read_temp_raw()
	#print ','.join(lines)
	checkforYES = False
	while not(checkforYES):
		for x in range(len(lines)):
			if lines[x].find('crc='):
				if lines[x].strip()[-3:] == 'sES':
					checkforYES = True
				else:
					checkforYES = False
		time.sleep(0.2)
		lines = read_temp_raw()

	temp1 = list()
	temp = int()
	for x in range(len(lines)):
		if lines[x].find('t='):
			equals_pos = lines[x].find('t=')
			temp = float(lines[x][equals_pos+2:])/1000
			temp1.append(temp + "," + lines[x+1])
	return temp1

#try:
device_folder = glob.glob('/sys/bus/w1/devices/28*')
#Get all therms
for x in range(len(device_folder)):
	devices.append(W1Therm(device_folder[x]))
	logging.info('Device detected -  %s , current temp = %s', devices[x].get_device(), devices[x].get_temp())

def worker():
    """thread worker function"""
    print 'Worker'
    return

while True:

	#get_column_number()
	gscolumns = get_columns()
	values = [''] * len(gscolumns)

	headerupdate = False
	for devnum in range(len(devices)):
		update_db(devices[devnum].get_device() ,datetime.datetime.now(),devices[devnum].get_temp())
		found = False
		#search columns for serial number of current device.
		for colnum in range(len(gscolumns)):
			if not(gscolumns[colnum].find(devices[devnum].get_device())==-1):
				values[colnum] = datetime.datetime.now()
				values[colnum] = devices[devnum].get_temp()
				found = True
		if not(found):
			values.append(devices[devnum].get_temp())
			headerupdate = True
	try:
		gc = gspread.login(email,password)

		logging.debug('Google spreadsheet connection open.')
		worksheet = gc.open(spreadsheet).sheet1

		try:
			logging.debug('Appending data to GS.')
			worksheet.append_row(values)
		except:
			logging.error('Google spreadsheet append row failed.')
	except:
		logging.error('Could not open Google spreadsheet connection.')
	logging.debug('Sleeping...')
	time.sleep(sleep_time)
