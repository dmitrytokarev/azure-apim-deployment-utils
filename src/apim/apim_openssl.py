import OpenSSL
import sys

from .utils import resolve_file


def pkcs12_fingerprint(pfx_file, password):
    with open(pfx_file, 'rb') as in_file:
        pkcs12 = OpenSSL.crypto.load_pkcs12(in_file.read(), password)
    x509 = pkcs12.get_certificate()
    sha1_fingerprint = x509.digest('sha1')
    return sha1_fingerprint.replace(':', '')


def pkcs12_fingerprint_local(pfx_file, password, base_dir):
    return pkcs12_fingerprint(resolve_file(pfx_file, base_dir), password)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("   python apim_openssl.py <pkcs#12 file> <password> [<config dir>]")
        sys.exit(1)

    if len(sys.argv) == 3:
        print(pkcs12_fingerprint(sys.argv[1], sys.argv[2]))
    else:
        print(pkcs12_fingerprint_local(sys.argv[1], sys.argv[2], sys.argv[3]))
