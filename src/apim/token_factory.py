import base64
import datetime
import hashlib
import hmac
import json
import os
import sys
if sys.version_info[0] >= 3:
    from urllib.parse import quote_plus
else:
    from urllib import quote_plus

import requests

from .utils import byteify, replace_env


def create_token_factory_from_file(instances_file):
    with open(instances_file, 'r') as json_file:
        json_instances = json.loads(json_file.read())
        return TokenFactory(replace_env(byteify(json_instances)))


class TokenFactory:
    API_VERSION = "?api-version=2015-09-15"

    def __init__(self, instances):
        self._instances = instances

    def get_sas_token(self, instance):
        return "SharedAccessSignature " + self.get_sas_token_internal(self._instances[instance]["id"], self._instances[instance]["key"])

    def get_scm_sas_token(self, instance):
        rest_token = self.get_sas_token(instance)
        
        git_access = requests.get(self.get_base_url(instance) + 'tenant/access/git' + self.get_api_version(),
                                  headers={'Authorization': rest_token})

        if requests.codes.ok != git_access.status_code:
            return git_access.text

        git_data = byteify(json.loads(git_access.text))

        if not git_data['enabled']:
            print("Enabling git repository...")
            enable_res = requests.patch(self.get_base_url(instance) + 'tenant/access/git' + self.get_api_version(),
                                        headers={'Authorization': rest_token},
                                        json={'enabled': True})
            if 204 != enable_res.status_code:
                print("Failed to enable git access!")
                return False
            return self.get_scm_sas_token(instance)

        return quote_plus(self.get_sas_token_internal(git_data['id'], git_data['primaryKey']))

    def get_admin_sso_link(self, instance):
        rest_token = self.get_sas_token(instance)
        
        sso_res = requests.post(self.get_base_url(instance) + 'users/1/generateSsoUrl' + self.get_api_version(),
                                headers={'Authorization': rest_token})
        if 200 != sso_res.status_code:
            print("Could not create SSO URL for administrator.")
            print(sso_res.text)
            raise RuntimeError("Could not create SSO URL for administrator")
        
        sso_json = byteify(json.loads(sso_res.text))
        return sso_json['value']

    def get_base_url(self, instance):
        check_url = self._instances[instance]["url"]
        if check_url.endswith('/'):
            return check_url
        return check_url + '/'
        
    def get_host(self, instance):
        return self._instances[instance]["host"]

    def get_scm_url(self, instance):
        return self._instances[instance]["scm"]

    def get_sas_token_internal(self, id_, key_):
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")

        data_to_sign = id_ + '\n' + expiry

        hmac512 = hmac.new(key_, data_to_sign, hashlib.sha512)
        sig = base64.b64encode(hmac512.digest())

        auth_header = "uid=" + id_ + "&ex=" + expiry + "&sn=" + sig
        
        return auth_header

    def get_api_version(self):
        return self.API_VERSION


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python token_factory.py <config dir> [sas|git|adminurl]")
        sys.exit(1)
    
    instances_json = os.path.join(sys.argv[1], 'instances.json')
    if not os.path.isfile(instances_json):
        print("Error: Could not find 'instances.json' in directory '" + sys.argv[1] + "'.")
        sys.exit(1)
    
    operation = ""
    arg = ""
    if len(sys.argv) >= 3:
        arg = sys.argv[2]
        if arg == "git":
            operation = "git"
        if arg == "adminurl":
            operation = "adminurl"
        if arg == "sas":
            operation = "sas"
    else:
        operation = "sas"
    
    if operation == "":
        print("Error: Unknown argument '" + arg + "'.")
        sys.exit(1)
    
    tf = create_token_factory_from_file(instances_json)
    if operation == "sas":
        print(tf.get_sas_token("apim"))
    if operation == "git":
        git_password = tf.get_scm_sas_token("apim")
        print("git clone https://apim:" + git_password + "@" + tf.get_scm_url("apim"))
        
    if operation == "adminurl":
        print(tf.get_admin_sso_link("apim"))
    sys.exit(0)
