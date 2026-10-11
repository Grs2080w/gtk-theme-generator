#!/usr/bin/env python3
"""Valida a matemática: gera temas com as cores-base oficiais de outras
variantes do Zorin e compara cor a cor com o tema oficial.

Esperado: mediana 0 e p95 baixo (< ~6). Valores altos isolados vêm de
desalinhamento (as variantes oficiais têm 1–2 cores a mais/menos).
"""
import math, os, re, shutil, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANTES = {'Green': ('#202b27', '#bbf1dd'), 'Purple': ('#28232d', '#d8c4f1'),
             'Red': ('#2e1f1f', '#fdb4b4'), 'Orange': ('#2e231f', '#fcc8b4')}
COR = re.compile(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![-\w])')


def rgb(h):
    h = h[1:]
    h = ''.join(c * 2 for c in h) if len(h) == 3 else h
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


for v, (fundo, destaque) in VARIANTES.items():
    nome = f'TesteVariante{v}'
    with tempfile.NamedTemporaryFile('w', suffix='.conf', delete=False) as f:
        f.write(f'nome = {nome}\nfundo = {fundo}\ndestaque = {destaque}\ntexto = {destaque}\n')
    subprocess.run([sys.executable, os.path.join(RAIZ, 'gerar-tema.py'), f.name], check=True, stdout=subprocess.DEVNULL)
    os.unlink(f.name)
    gerado = os.path.expanduser(f'~/.themes/{nome}')
    for rel in ('gtk-3.0/gtk.css', 'gtk-4.0/gtk.css', 'gnome-shell/gnome-shell.css'):
        a = COR.findall(open(f'{gerado}/{rel}').read())
        b = COR.findall(open(f'/usr/share/themes/Zorin{v}-Dark/{rel}').read())
        d = sorted(math.dist(rgb(x), rgb(y)) for x, y in zip(a, b))
        aviso = '' if len(a) == len(b) else f'  (alinhamento imperfeito: {len(a)} vs {len(b)})'
        print(f'{v:7} {rel:28} mediana={d[len(d)//2]:5.1f} p95={d[int(len(d)*.95)]:6.1f}{aviso}')
    shutil.rmtree(gerado)
