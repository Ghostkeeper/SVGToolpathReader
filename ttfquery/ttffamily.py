#!/usr/bin/env python
"""Query for font-members of a particular family"""
from ttfquery._scriptregistry import registry
import sys, os,logging
log = logging.getLogger( __name__ )

def main():
    usage ="""ttffamily MAJOR [MINOR]

    Will create a registry file font.cache if it doesn't
    already exist, otherwise will just use the existing
    cache.  See ttffiles.py for updating the cache.
    """
    if sys.argv[1:2]:
        major = sys.argv[1]
        if sys.argv[2:3]:
            minor = sys.argv[2]
        else:
            minor = None
    else:
        log.error( "Need a font-family name" )
        return 1
    for fontName in registry.familyMembers( major, minor ):
        print 'F', fontName
        for specific in registry.fontMembers( fontName ):
            print ' ', registry.fontFile( specific )
    return 0

if __name__ == "__main__":
    main()
