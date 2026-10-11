#!/usr/bin/env python3
"""Gera um tema Zorin Dark personalizado a partir do palette.conf.

Parte sempre do ZorinBlue-Dark original do sistema (nunca altera ele) e
recalcula cada cor por "família":

  fundo     tons escuros (janela, conteúdo, bordas, sidebar, texto apagado)
  destaque  seleção, botões em destaque, foco, sliders, switches
  texto     a mesma família do destaque, mas usada em `color:` (texto)
  sobre     texto escuro que fica em cima do destaque (texto_sobre_destaque)
  erro / aviso / sucesso   cores de status
  fixa      pretos, brancos, sombras, paleta GNOME — nunca mudam

Cada família tem uma cor de referência no tema original. A cor nova é obtida
aplicando a mesma "distância" (tom, saturação, luminosidade) entre a
referência original e a cor que você escolheu.

Uso:
  python3 gerar-tema.py                 # usa palette.conf ao lado do script
  python3 gerar-tema.py outro.conf
  python3 gerar-tema.py --aplicar       # gera e já ativa o tema
  python3 gerar-tema.py --blur          # só configura o Blur my Shell (blur = sim)

Extras (opcionais; com os valores padrão o tema fica igual ao Zorin):
  vidro    opacidade_janela / opacidade_conteudo deixam os fundos translúcidos;
           com blur = sim, o --aplicar liga o blur de apps no Blur my Shell
  botões   botoes = circulos | simples troca o desenho de fechar/maximizar/
           minimizar; icone_<botão> = caminho.svg usa um ícone seu
"""
import colorsys
import os
import re
import shutil
import subprocess
import sys

ORIGEM = '/usr/share/themes/ZorinBlue-Dark'
# O gsettings do linuxbrew (primeiro no PATH) grava num arquivo (backend keyfile)
# que o GNOME nunca lê. O do sistema grava no dconf, que é o que vale.
GSETTINGS = '/usr/bin/gsettings' if os.path.exists('/usr/bin/gsettings') else 'gsettings'
AQUI = os.path.dirname(os.path.abspath(__file__))

# Cores de referência do ZorinBlue-Dark (o que cada opção substitui)
REF = {
    'fundo': '#222b30',
    'destaque': '#bde6fb',
    'texto': '#bde6fb',
    'sobre': '#161c1f',
    'erro': '#fb7c7c',
    'aviso': '#faa483',
    'sucesso': '#6ee1b6',
}
PADRAO = {
    'nome': 'ZorinCustom-Dark',
    'fundo': REF['fundo'],
    'destaque': REF['destaque'],
    'texto': REF['texto'],
    'texto_sobre_destaque': 'auto',
    'erro': REF['erro'],
    'aviso': REF['aviso'],
    'sucesso': REF['sucesso'],
    'raio': '1.0',
    # vidro: fundos translúcidos (o blur em si vem da extensão Blur my Shell)
    'opacidade_janela': '1.0',
    'opacidade_conteudo': '1.0',
    'blur': 'nao',
    'blur_forca': '30',
    # estatico: cantos redondos, borra só o papel de parede (GNOME 46 não arredonda o dinâmico)
    'blur_modo': 'estatico',
    # botões da janela (fechar / maximizar / minimizar)
    'botoes': 'zorin',
    'botao_fechar': 'auto',
    'botao_maximizar': 'auto',
    'botao_minimizar': 'auto',
    'botao_tamanho': '18',
    'simbolos': 'hover',
    'glifos': 'linhas',
    'icone_fechar': 'nenhum',
    'icone_maximizar': 'nenhum',
    'icone_minimizar': 'nenhum',
    'icone_restaurar': 'nenhum',
}
BOTOES = ('fechar', 'maximizar', 'minimizar', 'restaurar')
# classe CSS de cada botão e a cor "auto" (família de status do tema)
CLASSE = {'fechar': 'close', 'maximizar': 'maximize', 'minimizar': 'minimize'}
COR_AUTO = {'fechar': 'erro', 'maximizar': 'sucesso', 'minimizar': 'aviso'}

# Paleta nomeada do GNOME no gtk-4.0 (blue_1 … dark_5): nunca mexer
PALETA_GNOME = re.compile(
    r'@define-color (?:blue|green|yellow|orange|red|purple|brown|light|dark)_\d[^;]*;')
COR = re.compile(
    r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![-\w])'
    r'|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)')
