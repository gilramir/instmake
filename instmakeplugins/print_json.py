"""
Print a list of records, with each record being a dictionary,
in JSON format.
"""
import sys
import pprint
import json

# Fields that are always present
FIELD_PID = "pid"                           # string
FIELD_PPID = "ppid"                         # string, or None (for root record)
FIELD_CWD = "cwd"                           # string
FIELD_CMDLINE = "cmdline"                   # string
FIELD_RETVAL = "retval"                     # numeric
FIELD_REAL_TIME = "real-time"               # numeric
FIELD_USER_TIME = "user-time"               # numeric
FIELD_SYS_TIME = "sys-time"                 # numeric
FIELD_CPU_TIME = "cpu-time"                 # numeric
FIELD_REAL_START = "real-start"             # numeric
FIELD_REAL_END = "real-end"                 # numeric

# Optional fields
FIELD_TOOL = "tool"                         # string
FIELD_MAKE_TARGET = "make-target"           # string
FIELD_MAKEFILE_NAME = "makefile-name"       # string
FIELD_MAKEFILE_LINENO = "makefile-lineno"   # string
FIELD_AUDIT_OK = "audit-ok"                 # True/False
FIELD_INPUT_FILES = "input-files"           # list
FIELD_OUTPUT_FILES = "output-files"         # list
FIELD_ENV_VARS = "env-vars"                 # dictionary
FIELD_OPEN_FDS = "open-fds"                 # list
FIELD_MAKE_VARS = "make-vars"               # dictionary
FIELD_MAKE_VAR_ORIGINS = "make-var-origins" # dictionary
FIELD_APP_INST_FIELDS = "app-inst-fields"   # dictionary

description = "Print as JSON list of dictionaries"

# This is exactly why the print plugins need to be converted to
# classes. This global variable is used as an indicator that
# the first record has been printed, so that we can control
# how many commas we print. Unlike Python, JSON lists cannot
# have a trailing comma.
PRINTED_FIRST = False

def PrintHeader():
    # Print the start of the list, with no new-line
    print "[",

def PrintFooter():
    # Print the end of the list, with a new-line
    print "]"

def Print(self, fh=sys.stdout, indent=0, vspace=1):

    global PRINTED_FIRST
    if PRINTED_FIRST:
        print ",\n"
    PRINTED_FIRST = True

    fields = {}

    # First, all the fields that are always present
    fields[FIELD_PID] = self.pid

    # JSON will show null instead of "None", so we
    # set the "None" string here.
    if self.ppid == None:
        fields[FIELD_PPID] = "None"
    else:
        fields[FIELD_PPID] = self.ppid
    fields[FIELD_CWD] = self.cwd
    fields[FIELD_RETVAL] = self.retval

    fields[FIELD_REAL_TIME] = self.diff_times[self.REAL_TIME]
    fields[FIELD_USER_TIME] = self.diff_times[self.USER_TIME]
    fields[FIELD_SYS_TIME] = self.diff_times[self.SYS_TIME]
    fields[FIELD_CPU_TIME] = self.diff_times[self.CPU_TIME]

    fields[FIELD_REAL_START] = self.times_start[self.REAL_TIME]
    fields[FIELD_REAL_END] = self.times_end[self.REAL_TIME]

    fields[FIELD_CMDLINE] = self.cmdline

    # Add the optional fields

    if self.tool:
        fields[FIELD_TOOL] = self.tool

    if self.make_target:
        fields[FIELD_MAKE_TARGET] = self.make_target

    if self.makefile_filename:
        fields[FIELD_MAKEFILE_NAME] = self.makefile_filename

    if self.makefile_lineno:
        # instmake recorded this from the environment,
        # as a string. Let's do the conversion to an integer, if possible.
        try:
            lineno = int(self.makefile_lineno, 10)
        except ValueError:
            lineno = -1
        fields[FIELD_MAKEFILE_LINENO] = lineno

    if self.audit_ok != None:
        fields[FIELD_AUDIT_OK] = self.audit_ok

    if self.input_files != None:
        fields[FIELD_INPUT_FILES] = self.input_files

    if self.output_files != None:
        fields[FIELD_OUTPUT_FILES] = self.output_files

    # Environment variables
    if self.env_vars:
        fields[FIELD_ENV_VARS] = self.env_vars

    # Open file descriptors
    if self.open_fds != None:
        fields[FIELD_OPEN_FDS] = self.open_fds

    # Make variables
    if self.make_vars:
        fields[FIELD_MAKE_VARS] = self.make_vars

    if self.make_var_origins:
        fields[FIELD_MAKE_VAR_ORIGINS] = self.make_var_origins

    # Application-instrumentation fields
    if self.app_inst != None:
        fields[FIELD_APP_INST_FIELDS] = self.app_inst

    json_text = json.dumps(fields, indent=2)
    print json_text,
