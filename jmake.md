# Introduction #

Within the instmake code there are some reference to JMAKE environment variables. jmake is tool my team at Cisco uses; it is a modified version of GNU Make that can export extra information to instmake for recording.

# Basic Info #

**JMAKE\_CURRENT\_MAKE\_TARGET** - this is the target that Make is trying to bring up to date while it is running a command. It is the equivalent of "$@" in a Make rule.

**JMAKE\_CURRENT\_MAKEFILE\_FILENAME** - this is the location of the rule that Make is using to run the currently-executing command.

**JMAKE\_CURRENT\_MAKEFILE\_LINENO** - this is the location of the rule that Make is using to run the currently-executing command.

# Variables #
jmake can be invoked with one or more -M VAR options, in which case jmake exports the value and origin of the VAR makefile variable. These 2 are exported as:

**JMAKE\_VAR\_x** - the value of $(x)
**JMAKE\_VOR\_x** - the origin of x, or rather, the value of $(origin x)

This works for regular variables as well as automatic variables:

instmake jmake -M CFLAGS -M '<'

# Other actions #

Finally, jmake will check if it is running under instmake by checking if the INSTMAKE\_SCRIPT environment variable is set. If so, then it will call the "instmake -r" interface for recording arbitrary actions in the instmake log.

For example, every time $(wildcard) is executed, jmake will record that fact in the instmake log. Or, when an intermediate file is automatically remove because it is not "precious", jmake records that in the instmake log.

For this, instmake needs no special jmake interface, other than provide the '-r' option for jmake, or any other tool, to record information in the log.