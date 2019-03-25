"""Heuristic attempting to extract descriptions from font names

This should only be used as a backup in case there is
no proper available querying mechanism (i.e. fonttools),
and even then, we really would rather avoid using this
extremely fragile mechanism.

Basically what happens is that a name compression function
is run over the font name, as seen in the Windows Registry,
producing a base name and a set of modifiers, with the
modifiers being the weight (as a string) and a flag
indicating whether the font appears to be italicised.

XXX This is English-specific and entirely dependent on the
    naming conventions commonly seen when naming fonts, so
    there will be a considerable number of cases where the
    resulting name and flags will be incorrect.
"""
WEIGHTS = [
    'demibold', 'extrabold', 'semibold', 'ultrabold', 'bold',
    'ultralight', 'extralight', 'light',
    'heavy',
    'medium',
    'thin',
]
IGNORE_MODIFIERS = [
    "unicode",
    "regular",
    "normal",
    "bt",
    "let",
##	"mt",
    'itc',
    "(truetype)",
    'ft',
    'win95bt',
    'plain:1.0',
    'plain',
    'plain:',
]
WEIGHT_SYNONYMS = [
    ('lt', 'light'),
    ('lite', 'light'),
    ('bolditalic','bold'),
    ('demi', 'demibold'),
    ('semi', 'semibold'),
]
WEIGHT_MODIFIERS = [
    'extra', 'ultra'
]
    

ITALIC_INDICATORS = [
    'italic', 'ital','itali', 'it', 'bolditalic',
]

def interpretModifiers( name ):
    """Heuristic attempt to get weight and italic data from font-name

    return base_font_name, (weight, italic)
    """
    name = name.replace('_',' ').replace('-',' ').lower().split()
    weight = "normal"
    for w in WEIGHTS:
        if w in name:
            weight = w
            while w in name:
                name.remove( w )
            break
    for w,syn in WEIGHT_SYNONYMS:
        if w in name:
            weight = syn
            while w in name:
                name.remove( w )
    if weight in ('bold','light'):
        # "extra bold", "extra light", etceteras
        for w in WEIGHT_MODIFIERS:
            if w in name:
                weight = w+weight
                while w in name:
                    name.remove( w )
                break
    # XXX should look for "extra" and "ultra" w/out bold/light,
    # but that that point we're basically just shooting blind
    # as to which it is...
    for i in ITALIC_INDICATORS:
        if i in name:
            italic = 1
            while i in name:
                name.remove( i )
            break
    else:
        italic = 0
    for i in IGNORE_MODIFIERS:
        while i in name:
            name.remove( i )
    name = " ".join( name )
    if not name.strip():
        # MT Extra
        raise ValueError( "name reduced to null by name compression" )
        return None,(None,None)
    return name, (weight, italic)


def add( name, file ):
    """Add a font with name and file to this module's registry"""
    name, style = interpretModifiers( name )
    if name is not None:
        SYSTEM_FONTS.setdefault(name, {})[style] = file
    return name, style
def get( name, style=None ):
    """Get a font by name and optional style

    Style defaults to ("normal", 0)
    """
    name, tstyle = interpretModifiers( name )
    if tstyle != style and style is None:
        style = tstyle
    set = SYSTEM_FONTS.get( name )
    if set:
        if set.has_key( style ):
            return set[style]
        # try match on italics
        for key, value in set.items():
            if key[1] == style[1]:
                return value
        # try match on weight
        for key, value in set.items():
            if key[0] == style[0]:
                return value
        # well, there's at least one font here, use it...
        for key, value in set.items():
            return value
    return None