"""Demo script to print ordered set of system fonts"""
from __future__ import print_function
from ttfquery import describe, ttffiles
import sys, logging
log = logging.getLogger( __name__ )

def buildTable( registry ):
    """Build table mapping {family:(font:{modifiers:(name,file)})}

    filenames -- if provided, list of filenames to scan,
    otherwise the full set of system fonts provided
    by findsystem will be used.
    """
    table = {}
    for major, minors in registry.families.items():
        for minor, fonts in minors.items():
            for fontname in fonts.keys():
                table.setdefault(major,{}).setdefault(fontname, {})
                font = registry.fonts.get(fontname)
                if font:
                    for modifier,specifics in sorted(font.items()):
                        for specific in specifics:
                            specificfont = registry.specificFonts[specific]
                            table[major][fontname][modifier] = (
                                specificfont.font_name,
                                specificfont.file_name
                            )
                            break
    return table

def get_options():
    base = ttffiles.get_options()
    base.description = '''Display all of the major font-groups on the system'''
    return base

def main():
    options = get_options().parse_args()
    table = buildTable(registry=ttffiles.registry_for_options(options))
    run_report(table)

def run_report(table):
    keys = sorted(table.keys())
    for fam in keys:
        print('_________________________')
        print(fam)
        fnts = sorted( table[fam].items() )
        for fnt,modset in fnts:
            mods = sorted(modset.keys())
            mods = ",".join([ '%s%s'%( w, ['','(I)'][i&1]) for (w,i) in mods])
            print('    ',fnt.ljust(32), '--', mods)
