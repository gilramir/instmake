# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Report multiple writes of the same file.
"""

import getopt
import sys
from instmakelib import pysets
from instmakelib import imlib
from instmakelib import instmake_log as LOG
from instmakelib import climanager

description = "Report multiple writes to the same file (can use clearaudit info)."

def usage():
    print "mwrite: [file ...]", description
    print "\t--filenames    : show only filenames, not instmake records."
    print
    print "If one or more files are given on the command line, only the"
    print "records for that file (or those files) are shown. If no files"
    print "are given on the command-line, records for all files that are"
    print "written-to multiple times are shown."
    print
    print "If clearaudit data is available, it is used."
    print "Otherwise, CLI plugins are used to determine output files."
    print "CLI plugins are much less accurate than clearaudit data."

def report(log_file_names, args):

    # Get the single log file name
    if len(log_file_names) != 1:
        sys.exit("'mwrite' report uses one log file.")
    else:
        log_file_name = log_file_names[0]

    optstring = ""
    longopts = ["filenames"]

    SHOW_RECORDS = 1

    # Parse our options (currently, none)
    try:
        opts, only_filenames = getopt.getopt(args, optstring, longopts)
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for opt, arg in opts:
        if opt == "--filenames":
            SHOW_RECORDS = 0
        else:
            assert 0, "%s option not handled." % (opt,)

    # Open the log file
    log = LOG.LogFile(log_file_name)

    run(log, SHOW_RECORDS, only_filenames)


def mk_recipe_invocation_key(rec):
    if not rec.make_target:
        return None
    return rec.ppid + "|" + rec.make_target

def run(log, SHOW_RECORDS, only_filenames):
    cli_plugins = climanager.CLIManager()

    # Read the log records
    # We'll group them into "recipe invocations", where a unique recipe
    # invocation is defined as PPID + TARGET
    recipe_invocation_records = {}

    while 1:
        try:
            rec = log.read_record()
        except EOFError:
            log.close()
            break

        key = mk_recipe_invocation_key(rec)
        if key:
            records = recipe_invocation_records.setdefault(key, [])
            records.append(rec)

    # For each recipe invocation, merge multiple records into a single record.
    # Then take the records and sort them by their outputs.
    recs_by_output = {}

    for (ri_key, ri_records) in recipe_invocation_records.items():
        if len(ri_records) > 1:

            # Sort then by the time they started
            ri_records.sort(imlib.cmp_real_time_start)

            first_record = ri_records[0]

            # Determine the set of input and output files.
            input_set = pysets.SetClass()
            output_set = pysets.SetClass()

            # Gather data from all records in this group
            for rec in ri_records:

                # Accumulate the output files
                # clearaudit information?
                if rec.output_files != None:
                    output_set.add_items(rec.output_files)
                else:
                    # No? Try parsing the command-line.
                    cliparser = cli_plugins.ParseRecord(rec)
                    if cliparser:
                        outputs = cliparser.Outputs()
                        output_set.add_items(outputs)

                # Accumulate the input files
                # clearaudit information?
                if rec.input_files != None:
                    input_set.add_items(rec.input_files)


            # Modify 'first_record' so that it has characteristics
            # of all the records in this recipe invocation.
            first_record.input_files = input_set.items()
            first_record.output_files = output_set.items()

            user_total = first_record.times_end[first_record.USER_TIME]
            sys_total = first_record.times_end[first_record.SYS_TIME]

            for rec in ri_records[1:]:
                first_record.cmdline_args.extend(";")
                first_record.cmdline_args.extend(rec.cmdline_args)

                first_record.cmdline += " ; " + rec.cmdline

                first_record.pid += ", " + rec.pid
                user_total += rec.times_end[rec.USER_TIME]
                sys_total += rec.times_end[rec.SYS_TIME]

            first_record.SetTimesEnd(user_total, sys_total, ri_records[-1].times_end[ri_records[-1].REAL_TIME])
            first_record.CalculateDiffTimes()

            # Replace the group of recipe-invocation records with this new record
            recipe_invocation_records[ri_key] = first_record
#            print "Replacing %s with:" % (ri_key,)
#            first_record.Print()

            for output in first_record.output_files:
                # Skip this file if the user wants to look at only
                # certain output files, and this isn't one of them.
                if only_filenames and not output in only_filenames:
                    continue

                recs = recs_by_output.setdefault(output, [])
                recs.append(first_record)

        else:
            # Only one record?
            rec = ri_records[0]

            # clearaudit info?
            if rec.output_files:
                for output in rec.output_files:
                    # Skip this file if the user wants to look at only
                    # certain output files, and this isn't one of them.
                    if only_filenames and not output in only_filenames:
                        continue

                    recs = recs_by_output.setdefault(output, [])
                    recs.append(rec)

            else:
                # No? Try parsing the command-line.
                cliparser = cli_plugins.ParseRecord(rec)
                if cliparser:
                    outputs = cliparser.Outputs()
                    for output in outputs:
                        # Skip this file if the user wants to look at only
                        # certain output files, and this isn't one of them.
                        if only_filenames and not output in only_filenames:
                            continue

                        recs = recs_by_output.setdefault(output, [])
                        recs.append(rec)

    # We don't need the recipe-invocation records any more
    del recipe_invocation_records

    # Remove data on files which were written only once.
    remove_single_writes(recs_by_output)

    # Report the duplicates
    outputs = recs_by_output.keys()
    outputs.sort()

    if SHOW_RECORDS:
        output_filenames = []
        times_written = []

        # Print the records
        for output in outputs:
            recs = recs_by_output[output]

            output_filenames.append(output)
            comment = "%d times" % (len(recs),)
            if imlib.records_overlap_in_time(recs):
                comment += " (OVERLAP)"
            times_written.append(comment)

            num_chars = len(output)
            print "=" * num_chars
            print output
            print "-" * num_chars
            for rec in recs:
                rec.Print()
            print "=" * num_chars
            print

        # Print the summary for all the files.
        if output_filenames:
            print
            print "SUMMARY:"
            print "--------"
            LOG.print_indented_list(sys.stdout, output_filenames, times_written)

        else:
            print "No multiply-written files found."

    else:
        # Just a list of filenames
        for output in outputs:
            print output

def remove_single_writes(recs_by_output):
    """Remove records where only one process wrote to the file."""
    for output, recs in recs_by_output.items():
        if len(recs) < 2:
            del recs_by_output[output]


