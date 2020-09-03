#!/bin/bash

URL=http://localhost:5000

clear
# Bad WAVE file
curl -v ${URL}/post -F "name=@OUT.wav"

# Good wave files
curl -v ${URL}/post --data-binary @example1.wav
curl ${URL}/post -F "name=@wav16.wav"
curl ${URL}/post --data-binary @wav16.wav

curl -v ${URL}/download?name=wav16.wav > /tmp/OUT
md5sum wav16.wav /tmp/OUT

# List options
curl  ${URL}/list
curl  ${URL}/list?maxduration=30

# Info options
curl  ${URL}/info?name=wav16.wav
