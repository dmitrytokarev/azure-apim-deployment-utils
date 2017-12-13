import base64
import hashlib
import json
import os
import random
import time

import requests

from . import apim_openssl
from . import token_factory
from .utils import byteify, replace_env, resolve_file


def create_azure_apim(config_dir):
    instances_json = os.path.join(config_dir, 'instances.json')
    if not os.path.isfile(instances_json):
        print("*** ERROR")
        raise Exception("Could not find 'instances.json' in '" + config_dir + "'.")
        
    tf = token_factory.create_token_factory_from_file(instances_json)
    return AzureApim(tf, config_dir)

class AzureApim:
    def __init__(self, token_factory, config_dir):
        self._token_factory = token_factory
        self._base_config_dir = config_dir
        
    def git_save(self, instance, target_branch):
        return self.exec_async_operation(instance, 'tenant/configuration/save',
                                         {'branch': target_branch, 'force': True})
                                    
    def git_deploy(self, instance, source_branch):
        return self.exec_async_operation(instance, 'tenant/configuration/deploy',
                                         {'branch': source_branch, 'force': True})
    
    def git_validate(self, instance, source_branch):
        return self.exec_async_operation(instance, 'tenant/configuration/validate',
                                         {'branch': source_branch, 'force': True})
                                    
    def get_token_factory(self):
        return self._token_factory

    def exec_async_operation(self, instance, operation, json_payload):
        sas_token = self._token_factory.get_sas_token(instance)
        base_url = self._token_factory.get_base_url(instance)
        api_version = self._token_factory.get_api_version()

        save_req = requests.post(base_url + operation + api_version, 
            headers = {'Authorization': sas_token, 'Content-Type': 'application/json' },
            json = json_payload)

        if 202 != save_req.status_code:
            print("Failed to execute operation.")
            print("Return Code: " + str(save_req.status_code))
            print(save_req.text)
        
            return False

        location = save_req.headers['Location']
        print(location)

        ready = False

        while not ready:
            time.sleep(5)
            status_req = requests.get(location, headers={'Authorization': sas_token})
        
            if (status_req.status_code > 299):
                print("Fetching the status of the process failed:")
                print(status_req.text)
                print("Status Code: " + str(status_req.status_code))

                return False

            status_json = byteify(json.loads(status_req.text))
            statusString = status_json['status']

            print("Operation Status: " + statusString)

            if statusString == "InProgress":
                continue
            if statusString == "Succeeded":
                ready = True
                break
            if statusString == "Failed":
                print("Operation failed! See status text for more information:")
            else:
                print("Unexpected status string: '" + statusString + "'. Exiting.")
            print(status_req.text)
            return False
        return True

    def upsert_certificates_from_file(self, instance, certificates_file):
        with open(self.__resolve_file(certificates_file), 'r') as json_file:
            json_certificates = replace_env(byteify(json.loads(json_file.read())))
        return self.upsert_certificates(instance, json_certificates['certificates'])


    def upsert_certificates(self, instance, certificate_infos):
        sas_token = self._token_factory.get_sas_token(instance)
        base_url = self._token_factory.get_base_url(instance)
        api_version = self._token_factory.get_api_version()

        sha1_bucket = {}
        for certificate_info in certificate_infos:
            fingerprint = apim_openssl.pkcs12_fingerprint_local(certificate_info['fileName'], certificate_info['password'], self._base_config_dir)
            sha1_bucket[fingerprint] = certificate_info

        certs_res = requests.get(base_url + 'certificates' + api_version,
                                headers = {'Authorization': sas_token})
        if 200 != certs_res.status_code:
            print(certs_res.text)
            return False

        fingerprint_bucket = {}
        certs_json = byteify(json.loads(certs_res.text))
        for cert in certs_json['value']:
            print("Certificate: " + cert['id'] + ", " + cert[u'subject'])
            thumbprint = cert['thumbprint']
            cid_string = cert['id'] # /certificates/{unique id}
            cid = cid_string[cid_string.index('/', 2) + 1:] # /certificates/{unique id} -- pick unique id
            print("cid: " + cid)
            fingerprint_bucket[thumbprint] = cid

        print(fingerprint_bucket)

        for fingerprint in fingerprint_bucket:
            if not fingerprint in sha1_bucket:
                cid = fingerprint_bucket[fingerprint]
                print("Will delete cert with fingerprint '" + fingerprint + "' (cid " + cid + ").")
                if not self.__delete_certificate(base_url, sas_token, api_version, cid):
                    return False
                print("Deleted cid '" + cid + "'.")

        for cert in sha1_bucket:
            if not fingerprint in fingerprint_bucket:
                print("Will add cert '" + sha1_bucket[cert]['fileName'] + "' (fingerprint(" + cert + ")")
                if not self.__add_certificate(base_url, sas_token, api_version, sha1_bucket[fingerprint], fingerprint):
                    return False
                print("Added cert '" + sha1_bucket[fingerprint]['fileName'] + "'")
            else:
                print("Found certificate with fingerprint '" + fingerprint + "'.")

        return True

    def extract_certificates_to_file(self, instance, certificates_file):
        sas_token = self._token_factory.get_sas_token(instance)
        base_url = self._token_factory.get_base_url(instance)
        api_version = self._token_factory.get_api_version()

        cert_res = requests.get(base_url + 'certificates' + api_version,
                                headers = {'Authorization': sas_token})
        if 200 != cert_res.status_code:
            print("Certificate extraction failed!")
            print(cert_res.text)
            return False

        cert_json = byteify(json.loads(cert_res.text))
        certs_file_json = { 'certificates': [] }
        cert_list = certs_file_json['certificates']
        for cert in cert_json['value']:
            cert_list.append({
                'fileName': cert['subject'],
                'password': cert['thumbprint']
            })
        with open (certificates_file, 'w') as outfile:
            json.dump(certs_file_json, outfile, indent=4)

        return True

    def __delete_certificate(self, base_url, sas_token, api_version, cid):
        cert_del_res = requests.delete(base_url + 'certificates/' + cid + api_version,
                                    headers = {'Authorization': sas_token, 'If-Match': '*'})
        if (204 == cert_del_res.status_code
            or 200 == cert_del_res.status_code):
            return True

        print("Deletion of certificate failed!")
        print(cert_del_res.text)
        return False

    def __file_base64(self, file_name):
        with open(self.__resolve_file(file_name), 'rb') as in_file:
            return base64.b64encode(in_file.read())

    def __add_certificate(self, base_url, sas_token, api_version, cert_info, fingerprint):
        cid = '%030x' % random.randrange(16**30)
        add_cert_body = {
            'data': self.__file_base64(cert_info['fileName']),
            'password': cert_info['password']
        }
        cert_add_res = requests.put(base_url + 'certificates/' + cid + api_version,
                                    headers = {'Authorization': sas_token},
                                    json = add_cert_body)
        if 201 != cert_add_res.status_code:
            print("Adding certificate failed!")
            print(cert_add_res.text)
            return False
        return True

    def update_swagger_from_file(self, instance, swaggerfiles_file):
        with open(swaggerfiles_file, 'r') as json_file:
            swaggerfiles = replace_env(byteify(json.loads(json_file.read())))
        return self.update_swagger(instance, swaggerfiles)

    def update_swagger(self, instance, swaggerfiles):
        sas_token = self._token_factory.get_sas_token(instance)
        base_url = self._token_factory.get_base_url(instance)
        api_version = self._token_factory.get_api_version()
        # First, find the ids of the APIs.
        api_res = requests.get(base_url + 'apis' + api_version,
                               headers = {'Authorization': sas_token})
        if 200 != api_res.status_code:
            print("Could not retrieve API information (/api endpoint).")
            print(api_res.text)
            return False

        apis_json = byteify(json.loads(api_res.text))

        api_id_bag = {}
        api_bag = {}
        for api_def in apis_json['value']:
            api_url = api_def['serviceUrl']
            api_id_url = api_def['id'] # /apis/3498734a389f7bc83749837493
            api_id = api_id_url[api_id_url.index('/', 2) + 1:]
            api_name = api_def['name']
            print("Found API '" + api_name + "' (id " + api_id + ").")
            api_id_bag[api_url] = api_id
            api_bag[api_url] = api_def

        for swaggerfile in swaggerfiles['swaggerFiles']:
            print("Updating '" + swaggerfile['swagger'] + "'.")
            swagger_url = swaggerfile['serviceUrl']
            if swagger_url not in api_id_bag:
                print("Could not find serviceUrl '" + swagger_url + "'. Is it a new API? Import it once first in the Web UI.")
                return False

            api_id = api_id_bag[swagger_url]
            swagger_json = self.__load_swagger(instance, swaggerfile['swagger'])
            swag_res = requests.put(base_url + 'apis/' + api_id + api_version + '&import=true',
                                    headers={'Authorization': sas_token,
                                             'If-Match': '*',
                                             'Content-Type': 'application/vnd.swagger.doc+json'},
                                    json = swagger_json)
            if 204 != swag_res.status_code:
                print("Updating the API did not succeed.")
                print(swag_res.status_code)
                return False
            # Re-update the API definition because the Swagger import overwrites the serviceUrl
            api_res = requests.patch(base_url + 'apis/' + api_id + api_version,
                                     headers = {'Authorization': sas_token,
                                                'If-Match': '*'},
                                     json = api_bag[swagger_url])
            if 204 != api_res.status_code:
                print("Could not update serviceUrl (next update will break!).")
                print(api_res.text)
                return False
            print("Update succeeded.")

        return True

    def __load_swagger(self, instance, swagger_file):
        with open(self.__resolve_file(swagger_file), 'r') as json_file:
            swagger_json = byteify(json.loads(json_file.read()))

        # Mandatory for importing swagger
        swagger_json['host'] = self._token_factory.get_host(instance)
        if 'basePath' not in swagger_json:
            raise LookupError("Could not find 'basePath' property.")
        if 'schemes' not in swagger_json:
            raise LookupError("Could not find 'schemes' property.")
        return swagger_json

    def export_swagger_files(self, instance, target_dir):
        sas_token = self._token_factory.get_sas_token(instance)
        base_url = self._token_factory.get_base_url(instance)
        api_version = self._token_factory.get_api_version()

        apis_res = requests.get(base_url + 'apis' + api_version,
                                headers = {'Authorization': sas_token})
        if 200 != apis_res.status_code:
            print("Could not retrieve APIs.")
            print(apis_res.text)
            return False

        apis_json = byteify(json.loads(apis_res.text))
        for api_def in apis_json['value']:
            api_url = api_def['id']

            swagger_res = requests.get(base_url + api_url[1:] + api_version + '&export=true',
                                       headers={'Authorization': sas_token,
                                                'Accept': 'application/vnd.swagger.doc+json'})
            if 200 != swagger_res.status_code:
                print("Could not export Swagger definition.")
                print(swagger_res.text)
                return False

            swagger = json.loads(swagger_res.text)
            id_name = swagger['basePath'].replace('/', '_')
            if (id_name.startswith('_')):
                id_name = id_name[1:]
            sep = ''
            if not target_dir.endswith(os.sep):
                sep = os.sep
            with open(target_dir + sep + id_name + ".json", 'w') as outfile:
                json.dump(swagger, outfile, indent=4)

        return True

    def extract_swaggerfiles_to_file(self, instance, swaggerfiles_file, swaggerfiles_dir):
        sas_token = self._token_factory.get_sas_token(instance)
        base_url = self._token_factory.get_base_url(instance)
        api_version = self._token_factory.get_api_version()

        apis_res = requests.get(base_url + 'apis' + api_version,
                                headers = {'Authorization': sas_token})
        if 200 != apis_res.status_code:
            print("Could not retrieve APIs.")
            print(apis_res.text)
            return False

        swaggerfiles_json = {
            'swaggerFiles': []
        }
        swaggerfiles_list = swaggerfiles_json['swaggerFiles']
        apis_json = byteify(json.loads(apis_res.text))
        for api_def in apis_json['value']:
            api_url = api_def['id']

            swagger_res = requests.get(base_url + api_url[1:] + api_version + '&export=true',
                                       headers={'Authorization': sas_token,
                                                'Accept': 'application/vnd.swagger.doc+json'})
            if (200 != swagger_res.status_code):
                print("Could not export Swagger definition.")
                print(swagger_res.text)
                return False

            swagger = json.loads(swagger_res.text)
            id_name = swagger['basePath'].replace('/', '_')
            if id_name.startswith('_'):
                id_name = id_name[1:]

            target_dir = self._base_config_dir
            if swaggerfiles_dir:
                target_dir = os.path.join(target_dir, swaggerfiles_dir)
            target_file = id_name + '.json'
            with open(os.path.join(target_dir, target_file), 'w') as outfile:
                json.dump(swagger, outfile, indent=4)

            local_file_name = target_file
            if swaggerfiles_dir:
                local_file_name = os.path.join(swaggerfiles_dir, target_file)

            swaggerfiles_list.append({
                'serviceUrl': api_def['serviceUrl'],
                'swagger': local_file_name
            })

        with open(swaggerfiles_file, 'w') as outfile:
            json.dump(swaggerfiles_json, outfile, indent=4)

        return True

    def extract_properties(self, instance):
        sas_token = self._token_factory.get_sas_token(instance)
        base_url = self._token_factory.get_base_url(instance)
        api_version = self._token_factory.get_api_version()

        prop_get = requests.get(base_url + 'properties' + api_version,
                                headers = {'Authorization': sas_token})
        if 200 != prop_get.status_code:
            print("Could not get properties from '" + instance + "'.")
            print(prop_get.text)
            return False

        props_json = byteify(json.loads(prop_get.text))
        props = {}
        for prop in props_json['value']:
            props[prop['name']] = {
                "value": prop['value'],
                "tags": prop['tags'],
                "secret": prop['secret']
            }
        return props

    def extract_properties_to_file(self, instance, file_name):
        props = self.extract_properties(instance)

        with open(file_name, 'w') as json_file:
            json.dump(props, json_file, indent = 4)
        return True

    def upsert_properties_from_file(self, instance, properties_file):
        with open(self.__resolve_file(properties_file), 'r') as json_file:
            json_properties = replace_env(byteify(json.loads(json_file.read())))
        return self.upsert_properties(instance, json_properties)

    def upsert_properties(self, instance, properties):
        sas_token = self._token_factory.get_sas_token(instance)
        base_url = self._token_factory.get_base_url(instance)
        api_version = self._token_factory.get_api_version()

        prop_get = requests.get(base_url + 'properties' + api_version,
                                headers = {'Authorization': sas_token})
        if 200 != prop_get.status_code:
            print("Could not get properties from '" + instance + "'.")
            print(prop_get.text)
            return False

        props_json = byteify(json.loads(prop_get.text))

        prop_id_bag = {}
        for prop in props_json['value']:
            prop_id = prop['id']
            prop_id_bag[prop['name']] = prop_id[prop_id.index('/', 2) + 1:]

        for prop_name in properties:
            if prop_name in prop_id_bag:
                print("Updating '" + prop_name + "'")
                if not self.__update_property(base_url, sas_token, api_version, prop_name, prop_id_bag[prop_name], properties[prop_name]):
                    return False
            else:
                print("Inserting '" + prop_name + "'")
                if not self.__insert_property(base_url, sas_token, api_version, prop_name, properties[prop_name]):
                    return False

        for prop in props_json['value']:
            prop_name = prop['name']
            if not prop_name in properties:
                # Property in APIm, not in JSON, delete it
                print("Deleting property '" + prop_name + "'.")
                if not self.__delete_property(base_url, sas_token, api_version, prop_name, prop_id_bag[prop_name]):
                    return False

        return True

    def __update_property(self, base_url, sas_token, api_version, prop_name, prop_id, properties):
        prop_res = requests.patch(base_url + 'properties/' + prop_id + api_version,
                                  headers = {'Authorization': sas_token, 'If-Match': '*'},
                                  json = {
                                      'name': prop_name,
                                      'value': properties['value'],
                                      'tags': properties['tags'],
                                      'secret': properties['secret']
                                  })
        if (200 != prop_res.status_code
            and 204 != prop_res.status_code):
            print("Update of property '" + prop_name + "' failed.")
            print(prop_res.text)
            return False
        print("Successfully updated property '" + prop_name + "' (id " + prop_id + ").")
        return True

    def __insert_property(self, base_url, sas_token, api_version, prop_name, properties):
        # We need a random ID to PUT the property to.
        prop_id = '%030x' % random.randrange(16**30)
        prop_res = requests.put(base_url + 'properties/' + prop_id + api_version,
                                headers = {'Authorization': sas_token},
                                json = {
                                    'name': prop_name,
                                    'value': properties['value'],
                                    'tags': properties['tags'],
                                    'secret': properties['secret']
                                })
        if (200 != prop_res.status_code
            and 201 != prop_res.status_code):
            print("Insert of property '" + prop_name + "' failed.")
            print(prop_res.text)
            return False
        print("Successfully inserted property '" + prop_name + "' (id " + prop_id + ").")
        return True

    def __delete_property(self, base_url, sas_token, api_version, prop_name, prop_id):
        prop_res = requests.delete(base_url + 'properties/' + prop_id + api_version,
                                   headers={'Authorization': sas_token, 'If-Match': '*'})
        if 204 != prop_res.status_code and 200 != prop_res.status_code:
            print("Deletion of property '" + prop_name + "' (id " + prop_id + ") failed.")
            print(prop_res.text)
            return False
        print("Successfully deleted property '" + prop_name + "' (id " + prop_id + ").")
        return True

    def __hexmd5(self, file_name):
        hasher = hashlib.md5()
        with open(self.__resolve_file(file_name), 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def __resolve_file(self, file_name):
        return resolve_file(file_name, self._base_config_dir)
