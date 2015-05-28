Instmake is a tool which embeds itself as the shell used during the run of GNU make. By doing this it can record every command executed during a build, along with data about that command. The resulting log file is much more detailed than the traditional output of GNU make. The log files can be analyzed to investigate what happened during the build.

Instrumenting a build is simple:

```
$ instmake make -j4
```


Then any of the reports can be run on that log:

```
$ instmake -s tooltime
CPU TIME, Non-Make Records
                                                                                 (*) 
                             TIMES         TOTAL   % TOT           MIN           MAX          MEAN
TOOL                           RUN          TIME    TIME          TIME          TIME          TIME
------------------------- -------- ------------- ------- ------------- ------------- -------------
./config.status                  3        7.970s  32.61%        0.070s        7.760s        2.657s
./config/missing                 4        6.060s  24.80%        0.280s        2.880s        1.515s
gcc                             26       10.350s  42.35%        0.070s        1.520s        0.398s
swig                             1        0.060s   0.25%        0.060s        0.060s        0.060s
if                               2        0.000s   0.00%        0.000s        0.000s        0.000s
rm                               3        0.000s   0.00%        0.000s        0.000s        0.000s
touch                            1        0.000s   0.00%        0.000s        0.000s        0.000s
cat                              1        0.000s   0.00%        0.000s        0.000s        0.000s
./python-config.py               1        0.000s   0.00%        0.000s        0.000s        0.000s

TOTAL                           42       24.440s
```

Instmake comes with many built-in reports for analyzing builds, parallelism issues, and race conditions.