PROPS_TEXTO = {'color', 'caret-color', '-gtk-secondary-caret-color'}
SVG_MARCA = {'toggle-on.svg', 'checkbox.svg', 'checkbox-focused.svg'}


# ---------- conversão de cores ----------

def hex_rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb):
    return '#%02x%02x%02x' % tuple(rgb)


def rgb_hsl(rgb):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in rgb))
    return h * 360, s, l


def hsl_rgb(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return tuple(max(0, min(255, round(x * 255))) for x in (r, g, b))


def mapear_l(l, l_ref, l_alvo):
    """Luminosidade por partes: 0→0, ref→alvo, 1→1 (preserva os extremos)."""
    if l <= l_ref:
        return l * l_alvo / l_ref if l_ref else l_alvo
    return l_alvo + (l - l_ref) * (1 - l_alvo) / (1 - l_ref) if l_ref < 1 else l_alvo


def transformar(rgb, ref_hex, alvo_hex):
    h, s, l = rgb_hsl(rgb)
    hr, sr, lr = rgb_hsl(hex_rgb(ref_hex))
    ha, sa, la = rgb_hsl(hex_rgb(alvo_hex))
    h2 = h + (ha - hr)
    s2 = min(1.0, s * sa / sr) if sr else sa
    return hsl_rgb(h2, s2, mapear_l(l, lr, la))


def luminancia(rgb):
    def canal(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ---------- classificação ----------

def familia(rgb, contexto):
    """Decide a família de uma cor ORIGINAL do ZorinBlue-Dark."""
    h, s, l = rgb_hsl(rgb)
    H, S, L = h, s * 100, l * 100
    if 188 <= H <= 208 and S >= 5:
        if S >= 30:
            return 'texto' if contexto == 'texto' else 'destaque'
        if contexto in ('texto', 'marca') and L <= 20:
            return 'sobre'
        return 'fundo'
    if L >= 55 and S >= 50:
        if H >= 350 or H <= 8:
            return 'erro'
        if 14 <= H <= 20:
            return 'aviso'
        if 154 <= H <= 160:
            return 'sucesso'
    return 'fixa'


class Gerador:
    def __init__(self, cfg):
        self.cfg = cfg
        self.alvo = {
            'fundo': cfg['fundo'], 'destaque': cfg['destaque'],
            'texto': cfg['texto'], 'erro': cfg['erro'],
            'aviso': cfg['aviso'], 'sucesso': cfg['sucesso'],
        }
        sobre = cfg['texto_sobre_destaque']
        if sobre == 'auto':
            # escuro do próprio fundo se o destaque for claro, branco se for escuro
            if luminancia(hex_rgb(cfg['destaque'])) > 0.3:
                sobre = rgb_hex(transformar(hex_rgb(REF['sobre']), REF['fundo'], cfg['fundo']))
            else:
                sobre = '#ffffff'
        self.alvo['sobre'] = sobre
        self.stats = {}

    def cor(self, rgb, contexto):
        fam = familia(rgb, contexto)
        self.stats[fam] = self.stats.get(fam, 0) + 1
        if fam == 'fixa':
            return None
        ref = REF[fam]
        alvo = self.alvo[fam]
        if fam == 'sobre' and alvo.lower() in ('#ffffff', '#fff'):
            return (255, 255, 255)
        return transformar(rgb, ref, alvo)

    def trocar(self, texto, contexto):
        def sub(m):
            t = m.group(0)
            if t.startswith('#'):
                novo = self.cor(hex_rgb(t), contexto)
                return rgb_hex(novo) if novo else t
            nums = re.findall(r'[\d.]+', t)
            novo = self.cor(tuple(int(x) for x in nums[:3]), contexto)
            if not novo:
                return t
            if len(nums) == 4:
                return 'rgba(%d, %d, %d, %s)' % (*novo, nums[3])
            return 'rgb(%d, %d, %d)' % novo
        return COR.sub(sub, texto)

    # --- CSS: percorre declaração por declaração para saber a propriedade ---
    def css(self, texto):
        comentarios = []

        def guardar(m):
            comentarios.append(m.group(0))
            return '\0%d\0' % (len(comentarios) - 1)
        texto = re.sub(r'/\*.*?\*/', guardar, texto, flags=re.S)

        saida, seletores = [], []
        for m in re.finditer(r'[^{};]*[{};]|[^{};]+$', texto):
            pedaco = m.group(0)
            fim = pedaco[-1] if pedaco[-1] in '{};' else ''
            corpo = pedaco[:-1] if fim else pedaco
            if fim == '{':
                seletores.append(corpo)
                saida.append(pedaco)
                continue
            saida.append(self.declaracao(corpo, seletores) + fim)
            if fim == '}' and seletores:
                seletores.pop()
        texto = ''.join(saida)
        texto = re.sub(r'\0(\d+)\0', lambda m: comentarios[int(m.group(1))], texto)
        return self.raio(texto)

    def declaracao(self, corpo, seletores):
        if PALETA_GNOME.fullmatch(corpo.strip() + ';'):
            return corpo
        dc = re.match(r'(\s*@define-color\s+)([\w-]+)(.*)', corpo, re.S)
        if dc:
            nome = dc.group(2)
            if 'accent' in nome and 'fg' in nome or 'selected_fg' in nome:
                ctx = 'marca'
            elif 'fg' in nome or 'text' in nome or 'title' in nome:
                ctx = 'texto'
            else:
                ctx = 'outro'
            return dc.group(1) + nome + self.trocar(dc.group(3), ctx)
        prop = re.match(r'\s*([-\w]+)\s*:', corpo)
        ctx = 'outro'
        if prop and prop.group(1) in PROPS_TEXTO:
            sel = seletores[-1] if seletores else ''
            ctx = 'outro' if 'link' in sel else 'texto'
        return self.trocar(corpo, ctx)

    def raio(self, texto):
        fator = float(self.cfg['raio'])
        if fator == 1.0:
            return texto

        def escala(m):
            def px(n):
                v = float(n.group(1))
                if v >= 99:  # pílulas / círculos continuam iguais
                    return n.group(0)
                return ('%g' % round(v * fator, 1)) + 'px'
            return m.group(1) + re.sub(r'([\d.]+)px', px, m.group(2))
        return re.sub(r'(border(?:-[a-z]+)*-radius\s*:)([^;}]*)', escala, texto)

    def gtkrc(self, texto):
        def par(m):
            ctx = 'texto' if m.group(1).endswith(('fg_color', 'text_color')) else 'outro'
            if m.group(1) == 'selected_fg_color':
                ctx = 'marca'
            return m.group(1) + ':' + self.trocar(m.group(2), ctx)
        return re.sub(r'(\w+_color):(#[0-9a-fA-F]{3,6})', par, texto)

    def svg(self, texto, nome):
        return self.trocar(texto, 'marca' if nome in SVG_MARCA else 'outro')


# ---------- extras: vidro e botões da janela ----------
# Os extras são regras acrescentadas no FIM dos CSS. Com os valores padrão
# nada é acrescentado e o tema continua byte a byte igual ao original.
# A página (pagina/estudio.html) reimplementa GLIFOS, svg_glifo, estados_botao
# e opacidade_sidebar: se mudar aqui, mude lá também.

# símbolos desenhados em 16×16 (traço de 1.5px, pontas redondas)
GLIFOS = {
    'linhas': {'fechar': 'M5 5l6 6M11 5l-6 6', 'maximizar': 'M5.5 5.5h5v5h-5z',
               'minimizar': 'M5 8h6', 'restaurar': 'M5 7.5h3.5V11H5zM7.5 7.5V5H11v3.5H8.5'},
    'setas': {'fechar': 'M5 5l6 6M11 5l-6 6', 'maximizar': 'M5 9.5l3-3 3 3',
              'minimizar': 'M5 6.5l3 3 3-3', 'restaurar': 'M5.5 4l2.5 2.5L10.5 4M5.5 12l2.5-2.5 2.5 2.5'},
    'mac': {'fechar': 'M5.5 5.5l5 5M10.5 5.5l-5 5', 'maximizar': 'M8 5v6M5 8h6',
            'minimizar': 'M5 8h6', 'restaurar': 'M5 8h6'},
}
ESTADOS = ('', ':hover', ':active', ':backdrop', ':backdrop:hover')


def svg_glifo(d, cor, opacidade):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
            f'<path d="{d}" fill="none" stroke="{cor}" stroke-opacity="{opacidade}" stroke-width="1.5" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>\n')


def opacidade_sidebar(a):
    """A sidebar fica por cima do fundo da janela: alfa menor para não somar demais."""
    return round(a ** 3, 3)


def estados_botao(estilo, botao, simbolos, cor, proprio):
    """Para cada estado: (cor do fundo ou None, imagem, efeito).

    imagem: 'escuro' (símbolo escuro), 'texto' (símbolo na cor do texto),
    'proprio' (ícone do usuário) ou None."""
    halo = 'alpha(currentColor,0.12)'
    if proprio:
        # ícone próprio = o botão inteiro (sem círculo), em qualquer estilo
        return {
            '': ('transparent', 'proprio', ''),
            ':hover': (halo, 'proprio', ''),
            ':active': (halo, 'proprio', 'escurecer'),
            ':backdrop': ('transparent', 'proprio', 'apagar'),
            ':backdrop:hover': (halo, 'proprio', ''),
        }
    if estilo == 'circulos':
        def img(mostrar):
            return 'escuro' if mostrar else None
        sempre, hover = simbolos == 'sempre', simbolos != 'nunca'
        return {
            '': (cor, img(sempre), ''),
            ':hover': (cor, img(hover), ''),
            ':active': (cor, img(hover), 'escurecer'),
            ':backdrop': ('alpha(currentColor,0.2)', None, ''),
            ':backdrop:hover': (cor, img(hover), ''),
        }
    # simples: só o símbolo; fechar fica colorido no hover
    quente = cor if botao == 'fechar' else halo
    img_q = 'escuro' if botao == 'fechar' else 'texto'
    return {
        '': ('transparent', 'texto', ''),
        ':hover': (quente, img_q, ''),
        ':active': (quente, img_q, 'escurecer'),
        ':backdrop': ('transparent', 'texto', 'apagar'),
        ':backdrop:hover': (quente, img_q, ''),
    }


class Extras:
    """Monta os arquivos e as regras CSS de vidro e botões."""

    def __init__(self, cfg, g):
        self.cfg, self.g = cfg, g
        self.a = float(cfg['opacidade_janela'])
        self.b = float(cfg['opacidade_conteudo'])
        self.estilo = cfg['botoes']
        self.proprios = {b: cfg['icone_' + b] for b in BOTOES if cfg['icone_' + b] != 'nenhum'}
        self.mexe_botoes = self.estilo != 'zorin' or bool(self.proprios)
        self.t = int(cfg['botao_tamanho']) if self.estilo != 'zorin' else 16

    def raio_janela(self):
        return '%g' % round(15 * float(self.cfg['raio']), 1)

    def fundo(self, hex_original):
        return rgb_hex(transformar(hex_rgb(hex_original), REF['fundo'], self.cfg['fundo']))

    def cor_botao(self, b):
        v = self.cfg['botao_' + b]
        return self.cfg[COR_AUTO[b]] if v == 'auto' else v

    def ativo(self):
        return self.a < 1 or self.b < 1 or self.mexe_botoes

    # --- arquivos de imagem (iguais em gtk-3.0/assets e gtk-4.0/assets) ---
    def arquivos(self):
        """{nome do arquivo em assets: bytes}"""
        if not self.mexe_botoes:
            return {}
        out = {}
        glifos = GLIFOS[self.cfg['glifos']]
        for b in BOTOES:
            if b in self.proprios:
                caminho = self.proprios[b]
                out[f'own-{b}-proprio{os.path.splitext(caminho)[1].lower()}'] = open(caminho, 'rb').read()
            if self.estilo != 'zorin':
                out[f'own-{b}-escuro.svg'] = svg_glifo(glifos[b], '#000000', '0.6').encode()
                out[f'own-{b}-texto.svg'] = svg_glifo(glifos[b], self.cfg['texto'], '1').encode()
        return out

    def url(self, b, img):
        if img == 'proprio':
            ext = os.path.splitext(self.proprios[b])[1].lower()
            return f'url("assets/own-{b}-proprio{ext}")'
        return f'url("assets/own-{b}-{img}.svg")'

    # --- regras dos botões ---
    def botoes(self, gtk):
        if not self.mexe_botoes:
            return ''
        t = self.t
        linhas = ['', '/* own-theme: botões da janela */']
        if self.estilo != 'zorin':
            if gtk == 4:
                linhas.append('windowcontrols > button > image { -gtk-icon-size: %dpx; padding: 0; '
                              '-gtk-icon-filter: opacity(0); border-radius: 100%%; box-shadow: none; animation: none; '
                              'background-repeat: no-repeat; background-position: center; '
                              'transition: background-color 150ms ease, opacity 150ms ease; }' % t)
            else:
                linhas.append('button.titlebutton.close, button.titlebutton.maximize, button.titlebutton.minimize '
                              '{ min-width: %dpx; min-height: %dpx; padding: 0; margin: 0 3px; border: none; '
                              'border-radius: 9999px; box-shadow: none; animation: none; -gtk-icon-shadow: none; '
                              'background-repeat: no-repeat; background-position: center; }' % (t, t))
        for b in ('fechar', 'maximizar', 'minimizar'):
            c = CLASSE[b]
            # o maximizar tem uma segunda variante: janela maximizada (restaurar)
            variantes = [(False, b)] + ([(True, 'restaurar')] if b == 'maximizar' else [])
            for maxi, nome in variantes:
                # ícone próprio desta variante; sem um de restaurar, usa o de maximizar
                proprio = nome if nome in self.proprios else (b if b in self.proprios else None)
                if self.estilo == 'zorin' and not proprio:
                    continue
                pre = ('window.maximized ' if gtk == 4 else '.maximized ') if maxi else ''
                if gtk == 4 and self.estilo == 'zorin':
                    linhas.append(f'{pre}windowcontrols > button.{c} > image {{ -gtk-icon-filter: opacity(0); }}')
                if gtk == 3:
                    linhas.append(f'{pre}button.titlebutton.{c} image {{ color: transparent; -gtk-icon-shadow: none; }}')
                est = estados_botao(self.estilo, b, self.cfg['simbolos'], self.cor_botao(b), bool(proprio))
                for estado, (cor, img, efeito) in est.items():
                    if gtk == 4:
                        sel = f'{pre}windowcontrols > button.{c}{estado} > image'
                    else:
                        sel = f'{pre}button.titlebutton.{c}{estado}'
                    props = []
                    if cor:
                        props.append(f'background-color: {cor};')
                    if img:
                        arquivo = proprio if img == 'proprio' else nome
                        props.append(f'background-image: {self.url(arquivo, img)}; background-size: {t}px {t}px; '
                                     'background-repeat: no-repeat; background-position: center;')
                    else:
                        props.append('background-image: none;')
                    if efeito == 'escurecer':
                        props.append('box-shadow: inset 0 0 0 100px rgba(0, 0, 0, 0.15);')
                    elif cor:
                        props.append('box-shadow: none;')
                    if self.estilo == 'simples' or proprio:
                        props.append('opacity: %s;' % ('0.55' if efeito == 'apagar' else '1'))
                    linhas.append(f'{sel} {{ {" ".join(props)} }}')
        return '\n'.join(linhas) + '\n'

    # --- regras do vidro ---
    def vidro(self, gtk):
        a, b = self.a, self.b
        if a >= 1 and b >= 1:
            return ''
        f = self.fundo
        linhas = ['', '/* own-theme: vidro (fundos translúcidos; o blur vem da extensão Blur my Shell) */']
        if gtk == 4:
            if a < 1:
                s = opacidade_sidebar(a)
                linhas += [
                    f'@define-color window_bg_color alpha({f("#222b30")},{a:g});',
                    f'@define-color window_backdrop_color alpha({f("#1e2428")},{a:g});',
                    f'@define-color dialog_bg_color {f("#222b30")};',
                    '@define-color headerbar_bg_color transparent;',
                    '@define-color headerbar_backdrop_color transparent;',
                    f'@define-color sidebar_bg_color alpha({f("#2d3940")},{s:g});',
                    f'@define-color sidebar_backdrop_color alpha({f("#242b30")},{s:g});',
                    f'@define-color secondary_sidebar_bg_color alpha({f("#273238")},{s:g});',
                    f'@define-color secondary_sidebar_backdrop_color alpha({f("#21282c")},{s:g});',
                ]
            if b < 1:
                linhas += [
                    f'@define-color view_bg_color alpha({f("#161c1f")},{b:g});',
                    f'@define-color view_backdrop_color alpha({f("#171c1f")},{b:g});',
                    f'@define-color card_bg_color alpha({f("#161c1f")},{b:g});',
                    f'@define-color card_backdrop_color alpha({f("#171c1f")},{b:g});',
                ]
        else:
            if a < 1:
                linhas += [
                    f'.background {{ background-color: alpha({f("#222b30")},{a:g}); }}',
                    f'.background:backdrop {{ background-color: alpha({f("#1e2428")},{a:g}); }}',
                    # com a barra de título transparente, os cantos de cima vêm do fundo
                    f'.background.csd {{ border-radius: {self.raio_janela()}px; }}',
                    '.background.csd.maximized, .background.csd.fullscreen, .background.csd.tiled, '
                    '.background.csd.tiled-top, .background.csd.tiled-right, .background.csd.tiled-bottom, '
                    '.background.csd.tiled-left, .background.csd.solid-csd { border-radius: 0; }',
                    '.titlebar:not(headerbar), headerbar, .titlebar:backdrop:not(headerbar), headerbar:backdrop, '
                    'toolbar, toolbar:backdrop, searchbar > revealer > box, searchbar > revealer > box:backdrop, '
                    '.inline-toolbar, .inline-toolbar:backdrop, .location-bar, .location-bar:backdrop '
                    '{ background-color: transparent; }',
                ]
            if b < 1:
                linhas += [
                    f'.view, iconview, list {{ background-color: alpha({f("#161c1f")},{b:g}); }}',
                    f'.view:backdrop, iconview:backdrop, list:backdrop {{ background-color: alpha({f("#171c1f")},{b:g}); }}',
                    '.view text, iconview text, textview text, .view text:backdrop, iconview text:backdrop, '
                    'textview text:backdrop { background-color: transparent; }',
                ]
        return '\n'.join(linhas) + '\n'

    def css(self, gtk):
        return self.vidro(gtk) + self.botoes(gtk)


# Monta um pipeline próprio no Blur my Shell (blur estático + cantos arredondados).
# Roda no Python do sistema, que tem o módulo gi (o do linuxbrew não tem).
SCRIPT_PIPELINE = r"""
import sys, gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib
pasta, sigma, raio = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
fonte = Gio.SettingsSchemaSource.new_from_directory(pasta, Gio.SettingsSchemaSource.get_default(), False)
s = Gio.Settings.new_full(fonte.lookup('org.gnome.shell.extensions.blur-my-shell', False), None, None)
atual = s.get_value('pipelines')
novo = {}
for i in range(atual.n_children()):
    par = atual.get_child_value(i)
    d = par.get_child_value(1)
    novo[par.get_child_value(0).get_string()] = {
        d.get_child_value(k).get_child_value(0).get_string(): d.get_child_value(k).get_child_value(1).get_variant()
        for k in range(d.n_children())}
V = GLib.Variant
efeitos = V('av', [  # mesmo formato dos pipelines da extensão: lista de variants
    V('a{sv}', {'type': V('s', 'native_static_gaussian_blur'), 'id': V('s', 'effect_own_theme_blur'),
                'params': V('a{sv}', {'radius': V('i', sigma), 'unscaled_radius': V('i', sigma),
                                      'brightness': V('d', 1.0)})}),
    V('a{sv}', {'type': V('s', 'corner'), 'id': V('s', 'effect_own_theme_corner'),
                'params': V('a{sv}', {'radius': V('d', raio)})}),
])
novo['pipeline_own_theme'] = {'name': V('s', 'own-theme (blur + cantos)'), 'effects': efeitos}
s.set_value('pipelines', V('a{sa{sv}}', novo))
Gio.Settings.sync()
"""


def configurar_blur(cfg):
    """Liga o blur de aplicativos do Blur my Shell (só se blur = sim)."""
    if cfg['blur'] != 'sim':
        return
    uuid = 'blur-my-shell@aunetx'
    pastas = [os.path.expanduser(f'~/.local/share/gnome-shell/extensions/{uuid}/schemas'),
              f'/usr/share/gnome-shell/extensions/{uuid}/schemas']
    pasta = next((p for p in pastas if os.path.exists(os.path.join(p, 'gschemas.compiled'))), None)
    if not pasta:
        print('Blur: a extensão Blur my Shell não está instalada. '
              'Instale em https://extensions.gnome.org/extension/3193/blur-my-shell/ e rode de novo.')
        return
    raio = round(15 * float(cfg['raio']))
    estatico = cfg['blur_modo'] == 'estatico'
    if estatico:
        r = subprocess.run(['/usr/bin/python3', '-c', SCRIPT_PIPELINE, pasta, cfg['blur_forca'], str(raio)])
        if r.returncode:
            print('Blur: não consegui criar o pipeline com cantos; usando o modo dinâmico.')
            estatico = False
    schema = 'org.gnome.shell.extensions.blur-my-shell.applications'
    valores = {
        'blur': 'true', 'enable-all': 'true', 'customize': 'true',
        'opacity': '255',            # a janela continua opaca; a transparência vem do tema
        'dynamic-opacity': 'false',
        'sigma': str(int(cfg['blur_forca'])),
        'brightness': '1.0',
        'corner-radius': str(raio),
        'static-blur': 'true' if estatico else 'false',
    }
    if estatico:
        valores['pipeline'] = "'pipeline_own_theme'"
    falhas = [k for k, v in valores.items()
              if subprocess.run([GSETTINGS, '--schemadir', pasta, 'set', schema, k, v]).returncode]
    if falhas:
        print('Blur: não consegui ajustar ' + ', '.join(falhas) + ' (versão diferente do Blur my Shell?)')
    elif estatico:
        print(f"Blur: Blur my Shell borrando o papel de parede atrás dos apps, cantos de {raio}px "
              f"(força {cfg['blur_forca']}).")
    else:
        print(f"Blur: Blur my Shell borrando tudo atrás dos apps (força {cfg['blur_forca']}); "
              'no GNOME 46 os cantos desse modo ficam retos.')


# ---------- execução ----------

def ler_conf(caminho):
    # formato "chave = valor  # comentário"; valores nunca têm espaço,
    # então pegamos só a primeira palavra (o '#' de cor não vira comentário)
    cfg = dict(PADRAO)
    if not os.path.exists(caminho):
        sys.exit(f'Erro: {caminho} não encontrado')
    with open(caminho) as f:
        for n, linha in enumerate(f, 1):
            linha = linha.strip()
            if not linha or linha.startswith(('#', ';', '[')):
                continue
            if '=' not in linha:
                sys.exit(f'Erro na linha {n} de {caminho}: esperado "chave = valor"')
            chave, valor = (x.strip() for x in linha.split('=', 1))
            if chave not in PADRAO:
                sys.exit(f'Erro na linha {n}: opção desconhecida "{chave}". '
                         f'Opções: {", ".join(PADRAO)}')
            cfg[chave] = valor.split()[0] if valor else ''
    for k in ('fundo', 'destaque', 'texto', 'erro', 'aviso', 'sucesso'):
        if not re.fullmatch(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}', cfg[k]):
            sys.exit(f'Erro: "{k} = {cfg[k]}" não é uma cor hex válida (ex: #222b30)')
    erro_opcao = validar_extras(cfg, os.path.dirname(os.path.abspath(caminho)))
    if erro_opcao:
        sys.exit('Erro: ' + erro_opcao)
    sobre = cfg['texto_sobre_destaque']
    if sobre != 'auto' and not re.fullmatch(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}', sobre):
        sys.exit('Erro: texto_sobre_destaque deve ser "auto" ou uma cor hex')
    if not re.fullmatch(r'[\w.+-]+', cfg['nome']):
        sys.exit('Erro: nome do tema só pode ter letras, números, "-", "_" e "."')
    return cfg


def validar_extras(cfg, base):
    """Confere as opções de vidro e botões; resolve os caminhos dos ícones."""
    hexa = re.compile(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}')
    for k in ('opacidade_janela', 'opacidade_conteudo'):
        try:
            v = float(cfg[k])
        except ValueError:
            v = -1
        if not 0.3 <= v <= 1:
            return f'"{k} = {cfg[k]}" deve ser um número de 0.3 a 1 (1 = opaco)'
        cfg[k] = '%g' % v
    escolhas = {'blur': ('sim', 'nao'), 'blur_modo': ('estatico', 'dinamico'), 'botoes': ('zorin', 'circulos', 'simples'),
                'simbolos': ('sempre', 'hover', 'nunca'), 'glifos': tuple(GLIFOS)}
    for k, ok in escolhas.items():
        if cfg[k] not in ok:
            return f'"{k} = {cfg[k]}" deve ser um destes: {", ".join(ok)}'
    if not cfg['blur_forca'].isdigit() or not 0 <= int(cfg['blur_forca']) <= 100:
        return 'blur_forca deve ser um número inteiro de 0 a 100'
    if not cfg['botao_tamanho'].isdigit() or not 16 <= int(cfg['botao_tamanho']) <= 26:
        return 'botao_tamanho deve ser um número inteiro de 16 a 26 (px)'
    for b in ('fechar', 'maximizar', 'minimizar'):
        v = cfg['botao_' + b]
        if v != 'auto' and not hexa.fullmatch(v):
            return f'"botao_{b} = {v}" deve ser "auto" ou uma cor hex'
    for b in BOTOES:
        k = 'icone_' + b
        v = cfg[k]
        if v in ('', 'nenhum'):
            cfg[k] = 'nenhum'
            continue
        caminho = os.path.join(base, os.path.expanduser(v))
        if not os.path.isfile(caminho):
            return f'"{k} = {v}": arquivo não encontrado (o caminho é relativo à pasta do palette.conf)'
        if os.path.splitext(caminho)[1].lower() not in ('.svg', '.png'):
            return f'"{k} = {v}": use um arquivo .svg ou .png'
        cfg[k] = caminho
    return None


def gerar(cfg):
    destino = os.path.expanduser(f"~/.themes/{cfg['nome']}")
    if os.path.realpath(destino) == os.path.realpath(ORIGEM):
        sys.exit('Erro: o destino não pode ser o tema original')
    if os.path.exists(destino):
        if not os.path.exists(os.path.join(destino, '.gerado-por-zorin-tema')):
            sys.exit(f'Erro: {destino} já existe e não foi criado por este script. '
                     'Escolha outro "nome" no palette.conf.')
        shutil.rmtree(destino)
    shutil.copytree(ORIGEM, destino, ignore=shutil.ignore_patterns('xfwm4'))
    open(os.path.join(destino, '.gerado-por-zorin-tema'), 'w').close()

    g = Gerador(cfg)
    for raiz, _, arquivos in os.walk(destino):
        for nome in arquivos:
            p = os.path.join(raiz, nome)
            rel = os.path.relpath(p, destino)
            if nome.endswith('.css'):
                novo = g.css(open(p).read())
            elif rel == 'gtk-2.0/gtkrc':
                novo = g.gtkrc(open(p).read())
            elif nome.endswith('.svg') and not nome.endswith('-light.svg'):
                novo = g.svg(open(p).read(), nome)
            elif nome == 'index.theme':
                novo = re.sub(r'ZorinBlue-Dark', cfg['nome'], open(p).read())
                novo = re.sub(r'(?m)^IconTheme=.*$', 'IconTheme=ZorinBlue-Dark', novo)
                novo = re.sub(r'(?m)^Comment=.*$', 'Comment=Tema gerado por gerar-tema.py', novo)
            else:
                continue
            with open(p, 'w') as f:
                f.write(novo)

    extras = Extras(cfg, g)
    if extras.ativo():
        for gtk in (3, 4):
            pasta = os.path.join(destino, f'gtk-{gtk}.0')
            for nome, dados in extras.arquivos().items():
                with open(os.path.join(pasta, 'assets', nome), 'wb') as f:
                    f.write(dados)
            regras = extras.css(gtk)
            for nome in ('gtk.css', 'gtk-dark.css'):
                with open(os.path.join(pasta, nome), 'a') as f:
                    f.write(regras)
    return destino, g


def aplicar(nome):
    cmds = [
        [GSETTINGS, 'set', 'org.gnome.desktop.interface', 'color-scheme', 'prefer-dark'],
        [GSETTINGS, 'set', 'org.gnome.desktop.interface', 'gtk-theme', nome],
        [GSETTINGS, 'set', 'org.gnome.shell.extensions.user-theme', 'name', nome],
    ]
    for c in cmds:
        subprocess.run(c, check=False)
    configurar_blur(cfg)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    conf = args[0] if args else os.path.join(AQUI, 'palette.conf')
    cfg = ler_conf(conf)
    if '--blur' in sys.argv:  # só configura o Blur my Shell (usado pelo instalar.sh)
        configurar_blur(cfg)
        return
    destino, g = gerar(cfg)
    print(f'Tema gerado em {destino}')
    print('Cores trocadas por família:', ', '.join(f'{k}={v}' for k, v in sorted(g.stats.items())))
    print(f"Texto sobre destaque: {g.alvo['sobre']}")
    if '--aplicar' in sys.argv:
        aplicar(cfg['nome'])
        print('Tema aplicado. Feche e reabra os apps para ver a mudança.')
    else:
        print(f'Para ativar: python3 {os.path.abspath(__file__)} --aplicar')


if __name__ == '__main__':
    main()
