# own-theme

Read `docs/DEVELOPMENT.md` before changing anything: it documents the color classification, the
byte-for-byte regression test and the rule that the editor's JS must match the Python math.

- Never modify `/usr/share/themes/ZorinBlue-Dark` (the source theme).
- Test with a throwaway theme `name` (e.g. `OwnTest-Dark`) and delete it afterwards; never generate
  into `~/.themes/<name>` for a theme that is installed in `/usr/share/themes`.
- After changing `family()` in `generate-theme.py`, run `tools/export-colors.py`.
