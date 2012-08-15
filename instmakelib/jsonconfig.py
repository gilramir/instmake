"""
Read a dictionary from a JSON file,
and add its contents to a Python dictionary.
"""

import json
import types

# These are the supported field names
# ===================================

# The name of the plugin (without ".py") for logging
# usage of instmake
CONFIG_USAGE_LOGGER = "usage-logger"

def update(caller_config, json_filename):
    # This will throw errors
    fh = open(json_filename)

    file_config = json.load(fh)

    fh.close()

    assert type(file_config) == types.DictType

    caller_config.update(file_config)
