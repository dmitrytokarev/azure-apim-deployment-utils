import sys

from . import apim_commands

if len(sys.argv) < 2:
    print("Usage:")
    print("   python apim_update.py <config dir>")
    sys.exit(1)

if not apim_commands.apim_update(sys.argv[1]):
    sys.exit(1)
    
sys.exit(0)
