1.2.1 - Bug Fixes
====
* Fixed sometimes not skipping retractions for 0-length travels due to rounding errors.
* Fixed crash if the user clicks the buttons of the dialog multiple times in quick succession.
* Fixed parsing of paths with scientific notation in the parameters.

1.2.0 - Getting Taller
====
This update adds support for multi-layer prints.

New Features
----
* Support for repeating the print across multiple layers.
* When loading an SVG file you now get a dialogue asking you how high the print should be.
* Optimise the order of extruded paths to reduce travel distance. Contributed by Jorisa.
* Limit precision to nanometres, to reduce g-code size.

Bug Fixes
----
* Tiny movements will no longer trigger scientific-notation numbers causing retractions with the E parameter.
* Skip 0-length moves.
* Fix getting font families on some Linux installations.
* Fix inheritance of font-family CSS property.
* Fix the viewport offset if it doesn't start on 0,0.

1.1.3 - Bug Fixes
====
* Add support for Cura 4.4 using SDK version 7.0.0.

1.1.2 - Bug Fixes
====
* Use the correct unretraction speed.
* Fix the fan speed when retractions are enabled.

1.1.1 - Bug Fixes
====
* Fix loading the FreeType binary on MacOS.
* Fix detecting features with the `requiredFeatures` attribute.
* Package FreeType with the CuraPackage files.

1.1.0 - Literacy Update
====
This update adds support for text, among a few other things.

New Features
----
* Support for `defs` and `use` SVG elements.
* Support for `text` SVG elements.
* Support for `font-size` attribute.
* Support for `font-family` attribute.
* Support for `text-transform` attribute.
* Support for `stroke-dasharray` attribute.
* Support for `stroke-dashoffset` attribute.
* Support for `text-decoration-line` attribute.
* Support for `text-decoration-style` attribute.
* Support for `text-decoration` attribute.
* Support for actual lengths in `%`, `mm`, `pt`, etc. No font-size related lengths (like `em`) though.
* Support for the viewport of the SVG file.
* Generate CuraPackage files automatically with CMake.
* Installation to the latest Cura installation with CMake.

Bug Fixes
----
* Order of transformations if more than one transformation is applied to the same element.
* Sizes being relative to the viewport instead of in pure `mm`.
* Rotating around different coordinates than 0,0 was not applied correctly.
* Use the initial layer flow setting rather than normal flow.

1.0.0 - Initial Release
====
This is the initial release of SVGToolpathReader. It was designed as a way to perform accurate single-line-single-layer tests easily.

Features
----
* Reading SVG files into Cura.
* Reading SVG elements `svg`, `rect`, `circle`, `g`, `ellipse`, `polygon`, `polyline`, `line`, `path`, `style` and `switch`.
* Reading SVG attributes `stroke-width` and `transform`.
* Output the paths as g-code.
* Generate basic g-code with proper g-code headers.