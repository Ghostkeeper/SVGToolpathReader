
"""Registry of available TrueType font files

XXX Currently two copies of exactly the same font
    will likely confuse the registry because the
    specificFonts set will only have one of the
    metrics sets.  Nothing breaks at the moment
    because of this, but it's not ideal.
"""
from ttfquery import describe, findsystem
import cPickle, time, traceback, os, sys
import logging 
log =logging.getLogger( __name__ )

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
            font.
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

        filename -- fully specified path to the font file
        force -- if false, and the metadata is already
        available for this file, do not access the
        font file to retrieve, just return the existing
        metadata.

        return value:
            tuple of:
                filename -- fully specified absolute path
                modifiers -- (weightInteger, italicsFlag)
                specificName -- specific name of the particular
                font stored in the given file, the name of
                the "modified" font
                fontName -- name of the general font which
                the modifiers are specialising
                specifier -- family specifier, two-tuple of
                high-level and sub-level font classifications
                based on font characteristics as encoded
                in the font file.
        """
        filename = os.path.abspath( filename )
        if self.files.has_key( filename ) and not force:
            return self.specificFonts.get( self.files[filename] )
        font = describe.openFont(filename)
        try:
            modifiers = describe.modifiers( font )
        except (KeyError,AttributeError), err:
            modifiers = (None,None)
        specificName, fontName = describe.shortName( font )
        specifier = describe.family(font)
        return (
            filename,
            modifiers,
            specificName,
            fontName,
            specifier,
        )
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
        if self.files.has_key( filename ) and not force:
            return self.specificFonts.get( self.files[filename] )
        self.dirty(1)
        if modifiers == None:
            (filename, modifiers, specificName, fontName, familySpecifier) = self.metadata(filename, force = force)
        description = (filename, modifiers, specificName, fontName, familySpecifier)
        try:
            self.files[filename] = specificName
            major,minor = familySpecifier
            self.families.setdefault(major,{}).setdefault(minor,{})[fontName] = 1
            self.fonts.setdefault(fontName, {}).setdefault(modifiers,[]).append(specificName)
            self.specificFonts[ specificName ] = description
            self.shortFiles.setdefault(os.path.basename(filename), []).append( filename )
        except Exception:
            if self.files.has_key(filename):
                del self.files[filename]
            raise
        return description

    def familyMembers( self, major, minor=None ):
        """Get all (general) fonts for a given family"""
        major = major.upper()
        if not minor:
            result = []
            for key,set in self.families.get(major,{}).items():
                result.extend( set.keys())
            return result
        minor = minor.upper()
        return self.families.get( major, {}).get(minor,{}).keys()
    def fontMembers( self, fontName, weight=None, italics=None ):
        """Get specific font names for given generic font name

        weight -- if specified, only members with the given weight
        italics -- if specified, only members where the flag matches

        returns list of specific font names
        """
        table = self.fonts.get( fontName, {})
        items = table.items()
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
        """Retrieve the set of font-forms (weight,italics) available in a font"""
        return self.fonts.get( fontName, {}).keys()

    def fontFile( self, specificName ):
        """Return the absolute path-name for a given specific font"""
        description = self.specificFonts.get( specificName )
        if description:
            return description[0]
        else:
            raise KeyError( """Couldn't find font with specificName %r, can't retrieve filename for it"""%( specificName,))

    def matchName( self, name, single=0 ):
        """Try to find a general font based on a name"""
        result = {}
        if self.fonts.has_key( name ):
            v = name
            if single:
                return v
            else:
                result[v] = 1
        if self.specificFonts.has_key( name ):
            v = self.specificFonts[name][FONTNAME]
            if single:
                return v
            else:
                result[v] = 1
        if self.families.has_key( name.upper() ):
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
        return result.keys()

    def save( self, file= None, force=0 ):
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
        cPickle.dump( self.specificFonts.values(), file, 1 )
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
        table = cPickle.load( file )
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
            except Exception, err:
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

def main():
    usage ="""ttffiles [registryFile [directories]]

    Update registryFile (default "font.cache") by scanning
    the given directories, the system font directories by
    default.
    """
    exit = 0
    import sys
    if sys.argv[1:2]:
        testFilename = sys.argv[1]
        if sys.argv[2:]:
            directories = sys.argv[2:]
        else:
            directories = None
    else:
        testFilename = "font.cache"
        directories = None
    if os.path.isfile( testFilename ):
        registry = load( testFilename )
    else:
        registry = Registry()
    new,failed = registry.scan( directories, printErrors = False, force = 0)
    log.info( '%s fonts available', len(new) )
    registry.save(testFilename)
    return exit

if __name__ == "__main__":
    main()
