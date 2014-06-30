import pygame
import os.path
import time
import datetime
import picamera
import RPi.GPIO as GPIO
import urllib
import shutil
from twython import Twython, TwythonError

import statusfinder

# eventTypes
EVENT_NONE = 0
EVENT_RED_SHORT = 1    # red button pressed once
EVENT_RED_LONG = 2	# red button pressed for several seconds
EVENT_BLACK_SHORT = 3 # same as above
EVENT_BLACK_LONG = 4
EVENT_QUIT = 5

# states
STATE_NONE = 0
STATE_STARTUP = 1		# startup screen
STATE_PREVIEW = 2		# capture preview
STATE_TAKE_PHOTO = 3		# take a photo
STATE_DISPLAY = 4		# photo display
STATE_TWEET = 5			# tweet photo
STATE_TWEET_PHOTO = 6		# successful tweet (message)
STATE_DELETE_PHOTO = 7		# delete a photo (message)
STATE_NEXT_PHOTO = 8		# flip to next (message)

# colors
COLOR_BLACK = pygame.Color(0,0,0)
COLOR_WHITE = pygame.Color(255,255,255)
COLOR_RED = pygame.Color(255,0,0)
COLOR_SKY = pygame.Color(135,206,250)
COLOR_GRAY = pygame.Color(119,136,153)
COLOR_OLIVE = pygame.Color(107,142,35)

pygame.init()
screen = pygame.display.set_mode((0,0))
state = STATE_STARTUP

#globals
redLED = 4
greenLED = 17
redButton = 24
blackButton = 23
mx = 0	# message position (x)
my = 0	# message position (y)
startTime = 0		# timer functions
endTime = 0		# timer functions
buttonWaitTime = 3
hasWifi = False
takenImages = []
savedImages = []
rootDir = "/home/pi/usbdrv/"
takenImagesDir = rootDir + "taken_images/"
sentImagesDir = rootDir + "sent_images/"
imageIndex = -1
keys = []
username = "<no wifi>"
status = "no wifi"

# GPIO variables and initialization
def initGPIO():
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(redLED, GPIO.OUT)
	GPIO.setup(greenLED, GPIO.OUT)
	GPIO.setup(redButton, GPIO.IN)
	GPIO.setup(blackButton, GPIO.IN)
	GPIO.output(greenLED, False)
	GPIO.output(redLED, False)

# init pygame, any other screen stuff
def initScreen():
	global font
	pygame.mouse.set_visible(0)
	pygame.font.init()
	font = pygame.font.Font(None,36)

# keys are in a 4-line file
# line 1 = apiKey, line 2 = apiSecret, line 3 = accessToken, line 4 = access secret
def initTwitter():
	global keys
	global api
	global username
	global hasWifi
	global status

	f = open("keys.txt","r")

	for line in f:
		keys.append( line.rstrip('\n'))
	f.close()
	api = Twython(keys[0],keys[1],keys[2],keys[3])
	try:
		details = api.show_user(screen_name='SelfiesBot')
		username = details['name']
		status = "Connected" 
		hasWifi = True
	except TwythonError as e:
		username = "exception"
		status = "No Wifi"
		hasWifi = False

def debounce():
	time.sleep(0.05)

def getTimeStamp():
	ts = time.time()
	return datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d%H%M%S')

def getEvent():

	# ESCAPE KEY exits program
	for event in pygame.event.get():
		if event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE:
				return EVENT_QUIT

	# check GPIO  -- do debouce or something
	if GPIOCheck(redButton) == True:
		return EVENT_RED_SHORT
	elif GPIOCheck(blackButton) == True:
		return EVENT_BLACK_SHORT
	
	return EVENT_NONE

def GPIOCheck(buttonType):
	global buttonWaitTime
	buttonLong = False

	if GPIO.input(buttonType) == True:
		debounce()
		startTime = time.time()
		if buttonType == redButton:
			GPIO.output(redLED, True)
		elif buttonType == blackButton:
			GPIO.output(greenLED,True)

		while GPIO.input(buttonType) == True:
			if time.time() > startTime + buttonWaitTime:
				if buttonLong == False:
					buttonHeld(buttonType)
					buttonLong = True
		
		GPIO.output(redLED,False)
		GPIO.output(greenLED,False)
		if buttonLong == False:
			return True

# maps buttons to state changes
def buttonPressed(currentState, eventType):	
	newState = currentState

	# red button (quick press)
	if eventType == EVENT_RED_SHORT:
		if currentState == STATE_STARTUP:
			newState = STATE_PREVIEW
		elif currentState == STATE_PREVIEW:
			newState = STATE_TAKE_PHOTO		
		elif currentState == STATE_DISPLAY:
			newState = STATE_TWEET
	
	elif eventType == EVENT_BLACK_SHORT:
		if currentState == STATE_STARTUP:
			newState = STATE_DISPLAY
		elif currentState == STATE_DISPLAY:
			newState = STATE_NEXT_PHOTO
		elif currentState == STATE_TWEET:
			newState = STATE_DISPLAY
	return newState

def buttonHeld(buttonType):
	global state
	if buttonType == redButton:
		if state == STATE_DISPLAY:
			deletePhoto()
			changeState(STATE_DISPLAY)
		elif state == STATE_TWEET:
			tweetPhoto()
			changeState(STATE_STARTUP)
	elif buttonType == blackButton:
		if state == STATE_DISPLAY:
			changeState(STATE_STARTUP)
		if state == STATE_STARTUP:
			initTwitter()
			changeState(STATE_STARTUP)
