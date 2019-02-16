SVGToolpathReader
-----------------
This is a plug-in for Cura that allows you to read an SVG file directly as g-code. The outlines of the shapes in your SVG image will get printed as outer walls.

Settings
--------
This plug-in will use the current settings in your currently activated extruder as the settings to print with. The following settings will influence your print:

| Setting                | Effect                                                                     |
| -----------------------|----------------------------------------------------------------------------|
| Initial Layer Height   | This will be used as the height of your layer.                             |
| Flow                   | Adjusts the amount of material extruded linearly.                          |
| Diameter               | Compute the correct length of filament to extrude.                         |
| Travel Speed           | The speed at which travel moves are made.                                  |
| Outer Wall Print Speed | The speed at which all lines are printed.                                  |
| Outer Wall Line Width  | The line width used for shapes that don't specify a line width themselves. |
| Maximum Resolution     | Length of segments in all curves.                                          |

SVG Support
-----------
Not all elements of the SVG specification will be printed. For some things, this is intended. For instance, all fills, gradients, glow effects, etc. should not be printed. For other things they may just not be supported yet. The following elements are currently supported:
* SVG
* rect (x, y, width, height, rx, ry)
* circle (cx, cy, r)

Line Widths
-----------
To draw the lines, the stroke width of the actual element in SVG is used. If this line width is 0, the outer wall line width will be used. The stroke of a line width can be specified using the `stroke-width` attribute in most elements, or using the `style` attribute. However support for CSS is very limited. Only inline `style` attributes are currently supported, no classes and no style elements.