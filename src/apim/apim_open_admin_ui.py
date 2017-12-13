import os
import sys
import webbrowser

from . import token_factory


def open_admin_ui(base_dir, instance):
    instances_json = os.path.join(base_dir, 'instances.json')
    tf = token_factory.create_token_factory_from_file(instances_json)
    sso_url = tf.get_admin_sso_link(instance)
    webbrowser.open(sso_url)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python apim_open_admin_ui.py <config dir> <instance>")
        print()
        print("  If <instance> is not supplied, 'apim' is assumed.")
        sys.exit(1)

    instance = 'apim'
    if len(sys.argv) >= 3:
        instance = sys.argv[2]

    open_admin_ui(sys.argv[1], instance)