def stateStartup():
	global keys
	global username
	global status

	background(COLOR_GRAY)
	resetMXY()

	if hasWifi == True:
		message(username)
		message(status)
	else:
		message(status)
		message(username)
	
	#s = statusfinder.getNextStatus()
	#message(s)
	#statusfinder.saveStatus(s)
	
	# prints out our keys
	#for i in range(0,len(keys)):
	#	message(keys[i])
	updateScreen()

def statePreview():
	global status
	background(COLOR_BLACK)
	updateScreen()
	camera.start_preview()
	if hasWifi == True:
		status = "Connected"
	else:
		status = "No wifi"

def stateDisplay():
	global imageIndex
	global status
	if hasWifi == True:
		status = "Connected"
	else:
		status = "No wifi"

	background(COLOR_OLIVE)
	loadImages()
	resetMXY()
	drawImage()
	displayImageFiles()
	if imageIndex >= 0:
		message( "Showing: " + takenImages[imageIndex])
	updateScreen()

def displayImageFiles():
	global takenImages
	global imageIndex

	loadImages()
	if len(takenImages) == 0:
		message("No images")
	else:
		message("Images")
		for i in range(0,len(takenImages)):
			message(takenImages[i])
	message(" ")

def drawImage():
	if imageIndex >= 0:
		im = pygame.image.load(takenImagesDir+takenImages[imageIndex])
		im = pygame.transform.scale(im, (400,300))
		screen.blit(im,(100,160))

def stateTweet():
	background(COLOR_SKY)
	resetMXY()
	message("Hold RED button down to Tweet this image")
	drawImage()
	updateScreen()

def tweetPhoto():
	global api
	global status
	success = False
	
	message("Tweeting")
	updateScreen()

	msg = getRandomMessage()
	
	if not imageIndex == -1:
		try:
			photoFilePath = takenImagesDir+takenImages[imageIndex]
			photo = open(photoFilePath,'rb')
			tweet = statusfinder.getNextStatus()
			api.update_status_with_media(media=photo,status=tweet)
			# this is just a photo
			#api.update_status_with_media(media=photo)
			shutil.move(photoFilePath,sentImagesDir+takenImages[imageIndex])
			status = tweet
			success = True
			statusfinder.saveStatus(tweet)
		except TwythonError as e:
			message("Error")
			status = "Error Tweeting"
			updateScreen()
			success = False
			
	time.sleep(1)
	return success

def getRandomMessage():
	return "Sunday Funday"

def deletePhoto():
	global takenImagesDir
	global takenImages

	if imageIndex == -1:
		message("No photos to delete")
	else:
		os.remove(takenImagesDir + takenImages[imageIndex])
		message("Deleting photo")
	updateScreen()
	time.sleep(1)

def takePhoto():
	# take photo here
	ts = getTimeStamp()
	camera.capture(takenImagesDir + ts + ".jpg")
	message("Took photo: " + ts)
	updateScreen()
	time.sleep(1)

def nextPhoto():
	# load next photo in list
	global imageIndex
	if imageIndex >= 0:
		imageIndex = imageIndex + 1
		if imageIndex == len(takenImages):
			imageIndex = 0

	message("Next photo")
	updateScreen()
	time.sleep(1)

def background(color):
	global screen
	screen.fill(color)

def message(msg):
	global screen
	global font
	global mx
	global my
	text = font.render(msg, True, COLOR_WHITE)
	textPos = text.get_rect()
	textPos.left = mx
	textPos.top = my
	screen.blit(text, textPos)
	advanceMY()

def updateScreen():
	pygame.display.update()

def resetMXY():
	global mx
	global my
	mx = 5
	my = 5

def advanceMY():
	global my
	my = my + 30

# load image names from disk
def loadImages():
	global takenImagesDir
	global takenImages
	global imageIndex
	takenImages = os.listdir(takenImagesDir)
	if len(takenImages) == 0:
		imageIndex = -1
	elif imageIndex == -1:
		imageIndex = len(takenImages)-1
	elif imageIndex >= len(takenImages):
		imageIndex = len(takenImages)-1


def changeState(newState):
	global state
	
	state = newState	

	# transitional states: messages or activities
	if state == STATE_TAKE_PHOTO:
		takePhoto()
		state = STATE_DISPLAY
	
	if state == STATE_TWEET_PHOTO:
		tweetPhoto()
		state = STATE_STARTUP

	if state == STATE_DELETE_PHOTO:
		deletePhoto()
		state = STATE_DISPLAY
	
	if state == STATE_NEXT_PHOTO:
		nextPhoto()
		state = STATE_DISPLAY

	# display states	
	if state == STATE_STARTUP:
		stateStartup()

	elif state == STATE_DISPLAY:
		camera.stop_preview()
		stateDisplay()
	
	elif state == STATE_PREVIEW:
		statePreview()

	elif state == STATE_TWEET:
		stateTweet()


# startup
initGPIO()
initScreen()	
initTwitter()
stateStartup()

# main loop
done = False
with picamera.PiCamera() as camera:
	camera.resolution = (1280,720)

	while not done:
		eventType = getEvent()
		stateChanged = False
		if eventType == EVENT_QUIT:
			done = True
		elif not eventType == EVENT_NONE:
			oldState = state
			state = buttonPressed(state, eventType)
			
			if not oldState == state:
				changeState(state)


		


