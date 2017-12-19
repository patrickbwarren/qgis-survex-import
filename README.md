# qgis-survex-import
Planned QGIS import plugin for survex 3d files

## Summary

The idea is that a survex `.3d` file should be easily readable into a
Geographic Information System (GIS) platform, such as
[QGIS](http://www.qgis.org/ "QGIS website"), then it can be integrated
with other geographical data such as maps, satellite imagery, digital
elevation models, and the like.  Now this is much closer to being
achievable than one might think.  Here's the contents of a
typical (modern) `.3d` file as exposed by running `dump3d`:

* survey metadata: title, date, and co-ordinate reference system;
* traverses (strings of survey legs) with metadata: names,
  flags (normal, duplicate, splay, surface);
* stations (points) with metadata: names, flags (exported, entrance,
  fixed, surface) and passage cross-sections (LRUD data).

Now compare this to a typical
[ESRI shapefile](https://en.wikipedia.org/wiki/Shapefile "wikipedia")
which is well known container for GIS vector data.  It specifies:

* geometries comprising points, polylines (line strings), and polygons, with or
  without elevation (z) data;
* geometry attributes consisting of records of various kinds that are user-configurable;
* a co-ordinate reference system, and possible other metadata.

Now at this point you are supposed to slap yourself on the head and
ask why on earth we haven't been using ESRI shapefiles for storing
survex output data all along!  Both are binary formats, and shapefiles
are certainly flexible enough to contain all the information normally
included in a `.3d` file.

## Co-ordinate Reference Systems

In order for this to work smoothly, we first have to be on top of our
co-ordinate reference system (CRS), or
[spatial reference system (SRS)](https://en.wikipedia.org/wiki/Spatial_reference_system "wikipedia").
In GIS parlance, this is basically a co-ordinate-based scheme for
locating geographical features.  The following notes hopefully contain
enough of the truth to be useful.

A CRS usually comprises:

* a [geodetic datum](https://en.wikipedia.org/wiki/Geodetic_datum "wikipedia")
or reference ellipsoid which specifies the overall shape
of the earth's surface (eg
[WGS84](https://en.wikipedia.org/wiki/World_Geodetic_System "wikipedia")
used in GPS, or the Airy ellipsoid
[OSGB36](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid "wikipedia")
used by the Ordnance Survey in the UK);

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
[datum shift between WGS84 and OSGB36](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid "wikipedia")
that nowadays only shows up in
[Magic Map](http://www.natureonthemap.naturalengland.org.uk/MagicMap.aspx "Magic Map").
Modern usage nearly always corresponds to the WGS84 datum, which is
pretty much universally used on the web so far as I know.  It is also used in
[Google Earth](https://en.wikipedia.org/wiki/Google_Earth "wikipedia")
and in fact Google's
[Keyhole Markup Language (KML)](https://developers.google.com/kml/ "Google")
only supports WGS84 latitude and longitude.
Most GPS devices will report WGS84 latitude and longitude, though
more often than not you won't see this directly but rather get metric
UTM co-ordinates, or metric British National Grid co-ordinates.

In the UK, Ordnance Survey (OS) British National Grid co-ordinates can
be specified in two ways.  The most common way is to use the OS grid
letter system which uses a pair of letters to specify a 100km &times; 100km
square.  Then within that a 10-figure national grid reference (NGR)
specifies a location to within a square metre.  This system
(two letters plus 10 figures) is commonly
what is seen when using a GPS device set to the British National
Grid.  Also many datasets on the [Cave Registry Data Archive](http://cave-registry.org.uk/ "Cave Registry")
have entrance fixes specified as 10-fig NGRs, assuming the grid
letters are common to all entrances for the cave system of interest.

Alternatively, and more commonly in GIS, in the UK one can use an
all-numeric 12-figure NGR in which the leading figures signal the 100
km &times; 100 km square numerically.

For example the entrance to Dow Cave (Great Whernside, Yorkshire) is
at `NGR SD 98378 74300`, which in the all-numeric system is `398378
474300`.  In the letter-based system these co-ordinates are often
truncated to 8-fig or 6-fig NGRs, to reflect the accuracy of the GPS
device for instance (thus 8-fig NGRs are used in the new Northern
Caves).  If you've forgotten your school geography lesson, the
_correct_ way to truncate an NGR is to _drop_ the least significant
figures, and not to round to the nearest 10 or 100.  This is because
an 8-fig (or 6-fig) NGR actually specifies a 10m &times; 10m (or 100m
&times; 100m) _square_ and not an approximate position as such.  Thus
the 6-fig NGR for Dow Cave is `NGR SD 983 743`.

If in doubt one can use the 'Where am I?' tool in the [Magic
Map](http://www.natureonthemap.naturalengland.org.uk/MagicMap.aspx
"Magic Map").  application to check NGRs.  Note that unless explicitly
set to use the WGS84 datum, Magic Map reports latitude and longitude
in the OSGB36 datum, which as mentioned is offset from WGS84 by a
datum shift of up to 50-100m.  Beware copying and pasting these OSGB36
latitudes and longitudes into Google Earth, for example!

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
the known geodetic CRS schemes (ie
[_georeferenced_](https://en.wikipedia.org/wiki/Georeferencing "wikipedia")),
then any feature in the cave will have a known position in GIS terms,
and can thus be tied into any other georeferenced data such as maps,
satellite imagery, digital elevation models, etc.  Given that most
cave surveying is done in metres, it is obviously convenient to tie
into a CRS which uses metric co-ordinates, such as UTM or British
National Grid (OS NGR).  Note that once you've tied the dataset into a
recognised CRS, any GIS platform worth its salt will be able to
re-project into a different CRS, and will be able to display and
combine information from different sources irrespective of the CRS.

The easiest way to georeference cave survey data, with a modern
survex distribution, is to `*fix` cave entrances in an appropriate
CRS and make judicious use of the `*cs` commands.  One would typically
use a plain `*cs` command to specify the input CRS that the entrance
co-ordinates are given in, and a `*cs out`
command to specify what the output CRS should be.  In
the UK for instance one can use this to convert between the OS grid
letter system and the all-numeric scheme. 
For example the survex files for the Dow Cave -
Providence Pot system contain, in `DowCave.svx`
```
*begin DowCave
*export entrance
...
*entrance entrance
*fix entrance 98378 74300 334
*equate entrance dow1.1
...
```
and in the master file `DowProv.svx`
```
*cs OSGB:SD
*cs out EPSG:27700

*begin DowProv
*include DowCave
...
```
The first of these (in `DowCave.svx`) specifies the entrance location
as a 10-fig NGR which is assumed to be in the SD letter square.  The
easting and northing here (and altitude) are obtained by field work.
The second of these (in `DowProv.svx`) specifies input CRS is the OS
GB SD square (to match with the `*fix` in `DowCave.svx`), and asks that the output
co-ordinates should be in the all-numeric OS NGR scheme.  To avoid
potential misunderstanding when importing into a GIS platform, this
output CRS is specified using a European Petroleum Survey Group (EPSG)
number that points to the British National Grid.  For example in QGIS one can find
this CRS easily enough by searching on the EPSG number:
```
OSGB 1936 / British National Grid    EPSG:27700
```

If you check the processed survey in `aven`, or run `3dtopos` on the `.3d` file,
the processed entrance co-ordinates are now indeed
```
(398378.00, 474300.00,   334.00 ) dowprov.dowcave.dow1.1
```
Whilst this may seem like a crazily over-the-top
way to add a '3' and '4' to the entrance co-ordinates, it is actually very simple to implement:
one only needs to add two lines (the `*cs` and `*cs out` commands) to the survex file.
The benefit is that it is robust, clean, and unambiguous.  Moreover, the output CRS
is included as metadata in the `.3d` file; thus with `dump3d` one sees
```
CS +init=epsg:27700 +no_defs
```
(this is in fact a [PROJ.4](http://proj4.org/ "proj4") string which species the map projection, and can be directly
used by a GIS application).

I've gone into this example in some detail as the survex documentation on the `*cs` command
is rather spartan.

As an aside, providing the survex data files include correctly formatted `*date` commands,
the fact that the `*cs` commands make survex aware of the geodetic CRS means that
magnetic declination corrections can be automatically added.  This is another reason one
might want to 'do things properly' with `*cs` commands.
The `DowProv.svx` master file thus also contains the lines (the first is just a comment)
```
; mag dec calculated for SD 97480 72608 (Dowbergill Bridge, just above Kettlewell)
*declination auto 97480 72608 225
```
This correctly applies the magnetic declination (using a standard
magnetic field model), computed at the specified location in the input
CRS, to _all_ the included survey files, even though in this case the
range of dates spans 30 years.

## Quick-and-dirty two dimensional (flat) GIS import

_Work in progress !_

## Notes on georeferencing images, maps, and old surveys

_Also work in progress !_
