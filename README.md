# QGIS plugin to import survex .3d files

_Requires QGIS &ge; 2.14 for QgsPointV2, and a .3d file processed typically by survex &ge; 1.2.14 to report CRS._

_The current version reads .3d files directly and doesn't require survex to be installed to load data._

This QGIS plugin provides a convenient route to import features (legs and
stations) from a [survex](https://survex.com/ "survex.com")
`.3d` file, with z-dimension (elevation) and other
metadata properly included.

To install the plugin:

* clone or download this repository and copy the `SurvexImport`
directory into the QGIS python plugins directory, which is usually
`~/.qgis2/python/plugins` (where `~` on Windows is probably
`C:\Users\<user>`);

* run QGIS and enable the plugin by going to 'Plugins &rarr; Manage and
  Install Plugins...' and make sure the box next to 'Import .3d file'
  is checked.

When installed, a menu item 'Import .3d file' should appear on the
'Vector' drop-down menu in the main QGIS window, and (possibly) a
`.3d` icon in a toolbar (if enabled).

Selecting 'Import .3d file' (or clicking on the .3d icon) brings up a
window for the user to select a `.3d` file, and choose whether to
import legs or stations, or both.  For the former (legs) additional
options allow the user to choose whether to include splay, duplicate,
and surface legs.  For the latter (stations) the user can choose
whether to include surface stations (in rare cases a station may be
flagged both surface and underground, in which case it is imported
even if this option is left unchecked).  Finally there is an option to
import the CRS from the `.3d` file if possible.  On clicking OK,
vector layers are created to contain the legs and stations as desired.

Attribute fields that are created are:

* stations: NAME, and flags SURFACE, UNDERGROUND, ENTRANCE, EXPORTED, FIXED, ANON

* legs: NAME, STYLE, DATE1 and DATE2, and flags SURFACE, DUPLICATE, SPLAY

The flag fields are integer fields set to 0 or 1.  For the leg data,
the style is one of NORMAL, DIVING, CARTESIAN, CYLPOLAR, or NOSURVEY,
and the date fields are either the same, or represent a date range, in
the standard QGIS format YYYY-MM-DD.

For the most part importing the CRS from the `.3d` file should work as
expected if the survey data has been georeferenced using the survex
`*cs` and `*cs out` commands.  If it doesn't, one can always uncheck
this option and set the CRS by hand.  To maximise the likelihood that
CRS import works as expected, use an EPSG code in the `*cs out` survex
command rather than a PROJ.4 string.

There is one point to bear in mind regarding the elevation data.
Because of the (current) limitations in QGIS for creating vector
layers in memory, the layer type does not explicitly know that the
features include z-dimension (elevation) data.  To work around this
one can save the layer to a shapefile, for example to an ESRI
Shapefile or a GeoPackage file.  In QGIS this usually results in the
saved shapefile automatically being loaded as a new vector layer, but
of course one can also explicitly load the new shapefile.  To ensure
the z-dimension data is correctly incorporated when saving to a
shapefile, in the 'Save as ...'  dialog make sure that the geometry
type is specified (for legs this should be 'LineString', and for
stations it should be 'Point') and the 'Include z-dimension' box is
checked.

Once the data is in QGIS one can do various things with it.

For example, regardless of the above comments about saving with
z-dimension data, features (legs or stations) can be coloured by depth
to mimic the behaviour of the `aven` viewer in survex (hat tip Julian
Todd for figuring this out).  The easiest way to do this is to use the
`.qml` style files provided in this repository.  For example to colour
legs by depth, open the properties dialog and under the 'Style' tab,
at the bottom select 'Style &rarr; Load Style', then choose the
`color_legs_by_depth.qml` style file.  This will apply a graduated
colour scheme with an inverted spectral colour ramp.  A small
limitation is that the ranges are not automatically updated to match
the vertical range of the current data set.  Refreshing this is
trivial: simply fiddle with the number of 'Classes' (box on right hand
side of 'Style' tab) and the ranges will update to match the current
dataset.

Colour legs by date is possible using an expression like
`day(age("DATE1",'1970-01-01'))` (which gives the number of days
between the recorded DATE1 and the given date), with a graduated style
colouring scheme.

Another thing one can do is enable 'map tips', for example to use the
NAME field.  Then, hovering the mouse near a station (or leg) will
show the name as a pop-up label.  For this to work:

* 'View &rarr; Map Tips' should be checked in the main menu;
* the map tip has to be set up ('Properties &rarr; Display') in the relevant layer;
* the layer has to be the currently _selected_ one, though it does not have to be displayed.

With a digital elevation model (DEM raster layer) one can use the
'Raster Interpolation' plugin to find the surface elevation at all the
imported stations (to do this, first create a field to hold the
numerical result, then run the plugin).  Then, one can use the
built-in field calculator to make another field containing the _depth
below surface_, as the surface elevation minus the z-dimension of the
station, `z($geometry)`.  This information can be added to the
'map tip', etc.

Sample georeferenced survey data can be found in
[`DowProv.3d`](DowProv/DowProv.3d).

Further notes on cave surveying and GIS are in 
[`cave_surveying_and_GIS.pdf`](cave_surveying_and_GIS.pdf).

### Roadmap

The current version reads the (binary) `.3d` file directly rather than
relying on `dump3d`, thus eliminating this explicit survex dependency.
Currently, _all_ the data fields in the file are read (this has to
be the case otherwise the file reader would get out of sync), however
some data fields are unused at present:

* data on misclosure errors;
* LRUD passage wall data.

Unfortunately these are only indirectly georeferenced.

From the LRUD data one might try to build a polygon layer.  At present
it seems to me this might best be done by a 'downstream' QGIS
processing script, rather than adding to the functionality of the
`.3d` plugin (the principle being to focus on importing the basic data
into QGIS, then use QGIS to make derived features and
attributes).

Finally, as this is aimed squarely at importing survex `.3d`
files, I have no plans to extend _this_ plugin to other cave survey
data formats which would be better served by _separate_ plugins (at
least, it seems that way to me!).  If developing these, of course feel
free to re-use any of the present code under the GPL terms.

### Copying

Code in this repository is licensed under GLP v2:

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see
<http://www.gnu.org/licenses/>.

### Copyright

The `.3d` file parser is based on a GPL v2 library to handle Survex 3D files (`*.3d`),
copyright &copy; 2008-2012 Thomas Holder, http://sf.net/users/speleo3/; 
see https://github.com/speleo3/inkscape-speleo.

Modifications and extensions to import to QGIS copyright &copy; (2017, 2018) Patrick B Warren.


