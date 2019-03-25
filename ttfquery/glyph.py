"""Representation of a single glyph including contour extraction"""
from ttfquery import glyphquery
import numpy

class Glyph( object):
    """Object encapsulating metadata regarding a particular glyph"""
    def __init__(self, glyphName ):
        """Initialize the glyph object

        glyphName -- font's glyphName for this glyph, see
            glyphquery.glyphName() for extracting the
            appropriate name from character and encoding.
        """
        self.glyphName = glyphName
    def compile( self, font, steps = 3 ):
        """Compile the glyph to a set of poly-line outlines"""
        self.contours = self.calculateContours( font )
        self.outlines = [
            decomposeOutline(contour,steps)
            for contour in self.contours
        ]
        self.width = glyphquery.width( font, self.glyphName )
        self.height = glyphquery.lineHeight( font )
    
    def calculateContours( self, font ):
        """Given a character, determine contours to draw

        returns a list of contours, with each contour
        being a list of ((x,y),flag) elements.  There may
        be only a single contour.
        """
        glyf = font['glyf']
        charglyf = glyf[self.glyphName]
        return self._calculateContours( charglyf, glyf, font )
    def _calculateContours( self, charglyf, glyf, font ):
        """Create expanded contour data-set from TTF charglyph entry

        This is called recursively for composite glyphs, so
        I suppose a badly-formed TTF file could cause an infinite
        loop.

        charglyph -- glyf table's entry for the target character
        glyf -- the glyf table (used for recursive calls)
        """
        charglyf.expand( font ) # XXX is this extraneous?
        contours = []
        if charglyf.numberOfContours == 0:
            # does not display at all, for instance, space
            pass
        elif charglyf.isComposite():
            # composed out of other items...
            for component in charglyf.components:
                subContours = self._calculateContours(
                    glyf[component.glyphName],
                    glyf,
                    font
                )
                dx,dy = component.getComponentInfo()[1][-2:]
                # XXX we're ignoring the scaling/shearing/etceteras transformation
                # matrix which is given by component.getComponentInfo()[1][:4]
                subContours = [
                    [((x+dx,y+dy),f) for ((x,y),f) in subContour]
                    for subContour in subContours
                ]
                contours.extend(
                    subContours
                )
        else:
            flags = charglyf.flags
            coordinates = charglyf.coordinates
            # We need to convert from the "end point" representation
            # to a distinct contour representation, requires slicing
            # each contour out of the list and then closing it
            last = 0
            for e in charglyf.endPtsOfContours:
                set = map(
                    None,
                    list(coordinates[last:e+1])+list(coordinates[last:last+1]),
                    list(flags[last:e+1])+list(flags[last:last+1])
                )
                contours.append( set )
                last = e+1
            if coordinates[last:]:
                contours.append( map(
                    None,
                    list(coordinates[last:])+list(coordinates[last:last+1]),
                    list(flags[last:])+list(flags[last:])
                ) )
        return contours
        
def decomposeOutline( contour, steps=3 ):
    """Decompose a single TrueType contour to a line-loop

    In essence, this is the "interpretation" of the font
    as geometric primitives.  I only support line and
    quadratic (conic) segments, which should support most
    TrueType fonts as far as I know.

    The process consists of first scanning for any multi-
    off-curve control-point runs.  For each pair of such
    control points, we insert a new on-curve control point.

    Once we have the "expanded" control point array we
    scan through looking for each segment which includes
    an off-curve control point.  These should only be
    bracketed by on-curve control points.  For each
    found segment, we call our integrateQuadratic method
    to produce a set of points interpolating between the
    end points as affected by the middle control point.

    All other control points merely generate a single
    line-segment between the endpoints.
    """
    # contours must be closed, but they can start with
    # (and even end with) items not on the contour...
    # so if we do, we need to create a new point to serve
    # as the midway...
    if len(contour)<3:
        return ()
    set = contour[:]
    def on( ((Ax,Ay),Af) ):
        """Is this record on the contour?"""
        return Af==1

    def merge( ((Ax,Ay),Af), ((Bx,By),Bf)):
        """Merge two off-point records into an on-point record"""
        return (((Ax+Bx)/2.0),((Ay+By))/2.0),1
    # create an expanded set so that all adjacent
    # off-curve items have an on-curve item added
    # in between them
    last = contour[-1]
    expanded = []
    for item in set:
        if (not on(item)) and (not on(last)):
            expanded.append( merge(last, item))
        expanded.append( item )
        last = item
    result = []
    last = expanded[-1]
    while expanded:
        assert on(expanded[0]), "Expanded outline doesn't have proper format! Should always have either [on, off, on] or [on, on] as the first items in the outline"
        if len(expanded)>1:
            if on(expanded[1]):
                # line segment from 0 to 1
                result.append( expanded[0][0] )
                #result.append( expanded[1][0] )
                del expanded[:1]
            else:
                if len(expanded) == 2:                          #KH
                    assert on(expanded[0]), """Expanded outline finishes off-curve""" #KH
                    result.append( expanded[1][0] )         #KH
                    del expanded[:1] 
                    break
                assert on(expanded[2]), "Expanded outline doesn't have proper format!"
                points = integrateQuadratic( expanded[:3], steps = steps )
                result.extend( points )
                del expanded[:2]
        else:
            assert on(expanded[0]), """Expanded outline finishes off-curve"""
            result.append( expanded[0][0] )
            del expanded[:1]
    result.append( result[-1] )
    return result
def integrateQuadratic( points, steps=3 ):
    """Get points on curve for quadratic w/ end points A and C

    Basis Equations are taken from here:
        http://www.truetype.demon.co.uk/ttoutln.htm

    This is a very crude approach to the integration,
    everything is coded directly in Python, with no
    attempts to speed up the process.

    XXX Should eventually provide adaptive steps so that
        the angle between the elements can determine how
        many steps are used.
    """
    step = 1.0/steps
    ((Ax,Ay),_),((Bx,By),_),((Cx,Cy),_) = points
    result = [(Ax,Ay)]
    ### XXX This is dangerous, in certain cases floating point error
    ## can wind up creating a new point at 1.0-(some tiny number) if step
    ## is sliaghtly less than precisely 1.0/steps
    for t in numpy.arange( step, 1.0, step ):
        invT = 1.0-t
        px = (invT*invT * Ax) + (2*t*invT*Bx) + (t*t*Cx)
        py = (invT*invT * Ay) + (2*t*invT*By) + (t*t*Cy)
        result.append( (px,py) )
    # the end-point will be added by the next segment...
    #result.append( (Cx,Cy) )
    return result