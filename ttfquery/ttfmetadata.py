#!/usr/bin/env python
"""Query for meta-data for a given font"""
from ttfquery import describe
from ttfquery._scriptregistry import registry
import sys, os

def printMetaData( metadata ):
    print '    Specific Name:', metadata[2]
    print '    File:', metadata[0]
    print '    Modifiers:', metadata[1]
    print '    Family Name:', ", ".join(metadata[4])

def main():
    usage ="""metadata_query name

    Will create a registry file font.cache if it doesn't
    already exist, otherwise will just use the existing
    cache.  See ttffiles.py for updating the cache.
    """
    if sys.argv[1:]:
        name = " ".join( sys.argv[1:] )
    else:
        sys.stderr.write( usage )
        sys.exit(1)
    fontNames = registry.matchName( name )
    fontNames.sort()
    for general in fontNames:
        print 'Font:', general
        specifics = registry.fontMembers( general )
        specifics.sort()
        for specific in specifics:
            printMetaData( registry.metadata( registry.fontFile(specific) ))
    
    
if __name__ == "__main__":
    main()
