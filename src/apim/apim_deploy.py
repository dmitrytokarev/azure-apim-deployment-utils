import sys

from . import apim_commands

if len(sys.argv) < 2:
    print("Usage:")
    print("   python apim_deploy.py <source zip>")
    sys.exit(1)

if not apim_commands.apim_deploy(sys.argv[1]):
    sys.exit(1)
    
sys.exit(0)
