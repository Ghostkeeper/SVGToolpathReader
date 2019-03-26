"""Provides a single font metadata cache from which multiple programs can run

Note: on systems without an XDG_CACHE_HOME or a HOME environment variable 
this will store the cache in the *code* directory for ttfquery, which is
obviously sub-optimal.

`registryFile` -- calculated at load time as the location for the cache
"""
from ttfquery import ttffiles
import os, logging 
log = logging.getLogger( __name__ )

### more robust registry-file location by John Hunter...
if 'XDG_CACHE_HOME' in os.environ:
    registryFile = os.path.join( os.environ['XDG_CACHE_HOME'], "ttfquery", "font.cache")
elif 'HOME' in os.environ:
    registryFile = os.path.join( os.environ['HOME'], ".font.cache")
else:
    # OpenGLContext uses the Application Data directory for win32,
    # should consider porting that code here...
    registryFile = os.path.join( os.path.split(__file__)[0], "font.cache")

registry = None
def get_registry():
    """Get a singleton registry instance in `registryFile` scanning if new"""
    global registry
    if registry is not None:
        return registry
    if os.path.isfile( registryFile ):
        registry = ttffiles.load( registryFile )
    else:
        registry = ttffiles.Registry()
        log.info( """Scanning for system fonts...""" )
        new,failed = registry.scan( printErrors = 1, force = 0)
        log.info( """Scan complete. Saving to %r\n""", registryFile,)
        registry.save(registryFile)
    return registry
