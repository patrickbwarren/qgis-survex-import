# qgis-survex-import
Planned QGIS import plugin for survex 3d files

## Outline

The idea is that a survex `.3d` file should be easily readable into a
Geographic Information System (GIS) platform, such as
[QGIS](http://www.qgis.org/ "QGIS website"), then it can be integrated
with other geographical data such as maps, satellite imagery, digital
elevation models, and the like.  Now this is much closer to being
achievable than one might think.  Here's the typical contents of a
modern `.3d` file such as can be exposed by running `dump3d`:

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
* attributes consisting of records of various kinds that are user-configurable, and associated with the geometries above;
* a co-ordinate reference system, and possible other metadata.

Now at this point you are supposed to slap yourself on the head and
ask why on earth we haven't been using ESRI shapefiles for storing
survex output data all along!  Note that both are binary formats, and shapefiles
are certainly flexible enough to contain all the information normally included
in a `.3d` file. 

## Co-ordinate Reference Systems

In order for this to work smoothly, we first have to be on top of our co-ordinate
reference system (CRS), or [spatial reference system (SRS)](https://en.wikipedia.org/wiki/Spatial_reference_system "wikipedia").  In GIS parlance, this is basically a co-ordinate-based
scheme for locating geographical features.  The following notes are
necessarily not quite the whole truth, but hopefully contain enough of
the truth to be useful.

A CRS usually comprises:

* a [geodetic datum](https://en.wikipedia.org/wiki/Geodetic_datum "wikipedia") or reference ellipsoid which specifies the overall
  shape of the earth's surface (eg [WGS84](https://en.wikipedia.org/wiki/World_Geodetic_System "wikipedia") used in GPS, or the Airy
  ellipsoid used by the Ordnance Survey (OS) in the UK)

* a map projection which is nearly always a [Transverse Mercator](https://en.wikipedia.org/wiki/Transverse_Mercator_projection "wikipedia") projection, such
  as the [Universal Transverse Mercator (UTM)](https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system "wikipedia") system used in GPS; this
  tries to optimally flatten the curved surface of the earth (note that there is always some minor compromise
  involved here);

* a co-ordinate system defined on top of the map projection,
  typically specifying a 'false origin' so that co-ordinates are always
  positive.

Given the geodetic datum one can always work with latitudes and
longitudes, but these aren't terribly convenient for cave survey data
crunching.  Also beware that the same point on the earth's surface may
have a different latitude and longitude depending on the reference
datum: this difference is known as a datum shift, and a well-known
example is the [datum shift between WGS84 and OSGB36](https://en.wikipedia.org/wiki/Ordnance_Survey_National_Grid "wikipedia") that nowadays only shows up in [Magic Map](http://www.natureonthemap.naturalengland.org.uk/MagicMap.aspx "Magic Map").  Modern usage
nearly always corresponds to the WGS84 datum, which is pretty much universally used on the web so far as I know, and used 
for instance in [Google Earth](https://en.wikipedia.org/wiki/Google_Earth "wikipedia") (in fact Google's [Keyole Markup Language (KML)](https://developers.google.com/kml/ "Google") only supports latitude and longitude, in WGS84).
Most GPS devices will report latitude and longitude in WGS84, though
more often than not you won't see this directly but rather get metric
UTM co-ordinates, or metric British National Grid co-ordinates (OS
12-fig NGR).

Back to cave surveying: for most surveys the earth's surface can be
regarded as essentially flat, so one is working in a 3d world with
eastings, northings, and altitudes, with the origin of the co-ordinate
system chosen at one's convenience.  Perhaps for synoptic maps of very
large karst areas, one might be worried about the curvature (grid
convergence), but for the most part it should be negligible relative
to the errors that typically creep into cave survey projects.

As long as this local cave co-ordinate system can be tied into one of
the known geodetic CRS schemes (ie [_georeferenced_](https://en.wikipedia.org/wiki/Georeferencing "wikipedia")), then any feature in the cave will have
a known position in GIS terms, and can thus be tied into any other
georeferenced data such as maps, satellite imagery, digital elevation
models, etc.  Given that most cave surveying is done in metres, it is
obviously convenient to tie into a CRS which uses metric co-ordinates,
such as UTM or British National Grid (OS NGR).  Note that once you've
tied the dataset into a recognised CRS, any GIS platform worth its
salt will be able to re-project into a different CRS, and will be able
to display and combine information from different sources irrespective
of the CRS.

The easiest way to do georeference cave survey data, with a modern
`survex` distribution, is to `*fix` cave entrances in an appropriate
CRS and make judicious use of the `*cs` commands. _To be continued_

## Quick-and-dirty two dimensional (flat) georeferencing

_Work in progress !_

## Notes on georeferencing images and maps

_Also work in progress !_
