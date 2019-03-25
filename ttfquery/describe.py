"""Extract meta-data from a font-file to describe the font"""
from fontTools import ttLib
import sys
try:
    from OpenGLContext.debug.logs import text_log
except ImportError:
    text_log = None

def openFont( filename ):
    """Get a new font object"""
    if isinstance( filename, (str,unicode)):
        filename = open( filename, 'rb')
    return ttLib.TTFont(filename)

FONT_SPECIFIER_NAME_ID = 4
FONT_SPECIFIER_FAMILY_ID = 1
def shortName( font ):
    """Get the short name from the font's names table"""
    name = ""
    family = ""
    for record in font['name'].names:
        if record.nameID == FONT_SPECIFIER_NAME_ID and not name:
            if '\000' in record.string:
                name = unicode(record.string, 'utf-16-be').encode('utf-8')
            else:
                name = record.string
        elif record.nameID == FONT_SPECIFIER_FAMILY_ID and not family:
            if '\000' in record.string:
                family = unicode(record.string, 'utf-16-be').encode('utf-8')
            else:
                family = record.string
        if name and family:
            break
    return name, family


FAMILY_NAMES = {
    0: ("ANY",{}),
    1: ("SERIF-OLD", {
        0: "ANY",
        1: "ROUNDED-LEGIBILITY",
        2: "GARALDE",
        3: "VENETIAN",
        4: "VENETIAN-MODIFIED",
        5: "DUTCH-MODERN",
        6: "DUTCH-TRADITIONAL",
        7: "CONTEMPORARY",
        8: "CALLIGRAPHIC",
        15: "MISCELLANEOUS",
    }),
    2: ("SERIF-TRANSITIONAL", {
        0: "ANY",
        1: "DIRECT-LINE",
        2: "SCRIPT",
        15: "MISCELLANEOUS",
    }),
    3: ("SERIF", {
        0: "ANY",
        1: "ITALIAN",
        2: "SCRIPT",
        15: "MISCELLANEOUS",
    }),
    4: ("SERIF-CLARENDON",{
        0: "ANY",
        1: "CLARENDON",
        2: "MODERN",
        3: "TRADITIONAL",
        4: "NEWSPAPER",
        5: "STUB-SERIF",
        6: "MONOTYPE",
        7: "TYPEWRITER",
        15: "MISCELLANEOUS",
    }),
    5: ("SERIF-SLAB",{
        0: 'ANY',
        1: 'MONOTONE',
        2: 'HUMANIST',
        3: 'GEOMETRIC',
        4: 'SWISS',
        5: 'TYPEWRITER',
        15: 'MISCELLANEOUS',
    }),
    7: ("SERIF-FREEFORM",{
        0: 'ANY',
        1: 'MODERN',
        15: 'MISCELLANEOUS',
    }),
    8: ("SANS",{
        0: 'ANY',
        1: 'GOTHIC-NEO-GROTESQUE-IBM',
        2: 'HUMANIST',
        3: 'ROUND-GEOMETRIC-LOW-X',
        4: 'ROUND-GEOMETRIC-HIGH-X',
        5: 'GOTHIC-NEO-GROTESQUE',
        6: 'GOTHIC-NEO-GROTESQUE-MODIFIED',
        9: 'GOTHIC-TYPEWRITER',
        10: 'MATRIX',
        15: 'MISCELLANEOUS',
    }),
    9: ("ORNAMENTAL",{
        0: 'ANY',
        1: 'ENGRAVER',
        2: 'BLACK-LETTER',
        3: 'DECORATIVE',
        4: 'THREE-DIMENSIONAL',
        15: 'MISCELLANEOUS',
    }),
    10:("SCRIPT",{
        0: 'ANY',
        1: 'UNCIAL',
        2: 'BRUSH-JOINED',
        3: 'FORMAL-JOINED',
        4: 'MONOTONE-JOINED',
        5: 'CALLIGRAPHIC',
        6: 'BRUSH-UNJOINED',
        7: 'FORMAL-UNJOINED',
        8: 'MONOTONE-UNJOINED',
        15: 'MISCELLANEOUS',
    }),
    12:("SYMBOL",{
        0: 'ANY',
        3: 'MIXED-SERIF',
        6: 'OLDSTYLE-SERIF',
        7: 'NEO-GROTESQUE-SANS',
        15: 'MISCELLANEOUS',
    }),
}

