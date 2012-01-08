# Copyright (c) 2010 by Cisco Systems, Inc.
"""
High-level interface to information that ClearCase's cleartool
can provide.
"""
import sys
import os
from instmakelib import cleartool

class NotAView(Exception):
    pass

class View:
    def __init__(self):
        self.ct = cleartool.ClearTool()

        self.vws_parent = None
        self.view_root  = None

        # Set self.view_name, self.vws, self.vws_parent
        try:
            self.DetermineDirectory()
        except cleartool.ClearToolError:
            raise NotAView()

    def Close(self):
        self.ct.Close()

    def DetermineDirectory(self):
        """Determine our storage directory and view name.
        Sets self.view_name, self.vws, and self.vws_parent."""

        if not self.vws_parent:
            # Figure out our view name and view storage area.
            result = self.ct.Run("lsview", "-cview")

            text = result[0]
            if text.find("not a ClearCase object") >=0 :
                raise NotAView

            if text[0] == "*":
                (active, self.view_name, self.vws) = text.split()
            else:
                (self.view_name, self.vws) = text.split()

            self.vws_parent = os.path.dirname(self.vws)


    def ClearToolObject(self):
        """Returns the cleartool.ClearTool object that we have
        open so that the calling application can make its own
        low-level calls to the 'cleartool' process."""
        return self.ct

    def Name(self):
        """The name of the view."""
        return self.view_name

    def RootDir(self):
        """The directory where the MVFS view is mounted, usually
        of the form /view/<viewname>."""

        if not self.view_root:
            # Find the root dir of this view
            try:
                result = self.ct.Run("pwv", "-root")
            except cleartool.ClearToolError, err:
                sys.exit("Unable to find view root:\n%s" % (err,))

            self.view_root = result[0]

        return self.view_root

    def VWS_ParentDir(self):
        """The parent directory of this view's view-working-storage
        directory."""
        return self.vws_parent

    def VWS_Dir(self):
        """This view's view-working-storage directory."""
        return self.vws

    def PrivateFiles(self):
        """Returns view-private files (ct lsprivate -short -other)"""
        result = self.ct.Run("lsprivate", "-short", "-other")
        return result
