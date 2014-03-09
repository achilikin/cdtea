#!/usr/bin/env python3

import os
import sys
import time
import RPi.GPIO as GPIO

pin_closed = 17 # CD tray sensor
pin_open = 18   # CD tray sensor
pin_btn = 22    # CD button
pin_red = 23    # motor's red wire
pin_gnd = 24    # motor's gnd wire 
pin_led = 25    # LED

deb = False   # debug output
stop = False  # termination flag

presoaking = 10 # pre-soaking time, sec
soak = 5        # soaking time, sec

GPIO.setmode(GPIO.BCM)

GPIO.setup(pin_led, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(pin_red, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(pin_gnd, GPIO.OUT, initial=GPIO.LOW)

GPIO.setup(pin_closed, GPIO.IN)
GPIO.setup(pin_open, GPIO.IN)
GPIO.setup(pin_btn, GPIO.IN)

# motor control function
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

# opens CD tray
def tray_open(brewing):
	if (GPIO.input(pin_open) == False):
		if (deb): print('\ttray already opened')
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
	if (deb): print('\ttray opened')
	return

# closes CD tray
def tray_close():
	if (GPIO.input(pin_closed) == False):
		if (deb): print("\ttray already closed")
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
	if (deb): print("\ttray closed")
	GPIO.output(pin_led, False)
	return

# sleeps and flashes LED
def led_sleep(sleep):
	led = 1
	tstamp = time.time()
	GPIO.output(pin_led, led)
	while((time.time() - tstamp) < sleep):
		time.sleep(0.1)
		led = led ^ 1	
		GPIO.output(pin_led, led)
		if (GPIO.input(pin_btn) == 0):
			tray_open(False)
			global stop
			stop = True
			break
	GPIO.output(pin_led, False)

# cycles through open-close-sleep states	
def tray_cycle(i, brewing):
	global stop
	start = time.time()
	if (deb): print("starting cycle {}".format(i+1))
	tray_open(brewing)
	if (stop == False):
		tray_close()
		led_sleep(soak)
	end = time.time()
	if (deb): print('cycle time {0:.2f} sec'.format(end - start))

# main	
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
		print('tray sensor state:')
		print('\tclosed: ', GPIO.input(pin_closed) == 0)
		print('\topened: ', GPIO.input(pin_open) == 0)
		print('Button: ',  GPIO.input(pin_btn) == 0)
	if (GPIO.input(pin_closed)):
		if(deb): print('initializing')
		tray_close()

	print('Please press the button to start tea brewing')
	state = 0
	tstop = 0
	while(1):
		if (GPIO.input(pin_btn) == 0):
			if (state == 0):
				GPIO.output(pin_led, True)
				if (stop == False):
					tray_open(False)
					state = 1
					print('Please attach fresh tea bag and press the button')
				else:
					if ((time.time() - tstop) > 2):
						tray_close()
						stop = False
						print('Please press the button to start tea brewing')
				continue
			if (state == 1):
				print('Starting tea brewing, to stop press the button when tray is open')
				stop = False
				tray_close()
				print('Presoaking for {} seconds'.format(presoaking), end='')
				sys.stdout.flush()
				led_sleep(presoaking)
				print('')
				for i in range (0,steps):
					if (stop == True):
						print('\nTerminating brewing process, press the button to close')
						tstop = time.time()
						break
					print("\r{} cycles left".format(steps - i), end='')
					tray_cycle(i, True)
					sys.stdout.flush()
				else:
					tray_open(False)
				state = 2
				GPIO.output(pin_led, False)
				if (stop == False):
					print("\rExecuted {} cycles.".format(steps))
					print("Your tea is ready! Please remove used tea bag and press the button to close.")
				continue
			if (state == 2):
				if (stop == False):
					tray_close()
					print('Please press the button to start tea brewing')
				state = 0;
				continue
		
except:
    pass

print('\nRestoring GPIO status')

tray_close()
GPIO.output(pin_led, False)
GPIO.cleanup()