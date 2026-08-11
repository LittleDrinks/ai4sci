#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 [-F <file>] [-D <directory>]"
    echo "  -F  Path to a single encrypted .zip file"
    echo "  -D  Path to a directory containing encrypted .zip files"
    exit 1
}

decrypt_file() {
    local zipfile="$1"
    local outfile="${zipfile%.zip}.json"

    python3 -c "
import json, base64, sys, zipfile
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

zf = zipfile.ZipFile('$zipfile', 'r')
name = zf.namelist()[0]
encrypted_data = json.loads(zf.read(name))
zf.close()

salt = base64.b64decode(encrypted_data['salt'].encode('utf-8'))
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
key = base64.urlsafe_b64encode(kdf.derive(b'hal1234'))
cipher = Fernet(key)

ct = base64.b64decode(encrypted_data['encrypted_data'].encode('utf-8'))
plaintext = cipher.decrypt(ct)
result = json.loads(plaintext.decode('utf-8'))

with open('$outfile', 'w') as f:
    json.dump(result, f, indent=2)
"
    echo "Decrypted: $zipfile -> $outfile"
}

FILE=""
DIR=""

while getopts "F:D:" opt; do
    case $opt in
        F) FILE="$OPTARG" ;;
        D) DIR="$OPTARG" ;;
        *) usage ;;
    esac
done

if [[ -z "$FILE" && -z "$DIR" ]]; then
    usage
fi

if [[ -n "$FILE" && -n "$DIR" ]]; then
    echo "Error: provide either -F or -D, not both" >&2
    exit 1
fi

if [[ -n "$FILE" ]]; then
    if [[ ! -f "$FILE" ]]; then
        echo "Error: file not found: $FILE" >&2
        exit 1
    fi
    decrypt_file "$FILE"
else
    if [[ ! -d "$DIR" ]]; then
        echo "Error: directory not found: $DIR" >&2
        exit 1
    fi
    shopt -s nullglob
    zips=("$DIR"/*.zip)
    if [[ ${#zips[@]} -eq 0 ]]; then
        echo "No .zip files found in $DIR"
        exit 0
    fi
    for f in "${zips[@]}"; do
        decrypt_file "$f" || echo "Failed: $f" >&2
    done
fi

echo "Done."
