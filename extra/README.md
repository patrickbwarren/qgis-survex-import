# Extra python scripts related to .3d file import

* `import3d.py` is a stripped down version of the main plugin which could
be useful for testing and troubleshooting.  It can be added as a user
script to the Processing Toolbox.  It does however need customising
for specific imports.

* `dump3d.py` replicates the functionality of the survex `dump3d`
command in pure python (try `diff` on the outputs).

* `survex_import_using_dump3d.py` is the original version of the main
plugin script which slurps then parses the output of the survex
`dump3d` command.

* `survex_import_with_tmpfile.py` is another version which uses a
temporary file to cache the output of `dump3d`, before parsing.

For more details see the main `README.md` in the top level directory.
