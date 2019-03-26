#!/usr/bin/env python
"""Query for meta-data for a given font"""
from __future__ import print_function
#from ttfquery import describe
from ttfquery import ttffiles
import sys, logging

def printMetaData( metadata ):
    print('    Specific Name:', metadata.specific_name)
    print('    File:', metadata.file_name)
    print('    Modifiers:', metadata.modifiers)
    print('    Family Name:', ", ".join(metadata.family))

def get_options():
    base = ttffiles.get_options()
    base.description = 'Query/search for metadata for the given name'
    base.add_argument(
        'name',
        help="The font name, family or fragment for which to search",
    )
    return base

def main():
    logging.basicConfig(level=logging.INFO)
    options = get_options().parse_args()
    registry = ttffiles.registry_for_options( options )
    find_match(options.name,registry)

def find_match(name, registry):
    fontNames = registry.matchName( name )
    fontNames.sort()
    for general in fontNames:
        print('Font:', general)
        specifics = registry.fontMembers( general )
        specifics.sort()
        for specific in specifics:
            printMetaData( registry.metadata( registry.fontFile(specific) ))
    
    
if __name__ == "__main__":
    main()
