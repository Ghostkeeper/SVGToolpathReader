SVG Toolpath Reader
-----------------
This is a plug-in for Cura that allows you to read an SVG file directly as g-code. The outlines of the shapes in your SVG image will get printed as outer walls.

Installation
------------
You can install this plug-in in one of four ways.
1. **Marketplace:** In Cura, go to the Marketplace and find SVG Toopath Reader in the list. Click it, then click on "install" and restart Cura.
2. **From package:** Go to the [releases](https://github.com/Ghostkeeper/SVGToolpathReader/releases) page to download the latest release. Select the SDK version that fits your version of Cura:

   | Cura version | SDK |
   |--------------|-----|
   | 3.5          | 5   |
   | 3.6          | 5   |
   | 4.0          | 6   |
   
   Drag that package file onto the Cura window, then restart Cura.
3. **Building packages:** Download the latest source code [from Github](https://github.com/Ghostkeeper/SVGToolpathReader/archive/master.zip), then in a terminal run `cmake . && make pack` to create a .curapackage file for each supported SDK version. Similar to the previous option, select the SDK version that fits your version of Cura and drag it onto the Cura window, then restart Cura.
4. **From source:** Download the latest source code [from Github](https://github.com/Ghostkeeper/SVGToolpathReader/archive/master.zip). In Cura, click on "Help", "Show configuration folder". Navigate to the "plugins" subfolder and unpack the .zip file from Github there. Rename the folder to "SVGToolpathReader" (removing any suffix that Github added such as "-master"). Restart Cura.

Usage
-----
To use this plug-in, simply load an SVG file. There are a couple of things you might want to watch out for though.
* Not all elements are supported. See the SVG Support header below for a list of what is supported.
* Curves will get sampled in segments of the Maximum Resolution. That may be too high of a sample rate for your printer to cope with.
* Unless your printer has the origin in the centre, the coordinate origin is in the back left corner of the printer. It is not the front left corner, like with g-code. This makes the image render in proper orientation. Coordinates are in millimetres.
* If you see nothing in the layer view, your image coordinates may be out of whack, causing the lines to be positioned out of view.
* There is no check for whether your print stays within the build volume. This might generate g-code that instructs the printer to go out of its build volume.
* The actual stroke width of the shape is used as the line width to print with. Common stroke widths in SVG are often too wide to print.

Settings
--------
This plug-in will use the current settings in your currently activated extruder as the settings to print with. The following settings will influence your print:

| Setting                               | Effect                                                                     |
|---------------------------------------|----------------------------------------------------------------------------|
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
* SVG (viewBox, width, height)
* rect (x, y, width, height, rx, ry)
* circle (cx, cy, r)
* g
* ellipse (cx, cy, rx, ry)
* polygon (points)
* polyline (points)
* line (x1, y1, x2, y2)
* path (d)
* style
* switch (requiredFeatures)
* defs
* use (x, y)
* text (x, y, dx, dy, rotate)

The following attributes are supported for each of these:
* stroke-width
* transform
* style

The following CSS properties are supported:
* font-family
* font-size
* font-weight
* font-style
* text-transform

Line Widths
-----------
To draw the lines, the stroke width of the actual element in SVG is used. If this line width is 0, the outer wall line width will be used. The stroke of a line width can be specified using the `stroke-width` attribute in most elements, or using the `style` attribute or `style` element. However support for CSS is very limited. Classes are not supported and may even get interpreted wrongly.