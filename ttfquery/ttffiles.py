"""Registry of available TrueType font files"""
from ttfquery import describe, findsystem
import traceback, os
try:
    import cPickle as pickle 
except ImportError:
    import pickle
try:
    unicode 
except NameError:
    unicode = str
import logging 
log =logging.getLogger( __name__ )
from collections import namedtuple

class FontMetadata(namedtuple(
    'FontMetadata',
    (
        'file_name',
        'modifiers',
        'specific_name',
        'font_name',
        'family',
    ),
)):
    """Stores specific font metadata

    A specific font is basically an actual font-file,
    that is, it is one of a family of fonts which make 
    up the various "modified" versions of a font face.

    So `Ubuntu Light Italic` would be a specific font 
    that is a part of the font-face `Ubuntu` with the modifers
    for `Light` and `Italic` applied.

    * file_name -- fully specified absolute path
    * modifiers -- (weightInteger, italicsFlag)
    * specific_name -- specific name of the particular
        font stored in the given file, the name of
        the "modified" font
    * font_name -- name of the general font which
        the modifiers are specialising
    * family -- family specifier, two-tuple of
        high-level and sub-level font classifications
        based on font characteristics as encoded
        in the font file.
    """
    __slots__ = ()


FILENAME, MODIFIERS, SPECIFICNAME, FONTNAME, FAMILY = range(5)

