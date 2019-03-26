"""The singleton "registry" object (an instance of :class:`ttfquery.ttffiles.Registry`
is the only member of note).  This registry with be created in a file 
in the user's $HOME directory ``.font.cache`` if the $HOME environment variable 
is defined.  Otherwise will be created in the ttfquery source code directory 
(which is obviously not a very good solution).

.. note::

    This module is basically here for legacy applications that used
    the singleton registry instance. Use scriptregistry.get_registry()
    in new code.
"""
from ttfquery import scriptregistry

_getRegistry = scriptregistry.get_registry
registry = scriptregistry.get_registry()
