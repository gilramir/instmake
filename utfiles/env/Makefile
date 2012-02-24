# Copyright (c) 2012 by Cisco Systems, Inc.

container.zip : a.txt b.txt c.txt d.txt
	zip $@ $^

%.txt : source
	cp $< $@