class Registry(object):
    """Object providing centralized registration of TTF files

    Attributes:

        families -- mapping from TrueType font families
            to sub-families and then to general fonts
            (as a set of font-names).
        fonts -- mapping from general fonts to modifiers to
            specific font instances
        specificFonts -- mapping from specific font names
            to the entire "metrics" set for the particular
            font (a :class:`FontMetadata` namedtuple)
        files -- mapping from (absolute) filenames to
            specific font names
        shortFiles -- mapping from font filename basenames
            to font-file-lists
        
        DIRTY -- flag indicating whether the registry has
            had a new font registered (i.e. whether it should
            be saved out to disk).
    """
    DIRTY = 0
    filename = ""
    def __init__(self):
        """Initialize the Registry"""
        self.families = {}
        self.fonts = {}
        self.specificFonts = {}
        self.files = {}
        self.shortFiles = {}
    def clear( self ):
        """Clear out the all tables and mark unchanged"""
        self.families.clear()
        self.fonts.clear()
        self.specificFonts.clear()
        self.files.clear()
        self.shortFiles.clear()
        self.dirty(0)
    def dirty(self, dirty = 1):
        """Mark the registry as changed/unchanged"""
        self.DIRTY = dirty

    def metadata(
        self,
        filename,
        force = 0
    ):
        """Retrieve metadata from font file

        :param filename: fully specified path to the font file
        :param force: if false, and the metadata is already
            available for this file, do not access the
            font file to retrieve, just return the existing
            metadata.

        :rtype: :class:`FontMetadata`
        """
        filename = os.path.abspath( filename )
        if filename in self.files and not force:
            return self.specificFonts.get( self.files[filename] )
        font = describe.openFont(filename)
        try:
            modifiers = describe.modifiers( font )
        except (KeyError,AttributeError):
            modifiers = (None,None)
        specificName, fontName = describe.shortName( font )
        specifier = describe.family(font)
        result = (
            filename,
            modifiers,
            specificName,
            fontName,
            specifier,
        )
        return FontMetadata(*[
            (x.decode('utf-8') if isinstance(x,bytes) else x)
            for x in result 
        ])
    def register(
        self,
        filename,
        modifiers = None,
        specificName = None,
        fontName = None,
        familySpecifier = None,
        force = 0,
    ):
        """Do the actual registration of a filename & metadata

        See metadata function for description of the various
        arguments.  If modifiers == None then the metadata function
        will be used to scan for the metadata.

        force -- if true, force re-reading font-file even if we already
            have the meta-data for the file loaded.
        """
        filename = os.path.abspath( filename )
        if filename in self.files and not force:
            return self.specificFonts.get( self.files[filename] )
        self.dirty(1)
        if modifiers == None:
            (filename, modifiers, specificName, fontName, familySpecifier) = self.metadata(filename, force = force)
        description = FontMetadata(filename, modifiers, specificName, fontName, familySpecifier)
        try:
            self.files[filename] = specificName
            major,minor = familySpecifier
            self.families.setdefault(major,{}).setdefault(minor,{})[fontName] = 1
            self.fonts.setdefault(fontName, {}).setdefault(modifiers,[]).append(specificName)
            self.specificFonts[ specificName ] = description
            self.shortFiles.setdefault(os.path.basename(filename), []).append( filename )
        except Exception:
            if filename in self.files:
                del self.files[filename]
            raise
        return description

    def familyMembers( self, major, minor=None ):
        """Get all (general) fonts for a given family

        :param major: string description of major family
        :param minor: optional string description of minor family
        
        :rtype: list of font faces in the family
        """
        major = major.upper()
        if not minor:
            result = []
            for key,set in self.families.get(major,{}).items():
                result.extend( set.keys())
            return result
        minor = minor.upper()
        return list(self.families.get( major, {}).get(minor,{}).keys())
    def fontMembers( self, fontName, weight=None, italics=None ):
        """Get specific font names for given generic font name

        :param fontName: general font name to search
        :param weight: if given, only return specific fonts with that weight
        :param italics: if given, only return fonts with italics value equal

        :rtype: list of specific font names
        """
        table = self.fonts.get( fontName, {})
        items = list(table.items())
        items.sort()
        if weight is not None:
            weight = describe.weightNumber( weight )
            items = [item for item in items if item[0][0]==weight]
        if italics is not None:
            items = [item for item in items if item[0][1]==italics]
        result = []
        for item in items:
            result.extend( item[1])
        return result
    def fontForms( self, fontName ):
        """Retrieve the set of font-forms (weight,italics) available in a font
        
        :param fontName: general font name to search
        :rtype: list of two-tuples of (weight,italics) available in the font
        """
        return list(self.fonts.get( fontName, {}).keys())

    def fontFile( self, specificName ):
        """Return the absolute path-name for a given specific font
        
        :param specificName: specific font name to search
        :rtype: str(file_name) of the FontMetadata instance
        """
        description = self.specificFonts.get( specificName )
        if description:
            return description[0]
        else:
            raise KeyError( """Couldn't find font with specificName %r, can't retrieve filename for it"""%( specificName,))

    def matchName( self, name, single=0 ):
        """Try to find a general font based on a name
        
        :param name: name to use to try to find the font, can match on any of
            specific name, major family, or minor family
        :param single: return the first match only (not a dictionary of results)

        :rtype: if single str(fontName) else {fontName:1,...}
        """
        if isinstance(name,bytes):
            try:
                name = name.decode('utf-8')
            except Exception:
                # suppose we should use something else here...
                name = name.decode('latin-1')
        result = {}
        if name in self.fonts:
            v = name
            if single:
                return v
            else:
                result[v] = 1
        if name in self.specificFonts:
            v = self.specificFonts[name][FONTNAME]
            if single:
                return v
            else:
                result[v] = 1
        if name.upper() in self.families:
            for general in self.familyMembers( name ):
                if single:
                    return general
                result[general] = 1
        testname = name.lower()
        for specific in self.specificFonts.keys():
            if specific.lower().find( testname ) > -1:
                if single:
                    return specific
                result[ self.specificFonts[specific][FONTNAME]]=1
        for majorFamily in self.families.keys():
            if majorFamily.lower().find( testname ) > -1:
                for item in self.familyMembers( majorFamily ):
                    if single:
                        return item
                    result[item] = 1
            else:
                # if previous was true, we already included everything
                # that could be included here...
                for minorFamily in self.families[majorFamily].keys():
                    if minorFamily.lower().find( testname ) > -1:
                        for item in self.familyMembers( majorFamily, minorFamily ):
                            if single:
                                return item
                            result[item] = 1
        if not result:
            raise KeyError( """Couldn't find a font with name %r"""%(name,))
        return list(result.keys())

    def save( self, file=None, force=0 ):
        """Attempt to save the font metadata to a pickled file

        file -- a file open in binary write mode or a filename
        force -- if not true and DIRTY false, then don't actually
        save anything

        returns number of records saved
        """
        if not force and not self.DIRTY:
            return 0
        file = file or self.filename
        if not file:
            raise TypeError( """Attempted to save %r to default file, no default file specified"""% (self,))
        if not hasattr( file, 'write'):
            file = open( file, 'wb' )
        pickle.dump( list(self.specificFonts.values()), file, 1 )
        self.dirty(0)
        return len(self.specificFonts)
    def load( self, file, clearFirst=1 ):
        """Attempt to load the font metadata from a pickled file

        file -- a file open in binary read mode or a filename
        clearFirst -- if true, clear tables first, and reset DIRTY
        to 0 after finished
        """
        if clearFirst:
            self.clear()
        if not hasattr( file, 'read'):
            self.filename = file
            file = open( file, 'rb' )
        table = pickle.load( file )
        for filename, modifiers, specificName, fontName, familySpecifier in table:
            ## Minimal sanity check...
            if os.path.isfile( filename ):
                self.register(filename, modifiers, specificName, fontName, familySpecifier)
        if clearFirst:
            self.dirty(0)
        return len(table)

    def scan( self, paths=None, printErrors=0, force = 0 ):
        """Scan the given paths registering each found font"""
        new, failed = [],[]
        for filename in findsystem.findFonts(paths):
            try:
                self.register( filename, force = force )
            except Exception:
                log.info( 'Failure scanning %s', filename )
                if printErrors:
                    log.warn( "%s", traceback.format_exc())
                failed.append( filename )
            else:
                new.append( filename )
        return new, failed

