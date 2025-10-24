#!/bin/bash

# Open Google Chrome with remote debugging enabled on port 9222
open -a "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="$HOME/Library/Application Support/Google/Chrome/RemoteProfile"