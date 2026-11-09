#!/bin/sh
# usage: put.sh <file> <content-type> <url>
curl -s -o /dev/null -w "%{http_code}" -X PUT -H "Content-Type: $2" -H "If-None-Match: *" --data-binary @"$1" "$3"
echo " $1"
