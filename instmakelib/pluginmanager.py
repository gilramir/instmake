# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Manage plugins for an application.
"""

from instmakelib import rtimport
import imp
import re
import os
import sys
import new

class PluginName:
    """Keeps track of the items necessary to locate and
    name a single plugin."""
    def __init__(self, prefix, name, dir, suffix):
        self.prefix = prefix
        self.name = name
        self.dir = dir
        self.suffix = suffix
        self.module = None

    def Prefix(self):
        return self.prefix

    def Name(self):
        return self.name

    def Dir(self):
        return self.dir
    
    def ModuleName(self):
        return self.prefix + "_" + self.name

    def Load(self):
        if self.module:
            return self.module
        if hasattr(imp, "load_module"):
            mod = self.StandardLoad()
        elif self.suffix == ".py":
            mod = self.TextLoad()
        else:
            mode = None

        self.module = mod
        return self.module

    def StandardLoad(self):
#        print "MODULENAME:", self.ModuleName()
#        print "DIR:", self.Dir()

        mod_desc = imp.find_module(self.ModuleName(), [self.Dir()])

        # Was the search unsuccessful?
        if not mod_desc:
            print >> sys.stderr, "%s is no longer available in %s." % \
                (self.ModuleName(), self.Dir())
            return None

        file = mod_desc[0]
        filename = mod_desc[1]
        description = mod_desc[2]

        if file == None:
            # It doesn't live in a file. ???
            return None

        try:
#            print "FILE:", file
#            print "FILENAME:", filename
#            print "DESCRIPTION:", description

            # Temporarily modify sys.path
            sys.path.insert(0, self.Dir())
#            print "SYSPATH:", sys.path
            # Try to import the module
            mod = imp.load_module(self.ModuleName(),
                file, filename, description)
        finally:
            # Revert sys.path
            del sys.path[0]

            # We're responsible for closing the open filehandle.
            if file:
                try:
                    file.close()
                except IOError:
                    pass

        return mod

    def TextLoad(self):
        """Jython doesn't have imp.load_module. Luckily, the only modules it
        can load are .py files. So we can take advantage of 'exec'."""

        basename = self.ModuleName() + self.suffix
        filename = os.path.join(self.dir, basename)

        try:
            fh = open(filename)
        except IOError:
            return None

        mod = new.module(self.ModuleName())
        try:
            # Temporarily modify sys.path
            sys.path.insert(0, self.Dir())
            exec fh in mod.__dict__
        finally:
            # Revert sys.path
            del sys.path[0]

        try:
            fh.close()
        except:
            pass

        return mod



class PluginManager:
    """Handles all plugins for an applicaton. The application
    should create one instance of this class."""

    def __init__(self, package_dirs, fs_dirs, env_vars, prefixes):
        """There are three ways to locate plugins.
        1. A list of python package directories. PluginManager will
        try to import __path__ from these these packages.

        2. A list of filesystem directories. PluginManager will
        look at the files in those directories.

        3. A list of environment variables. These environment variables
        are parsed like the PATH environment variable. The contents
        of these environment variables are filesystem directories,
        just like $PATH.

        Each plugin filename will be of the form "<type>_<name>.<ext>",
        where <type> is one of the strings listed in 'prefixes'. In
        this way, an application can have multiple types of plugins.
        The 'name' is what is shown to the user as the name of the plugin.
        The 'ext' is any of the file extensions that Python accepts
        for importable files (.py, .pyc, .pyo, .so, .dll on Windows, etc.)
        """

        # Sanity checks
        assert type(package_dirs) == type([]), "package_dirs is not a list"
        assert type(fs_dirs) == type([]), "fs_dirs is not a list"
        assert type(env_vars) == type([]), "env_vars is not a list"
        assert type(prefixes) == type([]), "prefixes is not a list"
        
        # Get the list of suffixes that this Python interpretor
        # supports
        suffixes = []
        for tuple in imp.get_suffixes():
            suffixes.append(tuple[0])

        # Create regexes for each of the prefix values combined
        # with each of the suffix values.
        filename_regexes_by_prefix = {}

        for prefix in prefixes:
            esc_prefix = re.escape(prefix)
            filename_regexes = []
            filename_regexes_by_prefix[prefix] = filename_regexes

            for suffix in suffixes:
                re_text = r"^%s_(?P<name>.*)(?P<suffix>%s)$" % (esc_prefix, re.escape(suffix))
                # I'm being pedantic here; I use re.DOTALL since
                # a filename technically can contain a new-line.
                filename_regexes.append(re.compile(re_text, re.DOTALL))

        # Determine the list of filesystem directories,
        # first using the environment variables, and then
        # the fs_dirs, and then the package_dirs.
        dirs = self.ParseEnvVars(env_vars)
        dirs.extend(fs_dirs)

        for package_dir in package_dirs:
            try:
                pkg = rtimport.rtimport(package_dir)
            except ImportError:
                continue
            dirs.append(pkg.__path__[0])

        # Hash-of-hashes to keep track of plugins by prefix and name
        self.plugins_by_prefix = {}

        # Retrieve the list of all plugins that are loadable
        for dir in dirs:
            if not os.path.exists(dir):
                continue

            # Get the list of files and see if any of them
            # are valid plugin filenames.
            try:
                files = os.listdir(dir)
            except OSError, err:
                print >> sys.stderr, "Error looking in %s: %s" % (dir, err)
                continue

            for file in files:
                for prefix in filename_regexes_by_prefix.keys():
                    plugins = self.plugins_by_prefix.setdefault(prefix, {})
                    filename_regexes = filename_regexes_by_prefix[prefix]
                    for regex in filename_regexes:
                        m = regex.search(file)
                        if m:
                            # Yes, the name looks like the file should be
                            # a plugin. If we haven't found a plugin of
                            # that name (and prefix) already, store it.
                            name = m.group("name")

                            # Don't override a plugin that was already found.
                            if plugins.has_key("name"):
                                continue

                            # Store the name away.
                            plugin = PluginName(prefix, name, dir, m.group("suffix"))
                            plugins[name] = plugin



    def ParseEnvVars(self, env_vars):
        """For each environment variable, parse the value to get
        a list of directories."""
        dirs = []

        for env_var in env_vars:
            if os.environ.has_key(env_var):
                value = os.environ[env_var]
                new_dirs = value.split(os.pathsep)
                while "" in new_dirs:
                    new_dirs.remove("")
                dirs.extend(new_dirs)

        return dirs

    def PluginNames(self, prefix):
        """For a given prefix, return a list of plugin names."""
        if not self.plugins_by_prefix.has_key(prefix):
            return []

        plugins = self.plugins_by_prefix[prefix]
        return plugins.keys()

    
    def LoadPlugin(self, prefix, name):
        """Return a Python module object for the given prefix/plugin-name.
        Can raise ImportError, or return None."""

        if not self.plugins_by_prefix.has_key(prefix):
            return None

        plugins = self.plugins_by_prefix[prefix]

        if not plugins.has_key(name):
            return None

        plugin = plugins[name]
        return plugin.Load()

    def LoadAllPlugins(self, prefix):
        """Returns a list of Python module objects for the given prefix."""
        modules = []
        names = self.PluginNames(prefix)
        for name in names:
            mod = self.LoadPlugin(prefix, name)
            if mod:
                modules.append(mod)

        return modules
