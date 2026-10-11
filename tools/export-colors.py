#!/usr/bin/env python3
"""Recompute the list of source colors (color, family, uses) and write it into
editor/index.html, on the `const SOURCE = [...]` line.

Run it whenever you change the classification (the family function) in
generate-theme.py, so the editor keeps showing exactly what the generator does.
"""
import collections, importlib.util, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('g', os.path.join(ROOT, 'generate-theme.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

uses = collections.Counter()


class Recorder(g.Generator):
    def color(self, rgb, context):
        uses[(g.rgb_hex(rgb), g.family(rgb, context))] += 1
        return None


r = Recorder(dict(g.DEFAULTS))
for rel in ('gtk-3.0/gtk.css', 'gtk-4.0/gtk.css', 'gnome-shell/gnome-shell.css'):
    r.css(open(os.path.join(g.SOURCE, rel)).read())
r.gtkrc(open(os.path.join(g.SOURCE, 'gtk-2.0/gtkrc')).read())

data = [[h, f, n] for (h, f), n in uses.most_common() if f != 'fixed']
page = os.path.join(ROOT, 'editor', 'index.html')
html = open(page).read()
new, n = re.subn(r'const SOURCE = \[.*?\];', lambda _: 'const SOURCE = ' + json.dumps(data) + ';', html, count=1, flags=re.S)
if not n:
    raise SystemExit('Could not find "const SOURCE = [...]" in editor/index.html')
open(page, 'w').write(new)
print(f'{len(data)} colors written to {page}:', dict(collections.Counter(f for _, f, _ in data)))
