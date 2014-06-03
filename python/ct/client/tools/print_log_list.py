#!/usr/bin/env python
"""Parse and print the list of logs, after validating signature."""


import base64
import hashlib
import json
import os
import sys

import gflags
import jsonschema
import M2Crypto

FLAGS = gflags.FLAGS

gflags.DEFINE_string("log_list", None, "Logs list file to parse and print.")
gflags.MarkFlagAsRequired("log_list")
gflags.DEFINE_string("signature", None, "Signature file over the list of logs.")
gflags.MarkFlagAsRequired("signature")
gflags.DEFINE_string("signer_key", None, "Public key of the log list signer.")
gflags.MarkFlagAsRequired("signer_key")
gflags.DEFINE_string("log_list_schema",
                     os.path.join(os.path.dirname(sys.argv[0]),
                                  'data', 'log_list_schema.json'),
                     "JSON schema for the list of logs.")
gflags.MarkFlagAsRequired("log_list_schema")


def is_log_list_valid(json_log_list, schema_file):
    try:
        jsonschema.validate(
            json_log_list,
            json.load(open(schema_file, "rb")))
        return True
    except jsonschema.exceptions.ValidationError as e:
        print e
        return False
    return False


def is_signature_valid(log_list_data, signature_file, public_key_file):
    loaded_pubkey = M2Crypto.RSA.load_pub_key(public_key_file)
    pubkey = M2Crypto.EVP.PKey()
    pubkey.assign_rsa(loaded_pubkey)
    pubkey.reset_context(md="sha256")
    pubkey.verify_init()
    pubkey.verify_update(log_list_data)
    return pubkey.verify_final(open(signature_file, "rb").read())


def print_formatted_log_list(json_log_list):
    operator_id_to_name = dict(
        [(o["id"], o["name"]) for o in json_log_list["operators"]])

    for log_info in json_log_list["logs"]:
        print "%s:" % log_info["description"]
        log_operators = [
            operator_id_to_name[i].encode("utf-8")
            for i in log_info["operated_by"]]
        print "  Operated by %s and has MMD of %f hours" % (
            ", ".join(log_operators),
            log_info["maximum_merge_delay"] / (60.0 ** 2))
        print "  At: %s" % (log_info["url"])
        key = base64.decodestring(log_info["key"])
        hasher = hashlib.sha256()
        hasher.update(key)
        key_hash = hasher.digest()
        print "  Key ID: %s" % (base64.encodestring(key_hash))


def run():
    with open(FLAGS.log_list, "rb") as f:
        json_data = f.read()

    if not is_signature_valid(json_data, FLAGS.signature, FLAGS.signer_key):
        print "ERROR: Signature over list of logs is not valid, not proceeding."
        sys.exit(1)

    parsed_json = json.loads(json_data)
    if not is_log_list_valid(parsed_json, FLAGS.log_list_schema):
        print "ERROR: Log list is signed but does not conform to the schema."
        sys.exit(2)
    print_formatted_log_list(parsed_json)


if __name__ == "__main__":
    sys.argv = FLAGS(sys.argv)
    run()