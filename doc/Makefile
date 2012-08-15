# Copyright (c) 2010 by Cisco Systems, Inc.

MANPAGES := instmake.1

instmake_VERSION := $(shell ../setup.py --version)

doco : $(MANPAGES)

POD2MAN := pod2man
GROUP_NAME := "Instmake"

# Turn a POD into a manpage
%.1 : %.pod
	$(POD2MAN) $< \
		--release=$($*_VERSION) \
		--center=$(GROUP_NAME) > $@

.PHONY : clean
clean :
	rm -f $(MANPAGES)
