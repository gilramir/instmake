# Introduction #

This document will teach you how to use instmake to analyze build problem.


# Running a build #

The first thing to do is to actually instrument a build. When using instmake, two logs are created: the normal text output from Make, and a binary log file that is proprietary to instmake.

By default, instmake will store its log as ~/.instmake-log, but this is only useful for short investigations. Usually you are running instmake multiple times with different targets or with different variable overrides, so in general it is better to explicitly name your instmake log file:

Default:
```
$ instmake make -j2 target-name
```

Giving the name of the instmake log file:
```
$ instmake -L ~/run1.imlog make -j2 target-name
```

Of course, it's usually best to save the output of Make to a file as well. You can do that  expliclty:
```
$ instmake -L ~/run1.imlog -o make.out make -j2 target-name
```

Or you can save both the instmake log and the make output with the same basename:
```
$ instmake --logs ~/run1 make -j2 target-name
```
In that case, two files will be created: ~/run1.imlog and ~/run1.make.out

Finally, if you are operating in a ClearCase view, the --vws option will let you name the two output file with the same name, **and** place the logs in your view's working storage directory:
```
$ instmake --vws run1 make -j2 target-name
```

One final note: instmake can automatically read gzipped instmake log files. Thus, after creating your instmake log file, if it is large and you have to ship it across the globe over the network, you can gzip it and then immediately use it on the other end without decompressing it.

# Using the Instmake log #
TBD