#!/usr/bin/env python3

import os
import sys
import time
import RPi.GPIO as GPIO

pin_closed = 17
pin_open = 18
pin_btn = 22
pin_red = 23
pin_gnd = 24
pin_led = 25

deb = False
stop = False

GPIO.setmode(GPIO.BCM)

GPIO.setup(pin_led, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(pin_red, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(pin_gnd, GPIO.OUT, initial=GPIO.LOW)

GPIO.setup(pin_closed, GPIO.IN)
GPIO.setup(pin_open, GPIO.IN)
GPIO.setup(pin_btn, GPIO.IN)

def motor(cmd):
	if (cmd == 'open'):
		GPIO.output(pin_red, False)
		GPIO.output(pin_gnd, True)
		return
	if (cmd == 'close'):
		GPIO.output(pin_red, True)
		GPIO.output(pin_gnd, False)
		return
	if (cmd == 'stop'):
		GPIO.output(pin_red, False)
		GPIO.output(pin_gnd, False)
		return
	
def door_open(brewing):
	if (GPIO.input(pin_open) == False):
		print('\tdoor already opened')
		return

	led = 1
	tstamp = time.time()
	GPIO.output(pin_led, led)
	motor('open')
	while(1):
		if (GPIO.input(pin_open) == False):
			break
		if ((time.time() - tstamp) >= 0.1):
			tstamp = time.time()
			led = led ^ 1	
			GPIO.output(pin_led, led)
	motor('stop')
	if (brewing and GPIO.input(pin_btn) == 0):
		global stop
		stop = True
	if (deb): print('\tdoor opened')
	return

def door_close():
	if (GPIO.input(pin_closed) == False):
		print("\tdoor already closed")
		return
	led = 1
	tstamp = time.time()
	GPIO.output(pin_led, led)
	motor('close')
	while(1):
		if (GPIO.input(pin_closed) == False):
			break
		if ((time.time() - tstamp) >= 0.1):
			tstamp = time.time()
			led = led ^ 1	
			GPIO.output(pin_led, led)

	motor('stop')
	if (deb): print("\tdoor closed")
	GPIO.output(pin_led, False)
	return

def led_sleep(sleep):
	led = 1
	tstamp = time.time()
	GPIO.output(pin_led, led)
	while((time.time() - tstamp) < sleep):
		time.sleep(0.1)
		led = led ^ 1	
		GPIO.output(pin_led, led)
		if (GPIO.input(pin_btn) == 0):
			door_open(False)
			global stop
			stop = True
			break

	GPIO.output(pin_led, False)
	
def door_cycle(i, brewing):
	global stop
	start = time.time()
	if (deb): print("starting cycle {}".format(i+1))
	door_open(brewing)
	if (stop == False):
		door_close()
		led_sleep(5)
	end = time.time()
	if (deb): print('cycle time {0:.2f} sec'.format(end - start))
	
try:
	# one command line parameter - brewing time, minutes 
	brewing = len(sys.argv)
	if (brewing > 1):
		brewing = float(sys.argv[1])
	else:
		brewing = 2.0 # default - 2 minutes
	# convert seconds to steps
	steps = (brewing * 60) / 10 - 1
	steps = int(steps)
	print('Brewing time is set to {} minutes or {} cycles'.format(brewing, steps))
	if (deb):
		print('door sensor state:')
		print('\tclosed: ', GPIO.input(pin_closed) == 0)
		print('\topened: ', GPIO.input(pin_open) == 0)
		print('Button: ',  GPIO.input(pin_btn) == 0)
	if (GPIO.input(pin_closed)):
		if(deb): print('initializing')
		door_close()

	print('Please press the button to start tea brewing')
	state = 0
	tstop = 0
	while(1):
		if (GPIO.input(pin_btn) == 0):
			if (state == 0):
				GPIO.output(pin_led, True)
				if (stop == False):
					door_open(False)
					state = 1
					print('Please attach fresh tea bag and press the button')
				else:
					if ((time.time() - tstop) > 2):
						door_close()
						stop = False
						print('Please press the button to start tea brewing')
				continue
			if (state == 1):
				print('Starting tea brewing, to stop press the button when lid is open')
				stop = False
				door_close()
				print('Presoaking for 10 seconds', end='')
				sys.stdout.flush()
				led_sleep(10)
				print('')
				for i in range (0,steps):
					if (stop == True):
						print('\nTerminating brewing process, press the button to close')
						tstop = time.time()
						break
					print("\r{} cycles left".format(steps - i), end='')
					door_cycle(i, True)
					sys.stdout.flush()
				else:
					door_open(False)
				state = 2
				GPIO.output(pin_led, False)
				if (stop == False):
					print("\rExecuted {} cycles.".format(steps))
					print("Your tea is ready! Please remove used tea bag and press the button to close.")
				continue
			if (state == 2):
				if (stop == False):
					door_close()
					print('Please press the button to start tea brewing')
				state = 0;
				continue
		
except:
    pass

print('\nRestoring GPIO status')
GPIO.cleanup()