#!/usr/bin/env python
"""Demo script to print ordered set of system fonts"""
from ttfquery import describe, findsystem
import sys, traceback, logging
log = logging.getLogger( __name__ )

def buildTable( filenames=None, failureCallback=None ):
    """Build table mapping {family:(font:{modifiers:(name,file)})}

    filenames -- if provided, list of filenames to scan,
    otherwise the full set of system fonts provided
    by findsystem will be used.
    failureCallback -- if provided, a function taking three
    arguments, the failing filename, an error-type code,
    and the error object.  If processing should stop,
    raise an error.
    codes:
    
        0 -- couldn't open the font file
        1 -- couldn't find modifiers in the font file
        2 -- couldn't find font-name in the font file
        3 -- couldn't find the generic family specifier
        for the font
    """
    if filenames is None:
        filenames = findsystem.findFonts()
    table = {}
    for filename in filenames:
        try:
            font = describe.openFont(filename)
        except Exception, err:
            if failureCallback:
                failureCallback( filename, 0, err )
        else:
            try:
                modifiers = describe.modifiers( font )
            except (KeyError,AttributeError), err:
                if failureCallback:
                    failureCallback( filename, 1, err )
                modifiers = (None,None)
            try:
                specificName, fontName = describe.shortName( font )
            except (KeyError,AttributeError), err:
                if failureCallback:
                    failureCallback( filename, 2, err )
            else:
                try:
                    specifier = describe.family(font)
                except KeyError:
                    if failureCallback:
                        failureCallback( filename, 3, err )
                else:
                    table.setdefault(
                        specifier,
                        {}
                    ).setdefault(
                        fontName,
                        {}
                    )[modifiers] = (specificName,filename)
    return table

def interactiveCallback( file, code, err ):
    """Simple error callback for interactive use"""
    log.warn(
        'Failed reading file %r (code %s):\n', file, code,
    )

def main():
    import time
    t = time.clock()
    if sys.argv[1:]:
        directories = sys.argv[1:]
        files = findsystem.findFonts(directories)
    else:
        files = None
    table = buildTable(files, failureCallback=interactiveCallback)
    t = time.clock()-t
    keys = table.keys()
    keys.sort()
    for fam in keys:
        print '_________________________'
        print fam
        fnts = table[fam].items()
        fnts.sort()
        for fnt,modset in fnts:
            mods = modset.keys()
            mods.sort()
            mods = ",".join([ '%s%s'%( w, ['','(I)'][i&1]) for (w,i) in mods])
            print '    ',fnt.ljust(32), '--', mods
    log.info( 'Scan took %s seconds CPU time', t )

if __name__ == "__main__":
    logging.basicConfig( level =logging.INFO )
    main()
