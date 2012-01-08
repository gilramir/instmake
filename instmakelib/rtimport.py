# Copyright (c) 2010 by Cisco Systems, Inc.
"""
Run-time import of modules, including modules within packages.
"""


def rtimport(name):
	"""Imports a module, even within a package (via the
	'package.module' naming convention, and returns a reference
	to the module (or object within a module!). Can raise
	the ImportError exception."""

	# This can raise ImportError
	obj = __import__(name)

	components = name.split('.')
	for comp in components[1:]:
		try:
			obj = getattr(obj, comp)
		except AttributeError:
			raise ImportError

	return obj
