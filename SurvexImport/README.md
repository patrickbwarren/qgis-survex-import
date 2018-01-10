# QGIS plugin to import survex .3d files

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

For more details see the main `README.md` in the top level directory.
