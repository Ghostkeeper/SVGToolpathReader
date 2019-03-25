"""Provides primitive font registry lookup/location for scripts

The singleton "registry" object (an instance of :class:`ttfquery.ttffiles.Registry`
is the only member of note).  This registry with be created in a file 
in the user's $HOME directory ``.font.cache`` if the $HOME environment variable 
is defined.  Otherwise will be created in the ttfquery source code directory 
(which is obviously not a very good solution).
"""
from ttfquery import ttffiles
import os, sys, logging 
log = logging.getLogger( __name__ )

### more robust registry-file location by John Hunter...
if os.environ.has_key('HOME'):
    registryFile = os.path.join( os.environ['HOME'], ".font.cache")
else:
    # OpenGLContext uses the Application Data directory for win32,
    # should consider porting that code here...
    registryFile = os.path.join( os.path.split(__file__)[0], "font.cache")

# make sure we can write to the registryFile
if not os.path.exists(registryFile):
    try: fh = file(registryFile, 'w')
    except IOError:
        log.error( 'Could not open registry file %r for writing', registryFile )
        raise
    else:
        fh.close()
        os.remove(registryFile)

def _getRegistry():
    if os.path.isfile( registryFile ):
        registry = ttffiles.load( registryFile )
    else:
        registry = ttffiles.Registry()
        log.info( """Scanning for system fonts...""" )
        new,failed = registry.scan( printErrors = 1, force = 0)
        log.info( """Scan complete. Saving to %r\n""", registryFile,)
        registry.save(registryFile)
    return registry
registry = _getRegistry()
