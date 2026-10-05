#!/bin/sh
# usage: scripts/notify.sh "Title" "message"   (progress push to ntfy.sh topic build_thon)
curl -s -H "Title: $1" -d "$2" https://ntfy.sh/build_thon > /dev/null
