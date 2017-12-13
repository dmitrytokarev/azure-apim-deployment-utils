import sys

from . import apim_commands

if len(sys.argv) < 3:
    print("Usage:")
    print("   python apim_extract.py <config dir> <target zip>")
    sys.exit(1)

if not apim_commands.apim_extract(sys.argv[1], sys.argv[2]):
    sys.exit(1)
    
sys.exit(0)
