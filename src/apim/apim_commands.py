import os
import tempfile
import shutil
import zipfile

import git

from . import apim_core


def apim_update(base_dir):
    if not base_dir.endswith(os.sep):
        base_dir = base_dir + os.sep
    print("Checking configuration...")

    apim = apim_core.create_azure_apim(base_dir)
    instance = 'apim'

    # Check for properties
    properties_file = os.path.join(base_dir, 'properties.json')
    if os.path.isfile(properties_file):
        if not apim.upsert_properties_from_file(instance, properties_file):
            print("Upserting properties failed.")
            return False
        print("Update of properties succeeded.")
    else:
        print("Skipping properties, could not find 'properties.json'.")
    
    # Check for certificates
    certificates_file = os.path.join(base_dir, 'certificates.json')
    if os.path.isfile(certificates_file):
        if not apim.upsert_certificates_from_file(instance, certificates_file):
            print("Upserting certificates failed.")
            return False
        print("Update of certificates succeeded.")
    else:
        print("Skipping certificates, could not find 'certificates.json'.")
        
    # Check for Swagger files
    swaggerfiles_file = os.path.join(base_dir, 'swaggerfiles.json')
    if os.path.isfile(swaggerfiles_file):
        if not apim.update_swagger_from_file(instance, swaggerfiles_file):
            print("Updating Swagger API definitions failed.")
            return False
        print("Update of APIs via Swagger definitions succeeded.")
    else:
        print("Skipping Swagger update, could not find 'swaggerfiles.json'.")
    
    # Room for more things (backends?)

    return True

def apim_extract(base_dir, target_zip):
    if not base_dir.endswith(os.sep):
        base_dir = base_dir + os.sep

    if target_zip.endswith('.zip'):
        target_zip = target_zip[:-4] # strip .zip

    print("Checking configuration...")

    config_files = [
        'instances.json',
        'properties.json',
        'certificates.json',
        'swaggerfiles.json',
        'docker_env.list'
    ]

    instance = "apim"

    apim = apim_core.create_azure_apim(base_dir)
    print("Telling APIm to store configuration to git...")
    if not apim.git_save(instance, 'master'):
        print("Failed.")
        return False

    # repo = git.Repo.clone_from('https://github.com/apisio/apis.io.git', '~/Temp/new_repo', branch='master')
    scm_user = 'apim'
    scm_password = apim.get_token_factory().get_scm_sas_token(instance)
    scm_host = apim.get_token_factory().get_scm_url(instance)

    git_temp = tempfile.mkdtemp()

    try:
        print("Cloning repository to temporary path...")
        print("Temp path: " + git_temp)
        apim_path = os.path.join(git_temp, 'azureapim.scm')
        repo = git.Repo.clone_from(
            'https://' + scm_user + ':' + scm_password + '@' + scm_host,
            apim_path
        )
        print("git clone done.")
        shutil.rmtree(os.path.join(apim_path, '.git')) # remove git folder

        for config_file in config_files:
            full_path = os.path.join(base_dir, config_file)
            if os.path.isfile(full_path):
                shutil.copyfile(full_path, os.path.join(git_temp, config_file))

        print("Creating archive.")
        shutil.make_archive(target_zip, format='zip', root_dir=git_temp)
        
    finally:
        shutil.rmtree(git_temp)

    print("Operation finished successfully.")
    return True

def apim_extract_properties(base_dir):
    instance = "apim"
    apim = apim_core.create_azure_apim(base_dir)
    properties_file = os.path.join(base_dir, 'properties_extracted.json')
    if not apim.extract_properties_to_file("apim", properties_file):
        print("Property extraction failed.")
        return False
    print("Property extraction succeeded.")
    return True
    
def apim_extract_certificates(base_dir):
    instance = "apim"
    apim = apim_core.create_azure_apim(base_dir)
    certificates_file = os.path.join(base_dir, 'certificates_extracted.json')
    if not apim.extract_certificates_to_file("apim", certificates_file):
        print("Certificate extraction failed.")
        return False
    print("Certificate extraction succeeded.")
    return True
    
def apim_extract_swaggerfiles(base_dir):
    instance = "apim"
    apim = apim_core.create_azure_apim(base_dir)
    swaggerfiles_file = os.path.join(base_dir, 'swaggerfiles_extracted.json')
    swaggerfiles_localdir = os.path.join(base_dir, 'local_swaggerfiles')
    if not os.path.exists(swaggerfiles_localdir):
        os.makedirs(swaggerfiles_localdir)
    if not apim.extract_swaggerfiles_to_file("apim", swaggerfiles_file, 'local_swaggerfiles'):
        print("Swaggerfiles extraction failed.")
        return False
    print("Swagger files extraction succeeded.")
    return True

def apim_deploy(source_zip):
    config_tmp = tempfile.mkdtemp()
    git_tmp = tempfile.mkdtemp()

    #print("Work in progress. Comment out to test."
    #return False

    try:
        # Extract ZIP file
        if not os.path.isfile(source_zip):
            print("Could not read source zip file '" + source_zip + "'.")
            return False
        
        print("Unzipping configuration file to '" + config_tmp + "'.")
        zip_file = zipfile.ZipFile(source_zip, 'r')
        try:
            zip_file.extractall(config_tmp)
        finally:
            zip_file.close()
        
        # Do an apim_update on the extracted files
        # Remove swaggerfiles.json; we don't want to do a Swagger update again
        swaggerfiles_json = os.path.join(config_tmp, 'swaggerfiles.json')
        if os.path.isfile(swaggerfiles_json):
            os.remove(swaggerfiles_json)
        print("Updating certificates and properties...")
        apim_update(config_tmp)
        
        # Save current config to git
        instance = "apim"

        apim = apim_core.create_azure_apim(config_tmp)
        print("Telling APIm to store configuration to git...")
        if not apim.git_save(instance, 'master'):
            print("Failed.")
            return False
        
        # Clone to local dir
        scm_user = 'apim'
        scm_password = apim.get_token_factory().get_scm_sas_token(instance)
        scm_host = apim.get_token_factory().get_scm_url(instance)
        
        print("Cloning repository to '" + git_tmp + "'.")
        repo = git.Repo.clone_from(
            'https://' + scm_user + ':' + scm_password + '@' + scm_host,
            git_tmp
        )
        print("git clone done.")
        
        # Overwrite config with content from ZIP file
        git_apim = os.path.join(git_tmp, 'api-management')
        config_apim = os.path.join(os.path.join(config_tmp, 'azureapim.scm'), 'api-management')
        shutil.rmtree(os.path.join(git_tmp, 'api-management'))
        shutil.copytree(config_apim, git_apim)
        
        # Push the changes to the APIm git repo
        print("Push changes to upstream repo.")
        git_repo = repo.git
        # Do we have differences?
        diffs = repo.index.diff(None)
        has_changes = False
        for diff in diffs:
            has_changes = True
            break
        if has_changes:
            git_repo.add(all=True)
            git_repo.commit(m='"Automatic push to git repository."')
            git_repo.push()
        
            # Deploy git configuration to upstream repo
            apim.git_deploy(instance, 'master')
        else:
            print("Remote repository is already up to date. No push needed.")
        
    finally:
        print("Cleaning up.")
        shutil.rmtree(config_tmp)
        #shutil.rmtree(git_tmp)
            
    return True