def load( *arguments, **named ):
    """Construct registry from saved file

    Assembly creates a Registry object and calls the
    load method with the file as argument.
    """
    registry = Registry()
    registry.load( *arguments, **named )
    return registry

def get_options():
    """Creation base options for creating a ttfquery registry"""
    import argparse
    from ttfquery import scriptregistry
    parser = argparse.ArgumentParser(description="Create or update font metadata cache")
    parser.add_argument(
        '-r','--registry',
        help="The registry file to update, defaults to %s"%(scriptregistry.registryFile),
        default=scriptregistry.registryFile,
    )
    parser.add_argument(
        '-s','--scan',
        help='If specified, then force a scan even if the registry already exists (otherwise only scan if new)',
        default=False,
        action='store_true',
    )
    parser.add_argument(
        '--directories',
        nargs='*',
        help='Directory (directories) to scan for font metadata, default is system font directories',
    )
    return parser


def main():
    import logging 
    logging.basicConfig(level=logging.INFO)
    options = get_options().parse_args()
    registry = registry_for_options(options)
    return 0

def registry_for_options(options):
    """Given options as in :func:`get_options` initialize registry"""
    if options.registry and os.path.exists(options.registry):
        registry = load(options.registry)
        new = False
    else:
        registry = Registry()
        new = True
    scan = new 
    if getattr(options,'scan',False):
        log.info("Forcing rescan of directories")
        scan = True
    if scan:
        new,failed = registry.scan( 
            options.directories or None, 
            printErrors = False, 
            force = 1
        )
        if options.registry and registry.DIRTY:
            registry.save(options.registry)
    else:
        log.info("Registry already populated")
    log.info( '%s fonts available', len(registry.fonts) )
    return registry


if __name__ == "__main__":
    main()
