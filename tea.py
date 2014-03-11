#!/usr/bin/env python3

import sys
import time
import argparse
import RPi.GPIO as GPIO

###
# For remote debugging from Visual Studio uncomment following two lines
#import ptvsd
#ptvsd.enable_attach(secret=None)

pin_closed = 17 # CD tray sensor
pin_open = 18   # CD tray sensor
pin_btn = 22    # CD button
pin_red = 23    # motor's red wire
pin_gnd = 24    # motor's gnd wire 
pin_led = 25    # LED

stop = False    # termination flag
dobreak = True
nobreak = False

# command line arguments
dbg = False     # debug output
soak = 5        # soaking time, sec
brewing = 2.5   # brewing time, min
presoaking = 10 # pre-soaking time, sec

# brewing states
START   = 0
BREWING = 1
READY   = 2

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
def tray_open(breakable = False):
	if (GPIO.input(pin_open) == False):
		if (dbg): print('\ttray already opened')
		return

	led = 1
	tstamp = time.time()
	GPIO.output(pin_led, led)
	motor('open')
	while(1):
		if (GPIO.input(pin_open) == False):
			break
		if (breakable and GPIO.input(pin_btn) == 0):
			global stop
			stop = True
		if ((time.time() - tstamp) >= 0.1):
			tstamp = time.time()
			led = led ^ 1	
			GPIO.output(pin_led, led)
	motor('stop')
	if (dbg): print('\ttray opened')
	return

# closes CD tray
def tray_close(breakable = True):
	if (GPIO.input(pin_closed) == False):
		if (dbg): print("\ttray already closed")
		return
	led = 1
	tstamp = time.time()
	GPIO.output(pin_led, led)
	motor('close')
	while(1):
		if (GPIO.input(pin_closed) == False):
			break
		if (breakable and GPIO.input(pin_btn) == 0):
			global stop
			stop = True
			break
		if ((time.time() - tstamp) >= 0.1):
			tstamp = time.time()
			led = led ^ 1	
			GPIO.output(pin_led, led)
	motor('stop')
	if (dbg): print("\ttray closed")
	GPIO.output(pin_led, False)
	return

# sleeps and flashes LED
def led_sleep(sleep):
	if (sleep <= 0):
		return
	led = 1
	tstamp = time.time()
	GPIO.output(pin_led, led)
	while((time.time() - tstamp) < sleep):
		time.sleep(0.1)
		led = led ^ 1	
		GPIO.output(pin_led, led)
		if (GPIO.input(pin_btn) == 0):
			tray_open(nobreak)
			global stop
			stop = True
			break
	GPIO.output(pin_led, False)

# cycles through open-close-sleep states	
def tray_cycle(i, breakable):
	global stop
	start = time.time()
	if (dbg): print("starting cycle {}".format(i+1))
	tray_open(breakable)
	if (stop == False):
		tray_close(dobreak)
		led_sleep(soak)
	if (stop == True):
		tray_open(nobreak)
	end = time.time()
	if (dbg): print('cycle time {0:.2f} sec'.format(end - start))

# main
# parse arguments
parser = argparse.ArgumentParser(description="""CD Tea Brewing Machine""");
parser.add_argument('--dbg', action='store_true', default = False, help="Enable debug output")
parser.add_argument('--brewing', type=float, default=2.5, help="Brewing time, min")
parser.add_argument('--soak', type=int, default=5, help="Tea bag soaking time, per cycle, sec")
parser.add_argument('--presoaking', type=int, default=10, help="Tea bag pre-soaking time, sec")

args = parser.parse_args()

dbg = args.dbg
soak = args.soak
brewing = args.brewing
presoaking = args.presoaking

try:
	# convert seconds to steps
	steps = (brewing * 60) / 10 - 1
	steps = int(steps)
	print('Brewing time is set to {} minutes or {} cycles'.format(brewing, steps))
	if (dbg):
		print('Presoaking: {} sec'.format(presoaking))
		print('Each cycle soak time: {} sec'.format(soak))
		print('tray sensor state:')
		print('\tclosed: ', GPIO.input(pin_closed) == 0)
		print('\topened: ', GPIO.input(pin_open) == 0)
		print('Button: ',  GPIO.input(pin_btn) == 0)
	if (GPIO.input(pin_closed)):
		if(dbg): print('initializing')
		tray_close(nobreak)

	print('Please press the button to start tea brewing')
	state = START
	tstop = 0
	while(1):
		if (GPIO.input(pin_btn) == 0):
			if (state == START):
				GPIO.output(pin_led, True)
				if (stop == False):
					tray_open(nobreak)
					state = BREWING
					print('Please attach fresh tea bag and press the button')
				else:
					if ((time.time() - tstop) > 2):
						stop = False
						tray_close(nobreak)
						print('Please press the button to start tea brewing')
				continue
			if (state == BREWING):
				print('Starting tea brewing, to stop press the button')
				stop = False
				tray_close(nobreak)
				print('Presoaking for {} seconds'.format(presoaking), end='')
				sys.stdout.flush()
				led_sleep(presoaking)
				print('')
				for i in range (0,steps):
					if (stop == True):
						print('\nTerminating brewing process, press the button to close')
						tstop = time.time()
						break
					print("\r{} cycles left ".format(steps - i), end='')
					tray_cycle(i, dobreak)
					sys.stdout.flush()
				else:
					tray_open(nobreak)
				state = READY
				GPIO.output(pin_led, False)
				if (stop == False):
					print("\rExecuted {} cycles.".format(steps))
					print("Your tea is ready! Please remove used tea bag and press the button to close.")
				continue
			if (state == READY):
				if (stop == False):
					tray_close(nobreak)
					print('Please press the button to start tea brewing')
				state = START;
				continue
		
except:
    pass

print('\nRestoring GPIO status')

tray_close(nobreak)
GPIO.output(pin_led, False)
GPIO.cleanup()
