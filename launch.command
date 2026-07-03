#!/bin/bash
# Launch the Tazos Collection Tracker.
cd "$(dirname "$0")"
exec python3 server.py
