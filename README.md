SVGToolpathReader
-----------------
This is a plug-in for Cura that allows you to read an SVG file directly as g-code. The outlines of the shapes in your SVG image will get printed as outer walls.

Settings
--------
This plug-in will use the current settings in your currently activated extruder as the settings to print with. The following settings will influence your print:

| Setting                               | Effect                                                                     |
| --------------------------------------|----------------------------------------------------------------------------|
| Initial Layer Height                  | This will be used as the height of your layer.                             |
| Flow                                  | Adjusts the amount of material extruded linearly.                          |
| Diameter                              | Compute the correct length of filament to extrude.                         |
| Initial Layer Travel Speed            | The speed at which travel moves are made.                                  |
| Initial Layer Print Speed             | The speed at which all lines are printed.                                  |
| Enable Retraction                     | Whether all travel moves should be made with filament retracted.           |
| Retraction Distance                   | How far to retract.                                                        |
| Retraction Retract Speed              | The speed at which to retract the filament.                                |
| Retraction Prime Speed                | The speed at which to unretract the filament.                              |
| Outer Wall Line Width                 | The line width used for shapes that don't specify a line width themselves. |
| Outer Wall Acceleration               | The acceleration to use throughout the print (also for travel moves).      |
| Outer Wall Jerk                       | The jerk to use throughout the print (also for travel moves).              |
| Maximum Resolution                    | Length of segments in all curves.                                          |
| Printing Temperature Initial Layer    | The temperature at which to print.                                         |
| Build Plate Temperature Initial Layer | The build plate temperature during the print.                              |
| Enable Prime Blob                     | Whether or not to prime before the print.                                  |
| Extruder Prime X Position             | The X coordinate of where to prime.                                        |
| Extruder Prime Y Position             | The Y coordinate of where to prime.                                        |

SVG Support
-----------
Not all elements of the SVG specification will be printed. For some things, this is intended. For instance, all fills, gradients, glow effects, etc. should not be printed. For other things they may just not be supported yet. The following elements are currently supported:
* SVG
* rect (x, y, width, height, rx, ry)
* circle (cx, cy, r)
* g
* ellipse
* polygon
* polyline
* line
* path
* style
* switch

The following attributes are supported for each of these:
* stroke-width
* transform

Line Widths
-----------
To draw the lines, the stroke width of the actual element in SVG is used. If this line width is 0, the outer wall line width will be used. The stroke of a line width can be specified using the `stroke-width` attribute in most elements, or using the `style` attribute. However support for CSS is very limited. Only inline `style` attributes are currently supported, no classes and no style elements.