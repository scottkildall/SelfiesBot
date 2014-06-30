#!/bin/sh
# launcher.sh: put in crontab, will navigate to home directory, this directory, executes python script then back home
# by Scott Kildall www.kildall.com

cd /
cd home/pi/selfiesbot
sudo python selfie.py
cd /
