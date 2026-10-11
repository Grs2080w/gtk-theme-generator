#!/usr/bin/env python3
"""Recalcula a lista de cores-fonte (cor, família, usos) e grava dentro de
pagina/estudio.html, na linha `const SOURCE = [...]`.

Rode sempre que mudar a classificação (função familia) no gerar-tema.py,
para a página continuar mostrando exatamente o que o gerador faz.
"""
import collections, importlib.util, json, os, re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('g', os.path.join(RAIZ, 'gerar-tema.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

usos = collections.Counter()


class Registrador(g.Gerador):
    def cor(self, rgb, contexto):
        usos[(g.rgb_hex(rgb), g.familia(rgb, contexto))] += 1
        return None


r = Registrador(dict(g.PADRAO))
for rel in ('gtk-3.0/gtk.css', 'gtk-4.0/gtk.css', 'gnome-shell/gnome-shell.css'):
    r.css(open(os.path.join(g.ORIGEM, rel)).read())
r.gtkrc(open(os.path.join(g.ORIGEM, 'gtk-2.0/gtkrc')).read())

dados = [[h, f, n] for (h, f), n in usos.most_common() if f != 'fixa']
pagina = os.path.join(RAIZ, 'pagina', 'estudio.html')
html = open(pagina).read()
novo, n = re.subn(r'const SOURCE = \[.*?\];', lambda _: 'const SOURCE = ' + json.dumps(dados) + ';', html, count=1, flags=re.S)
if not n:
    raise SystemExit('Não achei "const SOURCE = [...]" em pagina/estudio.html')
open(pagina, 'w').write(novo)
print(f'{len(dados)} cores gravadas em {pagina}:', dict(collections.Counter(f for _, f, _ in dados)))
