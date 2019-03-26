#!/usr/bin/env python
"""Query for font-members of a particular family"""
from __future__ import print_function
from ttfquery import ttffiles
import sys, logging
log = logging.getLogger( __name__ )

def get_options():
    options = ttffiles.get_options()
    options.description = 'Find all members of a particular font-family'
    options.add_argument(
        'major', help='The major family component, e.g. ANY or SANS, SCRIPT, SERIF, SERIF-OLD, SERIF-SLAB, etc',
        default='ANY',
        nargs='?',
    )
    options.add_argument(
        'minor', help='The minor family component, or all if unspecified',
        nargs='?',
        default=None,
    )
    return options

def main():
    logging.basicConfig(level=logging.INFO)
    options = get_options().parse_args()
    registry = ttffiles.registry_for_options(options)
    search(registry,options.major,options.minor)
    return 0

def search(registry,major,minor=None):
    for fontName in registry.familyMembers(major,minor):
        print('F', fontName)
        for specific in registry.fontMembers( fontName ):
            print(' ', registry.fontFile( specific ))

if __name__ == "__main__":
    main()
