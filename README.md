# QGIS survex .3d file import plugin

This QGIS plugin provides a convenient route to import features (legs and
stations) from a [survex](https://survex.com/ "survex.com")
`.3d` file, with z-dimension (elevation) and other
metadata properly included.

To install the plugin:

* clone or download this repository and copy the `SurvexImport`
directory into the QGIS python plugins directory, which is usually
`~/.qgis2/python/plugins` (where `~` on Windows is probably
`C:\Users\<user>`);

* run QGIS and enable the plugin by going to 'Plugins --> Manage and
  Install Plugins...' and make sure the box next to 'Import .3d file'
  is checked.

When installed, a menu item 'Import .3d file' should appear on the
'Vector' drop-down menu in the main QGIS window.  Clicking on this, a
pop-up window appears for the user to select a `.3d` file, and choose
whether to import legs or stations , or both.  For the former (legs)
additional options allow the user to choose whether to include splay,
duplicate, and surface legs.  For the latter (stations) the user can
choose whether to include surface stations.  Finally there is an option
to import the CRS from the `.3d` file if possible.

On clicking OK, vector layers are created to contain the legs and
stations as desired.  The CRS is requested for each layer if not
picked up from the file.  Some attributes are also imported (most
usefully perhaps, names for stations).

There is one point to bear in mind.  Because of the (current)
limitations in QGIS for creating vector layers in memory, the layer type does
not explicitly know that the features include z-dimension
(elevation) data.  To work around this one can save the layer
to a shapefile, for example to an ESRI Shapefile or a GeoPackage file.
In QGIS this usually results in the saved shapefile automatically
being loaded as a new vector layer, but of course one can also explicitly
load the new shapefile.  To ensure the z-dimension data is correctly
incorporated when saving to a shapefile, in the 'Save as ...'  dialog
make sure that the geometry type is specified (for legs this should be
'LineString', and for stations it should be 'Point') and the 'Include
z-dimension' box is checked.

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
expected if the survey data has been georeferenced using the survex
`*cs` and `*cs out` commands.  If it doesn't, one can always uncheck
this option and set the CRS by hand.  To maximise the likelihood that
CRS import works as expected, use an EPSG code in the `*cs out` survex
command rather than a PROJ.4 string.

Further notes on cave surveying and GIS are in 
[`cave_surveying_and_GIS.pdf`](cave_surveying_and_GIS.pdf).

Sample georeferenced survey data can be found in
[`DowProv.3d`](DowProv/DowProv.3d).

#### Platform-specific location of dump3d

The plugin uses `dump3d` to read the contents of the `.3d` file, and
obviously will fail if it can't find `dump3d`, or there is a survex
version mismatch (most likely, by trying to import a `.3d` file 'from
the future' with an older survex installation).

If you have a non-standard survex installation you can edit
`survex_python.py` to add an entry for the platform-specific location
of the `dump3d` executable.  The place to look is where a
dictionary of platform-specific executables is defined:
```
dump3d_dict = {'Linux' : '/usr/bin/dump3d',
               'Windows' : 'C:\Program Files (x86)\Survex\dump3d'}
```

The keys here are the return values of a call to `platform.system()`.
At the moment this dictionary lacks an entry for MAC OS X (e.g.
`'Darwin' : '...'`) but this will be fixed at some point (or you can
fix it yourself by running `which dump3d` in a Terminal).

### Copying

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

Copyright &copy; (2017, 2018) Patrick B Warren.


