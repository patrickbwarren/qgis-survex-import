# Extra python scripts

* `survex_import_v1.py` is the previous version of plugin.

* `survex_import_using_dump3d.py` is a version which slurps the output
  of the survex `dump3d` command, then parses it (requires `dump3d`
  from survex).

* `survex_import_with_tmpfile.py` is another version which uses a
  temporary file to cache the output of `dump3d`, before parsing.

* `dump3d.py` replicates _exactly_ the functionality of the survex
  `dump3d` command in pure python, for debugging.

* `import3d.py` is an old, stripped down version of the main plugin
  built for testing and troubleshooting when added as a user script to
  the Processing Toolbox.

* `test3d.py` was used for debugging the treatment of the passage wall
  data.  It runs like `dump3d.py`, but additionally generates a number of
  `*.dat` files containing xy data which can be read into a standard
  plotting package.
