# Extra python scripts related to .3d file import

* `import3d.py` is a stripped down version of the main plugin which could
be useful for testing and troubleshooting.  It can be added as a user
script to the Processing Toolbox.  It does however need customising
for specific imports.

* `survex_import_with_tmpfile.py` is a version of the main plugin
script which uses a temporary file to cache the output of `dump3d` and
may be useful if memory limitations are encountered.  If installed it
should be renamed `survex_import.py`.

For more details see the main `README.md` in the top level directory.
