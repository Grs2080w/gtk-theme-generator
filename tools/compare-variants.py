#!/usr/bin/env python3
"""Validate the math: generate themes from the official base colors of other
Zorin variants and compare them color by color with the official theme.

Expected: median 0 and a low p95 (< ~6). Isolated high values come from
misalignment (the official variants have 1–2 more/fewer colors).
"""
import math, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANTS = {'Green': ('#202b27', '#bbf1dd'), 'Purple': ('#28232d', '#d8c4f1'),
            'Red': ('#2e1f1f', '#fdb4b4'), 'Orange': ('#2e231f', '#fcc8b4')}
COLOR = re.compile(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![-\w])')


def rgb(h):
    h = h[1:]
    h = ''.join(c * 2 for c in h) if len(h) == 3 else h
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


for v, (background, accent) in VARIANTS.items():
    name = f'TestVariant{v}'
    with tempfile.NamedTemporaryFile('w', suffix='.conf', delete=False) as f:
        f.write(f'name = {name}\nbackground = {background}\naccent = {accent}\ntext = {accent}\n')
    subprocess.run([sys.executable, os.path.join(ROOT, 'generate-theme.py'), f.name], check=True, stdout=subprocess.DEVNULL)
    os.unlink(f.name)
    generated = os.path.expanduser(f'~/.themes/{name}')
    for rel in ('gtk-3.0/gtk.css', 'gtk-4.0/gtk.css', 'gnome-shell/gnome-shell.css'):
        a = COLOR.findall(open(f'{generated}/{rel}').read())
        b = COLOR.findall(open(f'/usr/share/themes/Zorin{v}-Dark/{rel}').read())
        d = sorted(math.dist(rgb(x), rgb(y)) for x, y in zip(a, b))
        note = '' if len(a) == len(b) else f'  (imperfect alignment: {len(a)} vs {len(b)})'
        print(f'{v:7} {rel:28} median={d[len(d)//2]:5.1f} p95={d[int(len(d)*.95)]:6.1f}{note}')
    shutil.rmtree(generated)
