"""
Read a dictionary from a JSON file,
and add its contents to a Python dictionary.
"""

import json
import types
from instmakelib import rtimport

INSTMAKE_SITE_DIR = "instmakesite"

# These are the supported field names
# ===================================

# The name of the plugin (without ".py") for logging
# usage of instmake
CONFIG_USAGE_LOGGER = "usage-logger"

# The name of the plugin (without ".py") for normalizing
# path names in the clidiff report.
CONFIG_CLIDIFF_NORMPATH = "clidiff-normpath"

def update(caller_config, json_filename):
    # This will throw errors
    fh = open(json_filename)

    file_config = json.load(fh)

    fh.close()

    assert type(file_config) == types.DictType

    caller_config.update(file_config)


def load_site_plugin(name):
    """Import a plugin from the instmakesite directory.
    The import can throw exceptions that the caller has to
    catch."""
    plugin_name = INSTMAKE_SITE_DIR + "." + name
    return rtimport.rtimport(plugin_name)

