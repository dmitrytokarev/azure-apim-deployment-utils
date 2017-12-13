import os
import tempfile
import shutil
import sys

if len(sys.argv) < 2:
    print("Usage:")
    print("  python create_dist.py <version>")
    sys.exit(1)

version = sys.argv[1]

try:
    temp_dir = tempfile.mkdtemp()
    print("Using temporary directory: " + temp_dir)
    target_dir = os.path.join(temp_dir, 'azure-apim-deployment-utils')
    # os.makedirs(target_dir)
    
    shutil.copytree(os.path.join('..', 'apim'), target_dir, ignore=shutil.ignore_patterns('*.pyc', 'tmp*', '.DS_*', '.gitignore'))
    
    target_zip_dir = os.path.join(os.path.join('..', '..'), 'bin')
    target_zip_file = os.path.join(target_zip_dir, 'azure-apim-deployment-utils-' + version)
    shutil.make_archive(target_zip_file, format='zip', root_dir=temp_dir)
    print("Created '" + target_zip_file + ".zip'.")
    
finally:
    shutil.rmtree(temp_dir)

try:
    temp_dir = tempfile.mkdtemp()
    print("Using temporary directory: " + temp_dir)
    target_dir = os.path.join(temp_dir, 'sample-repo')
    
    shutil.copytree(
        os.path.join(os.path.join('..', '..'), 'sample-repo'), 
        target_dir,
        ignore=shutil.ignore_patterns('.DS_*', '.gitignore'))
        
    target_zip_dir = os.path.join(os.path.join('..', '..'), 'bin')
    target_zip_file = os.path.join(target_zip_dir, 'azure-apim-deployment-utils-sample-repo-' + version)
    shutil.make_archive(target_zip_file, format='zip', root_dir=target_dir)
    print("Created '" + target_zip_file + ".zip'.")
finally:
    shutil.rmtree(temp_dir)

sys.exit(0)