WEIGHT_NAMES = {
    'thin':100,
    'extralight':200,
    'ultralight':200,
    'light':300,
    'normal':400,
    'regular':400,
    'plain':400,
    'medium':500,
    'semibold':600,
    'demibold':600,
    'bold':700,
    'extrabold':800,
    'ultrabold':800,
    'black':900,
    'heavy':900,
}
WEIGHT_NUMBERS = {}
for key,value in WEIGHT_NAMES.items():
    WEIGHT_NUMBERS.setdefault(value,[]).append(key)

def weightNumber( name ):
    """Convert a string-name to a weight number compatible with this module"""
    if isinstance( name, (str,unicode)):
        name = name.lower()
        name = name.replace( '-','').replace(' ','')
        if name and name[-1] == '+':
            name = name[:-1]
            adjust = 50
        elif name and name[-1] == '-':
            name = name[:-1]
            adjust = -50
        else:
            adjust = 0
        return WEIGHT_NAMES[ name ]+ adjust
    else:
        return int(name) or 400 # for cases where number isn't properly specified

def weightName( number ):
    """Convert integer number to a human-readable weight-name"""
    number = int(number) or 400
    if WEIGHT_NUMBERS.has_key( number ):
        return WEIGHT_NUMBERS[number]
    name = 'thin-'
    for x in range(100,1000, 100):
        if number >= x:
            name = WEIGHT_NUMBERS[x]+'+'
    return name

def family( font ):
    """Get the family (and sub-family) for a font"""
    HIBYTE = 65280
    LOBYTE = 255
    familyID = (font['OS/2'].sFamilyClass&HIBYTE)>>8
    subFamilyID = font['OS/2'].sFamilyClass&LOBYTE
    return familyNames( familyID, subFamilyID )
def familyNames( familyID, subFamilyID=0 ):
    """Convert family integers to human-readable names"""
    familyName, subFamilies = FAMILY_NAMES.get( familyID, ('RESERVED',None))
    if familyName == 'RESERVED':
        if text_log:
            text_log.warn( 'Font has invalid (reserved) familyID: %s', familyID )
    if subFamilies:
        subFamily = subFamilies.get(subFamilyID, 'RESERVED')
    else:
        subFamily = 'ANY'
    return (
        familyName,
        subFamily
    )

def modifiers( font ):
    """Get weight and italic modifiers for a font

    weight is taken from the OS/2 usWeightClass field
    italic is taken from either OS/2 fsSelection or
    head macStyle, if either indicates italics we
    report italics
    """
    return (
        # weight as an integer
        font['OS/2'].usWeightClass,
        ( # italic
            font['OS/2'].fsSelection &1 or
            font['head'].macStyle&2
        ),
    )

def guessEncoding( font, given=None ):
    """Attempt to guess/retrieve an encoding from the font itself

    Basically this will try to get the given encoding
    (unless it is None).

    If given is a single integer or a single-item tuple,
    we will attempt scan looking for any table matching
    given as the platform ID and returning the first sub
    table.

    If given is a two-value tuple, we will require
    explicit matching, and raise errors if the encoding
    cannot be retrieved.

    if given is None, we will return the first encoding
    in the font.

    XXX This needs some work, particularly for non-win32
        platforms, where there is no preference embodied
        for the native encoding.
    """
    if isinstance( given, tuple) and given:
        if len(given) == 2:
            if __debug__:
                if text_log:
                    text_log.info(
                        """Checking for explicitly required encoding %r""",
                        given
                    )
            if not font['cmap'].getcmap( *given ):
                raise ValueError(
                    """The specified font encoding %r does not appear to be available within the font %r. Available encodings: %s"""% (
                        given, shortName(font),
                        [
                            (table.platformID,table.platEncID)
                            for table in font['cmap'].tables
                        ],
                    )
                )
            return given
        elif len(given) > 2:
            raise TypeError("""Encoding must be None, a two-tuple, or an integer, got %r"""%(given,))
        else:
            # treat as a single integer, regardless of number of integer's
            given = given[0]
    if isinstance( given, (int, long)):
        for table in font['cmap'].tables:
            if table.platformID == given:
                return (table.platformID, table.platEncID)
        raise ValueError(
            """Could not find encoding with specified platformID==%s within the font %r. Available encodings: %s"""% (
                given, shortName(font),
                [
                    (table.platformID,table.platEncID)
                    for table in font['cmap'].tables
                ],
            )
        )
    if sys.platform == 'win32':
        prefered = (3,1)
        # should have prefered values for Linux and Mac as well...
        for table in font['cmap'].tables:
            if (table.platformID, table.platEncID) == prefered:
                return prefered
    # just retrieve the first table's values
    for table in font['cmap'].tables:
        return (table.platformID, table.platEncID)
    raise ValueError(
        """There are no encoding tables within the font %r, likely a corrupt font-file"""% (
            shortName(font),
        )
    )
