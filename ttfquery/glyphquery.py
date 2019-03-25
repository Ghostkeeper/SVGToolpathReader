"""Glyph-specific queries on font-files"""
from ttfquery import describe
try:
    from OpenGLContext.debug.logs import text_log
except ImportError:
    text_log = None

def hasGlyph( font, char, encoding=None ):
    """Check to see if font appears to have explicit glyph for char"""
    glyfName = explicitGlyph( font, char, encoding )
    if glyfName is None:
        return False
    return True
def explicitGlyph( font, char, encoding=None ):
    """Return glyphName or None if there is not explicit glyph for char"""
    cmap = font['cmap']
    if encoding is None:
        encoding = describe.guessEncoding( font )
    table = cmap.getcmap( *encoding )
    glyfName = table.cmap.get( ord(char))
    return glyfName

def glyphName( font, char, encoding=None, warnOnFailure=1 ):
    """Retrieve the glyph name for the given character

    XXX
        Not sure what the effect of the Unicode mapping
        will be given the use of ord...
    """
    glyfName = explicitGlyph( font, char, encoding )
    if glyfName is None:
        encoding = describe.guessEncoding( font )       #KH
        cmap = font['cmap']                             #KH
        table = cmap.getcmap( *encoding )               #KH
        glyfName = table.cmap.get( -1)
        if glyfName is None:
            glyfName = font['glyf'].glyphOrder[0]
            if text_log and warnOnFailure:
                text_log.warn(
                    """Unable to find glyph name for %r, in %r using first glyph in table (%r)""",
                    char,
                    describe.shortName(font),
                    glyfName
                )
    return glyfName

def width( font, glyphName ):
    """Retrieve the width of the giving character for given font

    The horizontal metrics table provides both the
    width and the left side bearing, we should really
    be using the left side bearing to adjust the
    character, but that's a later project.
    """
    try:
        return font['hmtx'].metrics[ glyphName ][0]
    except KeyError:
        raise ValueError( """Couldn't find glyph for glyphName %r"""%(
            glyphName,
        ))

def lineHeight( font ):
    """Get the base-line to base-line height for the font

    XXX
        There is some fudging going on here as I
        workaround what appears to be a problem with the
        specification for sTypoDescender, which states
        that it should normally be a negative value, but
        winds up being positive in at least one font that
        defines points below the zero axis.

    XXX The entire OS/2 table doesn't appear in a few
        fonts (symbol fonts in particular), such as Corel's
        BeeHive and BlackLight 686.
    """
    return charHeight(font) + font['OS/2'].sTypoLineGap

def charHeight( font ):
    """Determine the general character height for the font (for scaling)"""
    ascent = font['OS/2'].sTypoAscender
    descent = font['OS/2'].sTypoDescender
    if descent > 0:
        descent = - descent
    return ascent - descent

def charDescent( font ):
    """Determine the general descent for the font (for scaling)"""
    return font['OS/2'].sTypoDescender

