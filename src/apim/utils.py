import os
import sys
if sys.version_info[0] >= 3:
    unicode = str


def byteify(input):
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.items()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


def replace_env(input):
    if isinstance(input, dict):
        return {replace_env(key): replace_env(value)
                for key, value in input.items()}
    elif isinstance(input, list):
        return [replace_env(element) for element in input]
    elif isinstance(input, str):
        if input.startswith('$'):
            env_name = input[1:] # strip $
            return os.environ[env_name]
        return input
    else:
        return input


def resolve_file(file_name, base_dir):
    if os.path.isfile(file_name):
        return file_name
    
    joint = os.path.join(base_dir, file_name)
    if os.path.isfile(joint):
        return joint

    # Docker scenario
    if os.path.exists('/apim'):
        joint = os.path.join('/apim', file_name)
        if os.path.isfile(joint):
            return joint

    raise Exception("File not found: " + file_name)
