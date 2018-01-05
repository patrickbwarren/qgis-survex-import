# qgis-survex-import

QGIS import plugin for survex `.3d` files.
To get going straight away, skip to the [install instructions](#qgis-plugin).

## Summary

The idea that reduced cave survey data
should be easily readable into a
Geographic Information System (GIS) platform such as
[QGIS](http://www.qgis.org/ "QGIS website") is practically a no-brainer,
as it can then be integrated
with other geographical data such as maps, satellite imagery, digital
elevation models, and the like.  Now this is much closer to being
achievable than one might think.  Here's the contents of a
typical [survex](https://survex.com/ "survex website") `.3d` file as exposed by running `dump3d`:

* survey metadata: title, date, and co-ordinate reference system;
* strings of survey legs with metadata: names,
  flags (normal, duplicate, splay, surface);
* survey stations with metadata: names, flags (exported, entrance,
  fixed, surface) and passage cross-sections (LRUD data).

Now compare this to a typical
[ESRI shapefile](https://en.wikipedia.org/wiki/Shapefile "wikipedia"),
or the
[GeoPackage](https://en.wikipedia.org/wiki/GeoPackage "wikipedia") data format
from the [Open Geospatial Consortium](https://en.wikipedia.org/wiki/Open_Geospatial_Consortium "wikipedia"),
which are well known containers for GIS vector data.  These formats specify:

* geometries comprising points, lines, polylines (line strings), and polygons,
  with or without elevation (z) data;
* geometry attributes consisting of records of various kinds
  that are user-configurable;
* a co-ordinate reference system, and possible other metadata.

Now at this point you are supposed to slap yourself on the head and
ask why on earth we haven't been using GIS shapefiles
for storing reduced survey data all along!  The format is certainly
flexible enough to contain all the information normally included in a
`.3d` file.

## Spatial Reference Systems

In order for this to work smoothly, we first have to be on top of our
[spatial reference system (SRS)](https://en.wikipedia.org/wiki/Spatial_reference_system "wikipedia")
in general GIS parlance, or co-ordinate reference system (CRS) in QGIS
language.  The following notes hopefully contain enough of the truth
to be useful.  Something closer to the truth can be found
[here](http://www.bnhs.co.uk/focuson/grabagridref/html/OSGB.pdf "OSGB.pdf").

An SRS usually comprises:

* a [geodetic datum](https://en.wikipedia.org/wiki/Geodetic_datum "wikipedia")
or reference ellipsoid which specifies the overall shape
of the earth's surface (eg
[WGS84](https://en.wikipedia.org/wiki/World_Geodetic_System "wikipedia") datum
used in GPS, or the 
[OSGB36](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid "wikipedia")
datum used by the Ordnance Survey (OS) in the UK);

* a map projection which is nearly always a
[Transverse Mercator](https://en.wikipedia.org/wiki/Transverse_Mercator_projection "wikipedia")
projection, such as the
[Universal Transverse Mercator (UTM)](https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system "wikipedia")
system used in GPS; the map projection tries to optimally flatten the
curved surface of the earth (there is always some compromise involved
here);

* a co-ordinate system defined on top of the map projection,
  typically specifying a 'false origin' so that co-ordinates are always
  positive. 

Given the geodetic datum one can always work with latitudes and
longitudes, but these aren't terribly convenient for cave survey data
crunching.  Also beware that the same point on the earth's surface may
have a different latitude and longitude depending on the reference
datum: this difference is known as a datum shift, and a well-known
example is the 
[datum shift between WGS84 and OSGB36](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid#Datum_shift_between_OSGB_36_and_WGS_84 "wikipedia")
that nowadays only shows up in
[Magic Map](http://www.natureonthemap.naturalengland.org.uk/MagicMap.aspx "Magic Map").
Modern usage nearly always corresponds to the WGS84 datum, which is
pretty much universally used nowadays.  For example it's used in
[Google Earth](https://en.wikipedia.org/wiki/Google_Earth "wikipedia")
and in fact Google's
[Keyhole Markup Language (KML)](https://developers.google.com/kml/ "Google KML")
only supports WGS84 latitude and longitude.
Most GPS devices will report WGS84 latitude and longitude, though
more often than not you won't see this directly but rather get metric
UTM co-ordinates, or metric British National Grid co-ordinates.

To further add to the confusion, latitude and longitude can be
reported in decimal degrees; or degrees, minutes, and seconds (or
even degrees and decimal minutes).  For example the entrance
to Dow Cave is at NGR SD&nbsp;98378&nbsp;74300 (see below),
which translates to
(WGS84) 54&deg;&nbsp;9'&nbsp;52.2"&nbsp;N 2&deg;&nbsp;1'&nbsp;34.8"&nbsp;W
in deg / min / sec (where one decimal place in the seconds corresponds to approximately 3m on the ground),
or (WGS84) 54.16450&deg;&nbsp;N 2.02634&deg;&nbsp;W in decimal degrees
(where five decimal places corresponds approximately to
1m on the ground).
Online converters between British National Grid references and
WGS84 latitudes and logitudes can be found on the internet by searching
for 'OSGB36 to WGS84 converter'.  To check things,
the WGS84 latitude and longitude in
decimal degrees can be copied and pasted into Google maps for example, or for
that matter directly into the Google search engine.

In the UK, Ordnance Survey (OS)
[British National Grid](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid "wikipedia")
co-ordinates provide a metric SRS which is convenient for cave survey data.
Typically one fixes cave entrances using the numeric part of the national
grid reference (NGR).
NGRs can be specified in two ways.  The most convenient way is to use the OS grid
letter system in which a pair of letters specifies a 100km &times;
100km square.  Then within that a 10-figure national grid reference
(NGR) specifies a location to within a square metre.  This system (two
letters plus 10 figures) is what is usually encountered when using a GPS
device set to the British National Grid.  Many datasets in the
Cave Registry have entrance fixes specified as 10-fig NGRs, without the grid letters which are assumed known.

Alternatively, and more commonly in GIS, one can use an
all-numeric 12-figure NGR in which the leading figures signal the 100
km &times; 100 km square numerically.
For example as in the all-numeric scheme the entrance to Dow Cave is at NGR
398378&nbsp;474300.

In the letter-based system the co-ordinates are often
truncated to 8-fig or 6-fig NGRs, to reflect the accuracy of the GPS
device for instance (thus 8-fig NGRs are used in the new Northern
Caves).  In case you forgot your school geography lessons, recall that the
correct way to truncate an NGR is to _drop_ the least significant
figures, not to round to the nearest 10 or 100.  This is because
an 8-fig (or 6-fig) NGR actually specifies a 10m &times; 10m (or 100m
&times; 100m) _square_ and not an approximate position as such.  Thus
the 6-fig NGR for the Dow Cave entrance is NGR SD&nbsp;983&nbsp;743.

To check NGRs in the UK, one can use the 'Where am I?' tool in the
[Magic Map](http://www.natureonthemap.naturalengland.org.uk/MagicMap.aspx "Magic Map")
application.  Note that unless explicitly
set to use the WGS84 datum, Magic Map reports latitude and longitude
in the OSGB36 datum, which as mentioned is offset from WGS84 by a
datum shift of up to 50-100m.  Beware copying and pasting these OSGB36
latitudes and longitudes into Google Maps!

Elsewhere in the world, or for that matter in the UK as well, the UTM
system offers a convenient metric SRS for embedding cave survey data.
Typically one fixes the entrance co-ordinates as the numeric part of
the UTM position, making a note of the UTM grid zone.  Online
converters from WGS84 latitude and longitude to UTM or back are easily
found.  For example, the Dow Cave entrance in the UTM scheme is UTM
(WGS84) 30U&nbsp;6002262&nbsp;563570.  Perhaps it's restating the
obvious but if you accidentally paste
OSGB36 latitudes and longitudes into a UTM
converter, you will likely be out by 50-100m.


## Georeferencing cave survey data

Back to cave surveying: for most surveys the earth's surface can be
regarded as essentially flat, so one is working in a 3d world with
eastings, northings, and altitudes, with the origin of the co-ordinate
system chosen at one's convenience.  Perhaps for synoptic maps of very
large karst areas, one might be worried about the curvature of the
earth's surface, but for the most part assuming the world is flat
should introduce negligible errors, at least in comparison to the
errors that typically creep into cave survey projects.

As long as this local cave co-ordinate system can be tied into one of
the known geodetic SRS schemes (ie
[_georeferenced_](https://en.wikipedia.org/wiki/Georeferencing "wikipedia")),
then any feature in the cave will have a known position in GIS terms,
and can thus be tied into any other georeferenced data such as maps,
satellite imagery, digital elevation models, etc.  Given that most
cave surveying is done in metres, it is obviously convenient to tie
into an SRS which uses metric co-ordinates, such as UTM or British
National Grid.  Note that once you've tied the dataset into a
recognised SRS, any GIS platform worth its salt will be able to
re-project into a different SRS, and will be able to display and
combine information from different sources irrespective of the SRS.

The easiest way to georeference cave survey data, with a modern
survex distribution, is to `*fix` cave entrances with appropriate
co-ordinates and make judicious use of the `*cs` commands (for co-ordinate system):
use a plain `*cs` command to specify the input SRS that the entrance
co-ordinates are given in, and a `*cs out`
command to specify what the output SRS should be.  In
the UK for instance one can use this to convert between the OS grid
letter system and the all-numeric scheme.

The cave survey data used in the examples below is included in the
repository under the `DowProv` directory.  It is for the
[Dow Cave - Providence Pot system](http://www.mudinmyhair.co.uk/ "Mud in My Hair")
(Great Whernside, Wharfedale, UK), and is
essentially a snapshot of the data held in the
[Cave Registry Data Archive](http://cave-registry.org.uk/ "Cave Registry").
Note that the `.svx` files have
[unix-style line endings](https://en.wikipedia.org/wiki/Newline "wikipedia")
so on Windows you might have to use something like
[Notepad++](https://notepad-plus-plus.org/ "Notepad++")
to look at them.  The processed data is `DowProv.3d`, generated using
survex 1.2.32.

Back to georeferencing, the cave-specific
file `DowCave.svx` (for example) contains
```
*begin DowCave
*export entrance
...
*entrance entrance
*fix entrance 98378 74300 334
*equate entrance dow1.1
...
```
and the master file `DowProv.svx` contains
```
*cs OSGB:SD
*cs out EPSG:27700
...
*begin DowProv
*include DowCave
...
```
(obviously this is only one of many possible ways
to add the metadata into the survex files).

Thus the file `DowCave.svx` contains a `*fix` which specifies the entrance
location as a 10-fig NGR `SD 98378 74300`, without the `SD` part.  The
easting and northing here (and elevation
[OSDN](https://en.wikipedia.org/wiki/Ordnance_datum "wikipedia"))
were obtained by field work.
Then the file `DowProv.svx` specifies input SRS is the OS GB SD square, and
asks that the reduced data should be exported using the all-numeric British
National Grid scheme, here codified with a
[European Petroleum Survey Group (EPSG)](http://spatialreference.org/ "spatial reference website")
code.  Using EPSG numbers avoids
potential misunderstanding when importing into a GIS platform, for
example in QGIS one can find the exact exported SRS
easily enough by searching on
the EPSG number.

If you check the processed survey in `aven`, or run `3dtopos` on the `.3d` file,
the processed entrance co-ordinates are now indeed
```
(398378.00, 474300.00,   334.00 ) dowprov.dowcave.dow1.1
```
Whilst this may seem like a crazily over-the-top
way to add a '3' and '4' to the entrance co-ordinates, it is actually very simple to implement:
one only needs to add two lines (the `*cs` and `*cs out` commands) to the survex file.
The benefit is that it is robust, clean, and unambiguous.  Moreover, the output SRS
is included as metadata in the `.3d` file; thus with `dump3d` one sees
```
CS +init=epsg:27700 +no_defs
```
(this is in fact a [PROJ.4](http://proj4.org/ "proj4 website")
string which species the map projection, and can be directly
pushed to a GIS application).

As a slightly less trivial example, one can ask for the reduced survey
data to be re-projected as UTM co-ordinates.  This can be done almost
totally trivially by replacing the previous `*cs out` command with
`*cs out EPSG:32630` which specifies the output SRS is (WGS84) UTM
zone 30N (this includes zone 30U).  If we now
reduce the data with `cavern` and check with `3dtopos` we find the Dow Cave
entrance has magically moved to
```
(563570.22, 6002262.20,   384.57 ) dowprov.dowcave.dow1.1
```
and the exported SRS from `dump3d` is
```
CS +init=epsg:32630 +no_defs
```
As expected, the entrance location in UTM
is the same as obtained by converting the original NGR first
to WGS84 latitude and longitude, then to UTM, using the online converters.  Note
that in re-projecting to UTM, we also get a vertical datum shift.

For another example, the CUCC Austria data set which comes as sample
data with the survex distribution can be georeferenced 
by adding the following to the top of the `all.svx` file: 
```
*cs custom "+proj=tmerc +lat_0=0 +lon_0=13d20 +k=1 +x_0=0 +y_0=-5200000 +ellps=bessel +towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +units=m +no_defs"
*cs out EPSG:31255
```
The first line specifies the custom SRS in which the co-ordinates of
the surface fixed points in the Austria data set are specified.  The
second line determines the output SRS.  This doesn't really matter to
much as long as the SRS can be recognised by the GIS platform: this
example uses the MGI / Austria Gauss-Kruger (GK) Central SRS
(EPSG:31255), where the _only_ difference compared to custom SRS is in
the y_0 false origin.  Another sensible output SRS would be `EPSG:32633`
which is (WGS84) UTM zone 33N.

I've gone into these examples in some detail as the
survex documentation on the `*cs` command is rather spartan.

As a further benefit, providing the survex data files include correctly
formatted `*date` commands (as the Dow-Providence dataset does), 
the `*cs` commands make survex aware of the geodetic SRS and
magnetic declination corrections can be automatically added.  This is
another reason one might want to 'do things properly' with `*cs`
commands.  The `DowProv.svx` master file thus also contains the lines
(the first two are just comments)
```
; Mag dec calculated for SD 97480 72608
;(Dowbergill Bridge, just above Kettlewell)

*declination auto 97480 72608 225
```
This correctly applies the magnetic declination using the
[International Geomagnetic Reference Field (IGRF)](https://en.wikipedia.org/wiki/International_Geomagnetic_Reference_Field "wikipedia") model, 
calculated at the specified location in the input
SRS, and applied to _all_ the included survey files,
in this case taking into account 
the range of dates which spans some 30 years.

## GIS import methods

### Quick-and-dirty two dimensional (flat) import

The quickest way to get survey data into a GIS platform (QGIS) once
the dataset has been georeferenced as just described is via the DXF
file format, using the survex `cad3d` tool, or exporting from `aven`.
One can load this DXF file into a GIS platform like QGIS.  At present
this direct route does not import z-dimension (elevation) data, but
nevertheless could be useful as a quick and dirty way to throw for
example a centreline onto a map.

### Three dimensional import

From the DXF file, the centreline can be extracted by running (at the
command line)
```
ogr2ogr -f "ESRI Shapefile" DowProv_centreline.shp DowProv.dxf -where "Layer='CentreLine'" -a_srs EPSG:27700
```

We take the opportunity here to add an SRS to match that used in the
georeferenced survey data.  The resulting shapefile can then be
imported in QGIS, and this route _does_ preserve z-dimension
(elevation) data.
Thus, for example, one can run the
[Qgis2threejs](https://plugins.qgis.org/plugins/Qgis2threejs/ "Qgis2threejs plugin")
plugin with a suitable digital elevation model (DEM) raster to
generate a three dimensional view with the cave features
underneath the landscape.

Similarly the stations with labels (and elevations)
can be extracted by running
```
ogr2ogr -f "ESRI Shapefile" DowProv_stations.shp DowProv.dxf -where "Layer='Labels'" -a_srs EPSG:27700
```

This import route requires command-line access to the
[GDAL utilities](http://www.gdal.org/ogr_utilities.html "gdal.org").

### Import using QGIS plugin

The plugin provides a convenient route to import features (legs and
stations) from a `.3d` file, with z-dimension (elevation) and other
metadata properly included.

To install the plugin, clone or download this repository and copy the
`SurvexImport` directory into the QGIS python plugins directory, which is
usually `~/.qgis2/python/plugins` (where `~` on Windows is probably
`C:\Users\<user>`).  

When installed, a menu item 'Import .3d file' should appear on the
'Vector' drop-down menu in the main QGIS window.  Running this, a
pop-up window appears for the user to select a `.3d` file, and chose
whether to import legs or stations , or both.  For the former (legs)
additional options allow the user to chose whether to include splay,
duplicate, and surface legs.  For the latter (stations) the user can
chose whether to include surface stations.  Finally there is an option
to import the CRS from the `.3d` file if possible (see below).

On clicking OK, vector layers are created to contain the legs and
stations as desired.  The CRS is requested for each layer if not
picked up from the file.  Some attributes are also imported (most
usefully perhaps, names for stations).

There is one point to bear in mind.  Because of the (current)
limitations in QGIS for creating vector layers in memory, the layer type does
not explicitly know that the features include z-dimension
(elevation) data.  Thus, for example, running the Qgis2threejs plugin
doesn't quite work as expected.  To work around this one can save the layer
to a shapefile, for example to an ESRI Shapefile or a GeoPackage file.
(In QGIS this usually results in the saved shapefile automatically
being loaded as a new vector layer, or of course one can explicitly
load the new shapefile.)  To ensure the z-dimension data is correctly
incorporated when saving to a shapefile, in the 'Save as ...'  dialog
make sure that the geometry type is specified (for legs this should be
'LineString', and for stations it should be 'Point') and the 'Include
z-dimension' box is checked.  A new vector layer created this way can
then be used with Qgis2threejs for example.

Regardless of the above, features (legs or stations) in the created
layers can be coloured by depth to mimic the behaviour of the `aven`
viewer in survex (hat tip Julian Todd for figuring this out).  The
easiest way to do this is to use the `.qml` style files provided in
this repository.  For example to colour legs by depth, open the
properties dialog and under the 'Style' tab, at the bottom select
'Style --> Load Style', then choose the `color_legs_by_depth.qml`
style file.  This will apply a graduated colour scheme with an
inverted spectral colour ramp.  A small limitation is that the ranges
are not automatically updated to match the vertical range of the
current data set.  Refreshing this is trivial: simply fiddle with the
number of 'Classes' (box on right hand side of 'Style' tab) and the ranges
will update to match the current dataset.

For the most part importing the CRS from the `.3d` file should work as
expected if the survey data has been georeferenced as suggested above.
If it doesn't, one can always uncheck this option and set the CRS by
hand.  To maximise the likelihood that CRS import works as expected, use an
EPSG code in the `*cs out` survex command rather than a PROJ.4 string.

#### Platform-specific location of dump3d

The plugin uses `dump3d` to dump the contents of the
`.3d` file to text, and obviously will fail if it can't find `dump3d`,
or there is a survex version mismatch (most likely, by trying to
import a `.3d` file 'from the future' with an older survex
installation).

If you have a non-standard survex installation you can edit
`survex_python.py` to add an entry for the platform-specific location
of the `dump3d` executable.  The place to look is where a
dictionary of platform-specific executables is defined:
```
dump3d_dict = {'Linux' : '/usr/bin/dump3d',
               'Windows' : 'C:\Program Files (x86)\Survex\dump3d'}
```
The keys here are the return values of a call to `platform.system()`.
At the moment this dictionary lacks an entry for MAC OS X (eg
`'Darwin' : '...'`) but this will be fixed at some point.

###  Other import scripts

In the `extra` directory, the script `import3d.py` is a stripped down
version of the plugin which could be useful for testing and
troubleshooting.  It can be added as a user script to the Processing
Toolbox.

Also in the `extra` directory, `survex_import_with_tmpfile.py` is a
slightly old version of the main plugin script which uses a temporary
file to cache the output of `dump3d`.

## Notes on georeferencing images, maps, and old surveys

Georeferencing here refers to assigning a co-ordinate system to an
image or map, or a scanned hard copy of a survey.  The actual steps
require identifying so-called Ground Control Points (GCPs), which are
identifiable features on the map for which actual co-ordinates are
known.  One way to do this is to use the [GDAL Georeferencer](https://docs.qgis.org/2.8/en/docs/user_manual/plugins/plugins_georeferencer.html "qgis.org")
plugin in QGIS.
Then, a useful way to extract co-ordinates for GCPs can be to install the
[OpenLayers](https://plugins.qgis.org/plugins/openlayers_plugin/ "qgis.org")
plugin which allows one to pull down data from Open
Street Map, Google Maps, and so on.  In particular, one can pull down
satellite imagery into QGIS and use the option to set the GCP
co-ordinates from the QGIS main window.  Georeferencing then becomes
quick and easy, for example finding 2-3 wall corners or other features
on the image, and set their co-ordinates by simply clicking on the
same features in the main window (make sure the SRS in the main window
is set to what you want though).

Georeferencing surveys may be easier if there is more than one
entrance and the positions are known, or there is already a surface
grid.  If there is only one entrance then tracing a centerline in
Inkscape and using the survex output tool as described
[here](https://github.com/patrickbwarren/inkscape-survex-export "GitHub")
may help.

### Copying

These notes are licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/ "CC BY-NC-SA 4.0").
That is to say for the most part you are free to copy and use them in
a non-commercial setting.

Code in this repository is licensed under GLPv2:

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

Copyright &copy; (2017) Patrick B Warren.


