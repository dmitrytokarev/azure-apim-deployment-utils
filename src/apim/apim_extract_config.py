import sys

from . import apim_commands

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python apim_extract_config.py <config dir> [list of <all|swagger|properties|certificates>]")
        sys.exit(1)
    
    base_dir = sys.argv[1]
    
    do_swagger = False
    do_properties = False
    do_certificates = False
    
    index = 2
    while index < len(sys.argv):
        do = sys.argv[index]
        if "all" == do or "swagger" == do:
            do_swagger = True
        if "all" == do or "properties" == do:
            do_properties = True
        if "all" == do or "certificates" == do:
            do_certificates = True
        index += 1
    
    if do_properties:
        if not apim_commands.apim_extract_properties(base_dir):
            sys.exit(1)
    if do_certificates:
        if not apim_commands.apim_extract_certificates(base_dir):
            sys.exit(1)
    if do_swagger:
        if not apim_commands.apim_extract_swaggerfiles(base_dir):
            sys.exit(1)

    sys.exit(0)
