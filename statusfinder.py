#! /user/bin/env python
import random
import datetime

def getRandomStatus():
	s = readStatusStrings()
	return  s[random.randint(0,len(s)-1)].rstrip()

def getNextStatus(): 
	s = readStatusStrings()
	last = getLastStatus()

	# iterate through array to find next tweet
	save = False
	next = s[0]
	if last:
		for line in s:
			if save == True:
				next = line
				save = False
			elif line == last:
				save = True

	saveLastStatus(next)
	return next

def saveStatus(s):	
	# save all transmitted tweets, just for sake of recording
	f = open("sent.txt", "a")
	f.write(s)
	f.write(" | ")
	f.write(get_timestamp())
	f.write("\n")
	f.close()


def readStatusStrings():
	# array of strings
	f = open( "status.txt", "r" )
	s = []
	for line in f:
		s.append( line.rstrip('\n') )
	f.close()
	return s

def getLastStatus():
	# grab the last quote
	f = open("laststatus.txt", "r")
	last = f.read()
	f.close
	last = last.rstrip('\n')
	return last

def saveLastStatus(s):
	# grab the last quote
	f = open("laststatus.txt", "w")
	f.write(s)
	f.close()

# returns our custom timestamp for logging
def get_timestamp():
	return datetime.datetime.today().strftime("%B %d %Y %H:%M")

