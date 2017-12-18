# qgis-survex-import
Planned QGIS import plugin for survex 3d files

## Outline

The idea is that a survex `.3d` file should be easily readable into a
Geographic Information System (GIS) platform, such as
[QGIS](http://www.qgis.org/ "QGIS website"), then it can be integrated
with other geographical data such as maps, satellite imagery, digital
elevation maps, and the like.  Now this is much closer to being
achievable than one might think.  Here's the typical contents of a
modern `.3d` file such as can be exposed by running `dump3d`:

* survey metadata: title, date, and coordinate reference system;
* traverses (strings of survey legs) with metadata: names,
  flags (normal, duplicate, splay, surface);
* stations (points) with metadata: names, flags (exported, entrance,
  fixed, surface) and passage cross-sections (LRUD data).

Now compare this to a typical
[ESRI shapefile](https://en.wikipedia.org/wiki/Shapefile "wikipedia")
which is well known for containing GIS vector data:

* geometry data: points, polylines (line strings), polygons, with or
  without elevation (z) data;
* attributes consisting of records of various kinds;
* a coordinate reference system.

Now at this point you are supposed to slap yourself on the head and
ask why on earth we haven't been using ESRI shapefiles for storing
survex output data!  Note that both are binary formats, and shapefiles
are flexible enough to contain all the information normally included
in a `.3d` file.  You might well ask...!

## Co-ordinate systems



## 2d 

_Work in progress !_
