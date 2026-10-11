#!/usr/bin/env python3
"""Generate a custom Zorin OS dark theme from palette.conf.

It always starts from the system's original ZorinBlue-Dark (never modified)
and recalculates every color by "family":

  background  dark tones (window, content, borders, sidebar, dimmed text)
  accent      selection, suggested buttons, focus, sliders, switches
  text        same family as the accent, but used in `color:` (text)
  on_accent   dark text drawn on top of the accent (text_on_accent)
  error / warning / success   status colors
  fixed       blacks, whites, shadows, GNOME palette — never change

Each family has a reference color in the original theme. A new color is
obtained by applying the same "distance" (hue, saturation, lightness)
between the original reference and the color you picked.

Usage:
  python3 generate-theme.py                 # uses palette.conf next to the script
  python3 generate-theme.py other.conf
  python3 generate-theme.py --apply         # generate and activate the theme
  python3 generate-theme.py --blur          # only configure Blur my Shell (blur = yes)

Extras (optional; with the default values the theme is identical to Zorin's):
  glass    window_opacity / content_opacity make backgrounds translucent;
           with blur = yes, --apply turns on app blur in Blur my Shell
  buttons  buttons = circles | plain redraws close/maximize/minimize;
           icon_<button> = path.svg uses your own icon
"""
import colorsys
import os
import re
import shutil
import subprocess
import sys

SOURCE = os.environ.get('OWN_THEME_SOURCE', '/usr/share/themes/ZorinBlue-Dark')
# Every theme this project creates carries this marker; nothing without it is
# ever overwritten. The legacy name is still accepted for older installs.
MARKER = '.generated-by-own-theme'
LEGACY_MARKERS = ('.gerado-por-zorin-tema',)
# Some setups (e.g. linuxbrew) put a gsettings first in PATH that writes to a
# keyfile GNOME never reads. The system one writes to dconf, which is what counts.
GSETTINGS = '/usr/bin/gsettings' if os.path.exists('/usr/bin/gsettings') else 'gsettings'
HERE = os.path.dirname(os.path.abspath(__file__))

# Reference colors of ZorinBlue-Dark (what each option replaces)
REF = {
    'background': '#222b30',
    'accent': '#bde6fb',
    'text': '#bde6fb',
    'on_accent': '#161c1f',
    'error': '#fb7c7c',
    'warning': '#faa483',
    'success': '#6ee1b6',
}
DEFAULTS = {
    'name': 'ZorinCustom-Dark',
    'background': REF['background'],
    'accent': REF['accent'],
    'text': REF['text'],
    'text_on_accent': 'auto',
    'error': REF['error'],
    'warning': REF['warning'],
    'success': REF['success'],
    'radius': '1.0',
    # glass: translucent backgrounds (the blur itself comes from the Blur my Shell extension)
    'window_opacity': '1.0',
    'content_opacity': '1.0',
    'blur': 'no',
    'blur_strength': '30',
    # static: rounded corners, blurs only the wallpaper (GNOME 46 can't round the dynamic one)
    'blur_mode': 'static',
    # window buttons (close / maximize / minimize)
    'buttons': 'zorin',
    'button_close': 'auto',
    'button_maximize': 'auto',
    'button_minimize': 'auto',
    'button_size': '18',
    'symbols': 'hover',
    'glyphs': 'lines',
    'icon_close': 'none',
    'icon_maximize': 'none',
    'icon_minimize': 'none',
    'icon_restore': 'none',
}
COLOR_KEYS = ('background', 'accent', 'text', 'error', 'warning', 'success')
BUTTONS = ('close', 'maximize', 'minimize', 'restore')
# "auto" color of each button (a status family of the theme)
AUTO_COLOR = {'close': 'error', 'maximize': 'success', 'minimize': 'warning'}

# GNOME named palette in gtk-4.0 (blue_1 … dark_5): never touch
GNOME_PALETTE = re.compile(
    r'@define-color (?:blue|green|yellow|orange|red|purple|brown|light|dark)_\d[^;]*;')
COLOR = re.compile(
    r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![-\w])'
    r'|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)')
HEX = re.compile(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}')
TEXT_PROPS = {'color', 'caret-color', '-gtk-secondary-caret-color'}
MARK_SVGS = {'toggle-on.svg', 'checkbox.svg', 'checkbox-focused.svg'}


# ---------- color conversion ----------

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


def map_l(l, l_ref, l_target):
    """Piecewise lightness: 0→0, ref→target, 1→1 (keeps the extremes)."""
    if l <= l_ref:
        return l * l_target / l_ref if l_ref else l_target
    return l_target + (l - l_ref) * (1 - l_target) / (1 - l_ref) if l_ref < 1 else l_target


def transform(rgb, ref_hex, target_hex):
    h, s, l = rgb_hsl(rgb)
    hr, sr, lr = rgb_hsl(hex_rgb(ref_hex))
    ht, st, lt = rgb_hsl(hex_rgb(target_hex))
    h2 = h + (ht - hr)
    s2 = min(1.0, s * st / sr) if sr else st
    return hsl_rgb(h2, s2, map_l(l, lr, lt))


def luminance(rgb):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ---------- classification ----------

def family(rgb, context):
    """Decide the family of an ORIGINAL ZorinBlue-Dark color."""
    h, s, l = rgb_hsl(rgb)
    H, S, L = h, s * 100, l * 100
    if 188 <= H <= 208 and S >= 5:
        if S >= 30:
            return 'text' if context == 'text' else 'accent'
        if context in ('text', 'mark') and L <= 20:
            return 'on_accent'
        return 'background'
    if L >= 55 and S >= 50:
        if H >= 350 or H <= 8:
            return 'error'
        if 14 <= H <= 20:
            return 'warning'
        if 154 <= H <= 160:
            return 'success'
    return 'fixed'


class Generator:
    def __init__(self, cfg):
        self.cfg = cfg
        self.target = {k: cfg[k] for k in COLOR_KEYS}
        on_accent = cfg['text_on_accent']
        if on_accent == 'auto':
            # the theme's own dark tone if the accent is light, white if it is dark
            if luminance(hex_rgb(cfg['accent'])) > 0.3:
                on_accent = rgb_hex(transform(hex_rgb(REF['on_accent']), REF['background'], cfg['background']))
            else:
                on_accent = '#ffffff'
        self.target['on_accent'] = on_accent
        self.stats = {}

    def color(self, rgb, context):
        fam = family(rgb, context)
        self.stats[fam] = self.stats.get(fam, 0) + 1
        if fam == 'fixed':
            return None
        target = self.target[fam]
        if fam == 'on_accent' and target.lower() in ('#ffffff', '#fff'):
            return (255, 255, 255)
        return transform(rgb, REF[fam], target)

    def replace(self, text, context):
        def sub(m):
            t = m.group(0)
            if t.startswith('#'):
                new = self.color(hex_rgb(t), context)
                return rgb_hex(new) if new else t
            nums = re.findall(r'[\d.]+', t)
            new = self.color(tuple(int(x) for x in nums[:3]), context)
            if not new:
                return t
            if len(nums) == 4:
                return 'rgba(%d, %d, %d, %s)' % (*new, nums[3])
            return 'rgb(%d, %d, %d)' % new
        return COLOR.sub(sub, text)

    # --- CSS: walk declaration by declaration to know the property ---
    def css(self, text):
        comments = []

        def keep(m):
            comments.append(m.group(0))
            return '\0%d\0' % (len(comments) - 1)
        text = re.sub(r'/\*.*?\*/', keep, text, flags=re.S)

        out, selectors = [], []
        for m in re.finditer(r'[^{};]*[{};]|[^{};]+$', text):
            chunk = m.group(0)
            end = chunk[-1] if chunk[-1] in '{};' else ''
            body = chunk[:-1] if end else chunk
            if end == '{':
                selectors.append(body)
                out.append(chunk)
                continue
            out.append(self.declaration(body, selectors) + end)
            if end == '}' and selectors:
                selectors.pop()
        text = ''.join(out)
        text = re.sub(r'\0(\d+)\0', lambda m: comments[int(m.group(1))], text)
        return self.radius(text)

    def declaration(self, body, selectors):
        if GNOME_PALETTE.fullmatch(body.strip() + ';'):
            return body
        dc = re.match(r'(\s*@define-color\s+)([\w-]+)(.*)', body, re.S)
        if dc:
            name = dc.group(2)
            if 'accent' in name and 'fg' in name or 'selected_fg' in name:
                ctx = 'mark'
            elif 'fg' in name or 'text' in name or 'title' in name:
                ctx = 'text'
            else:
                ctx = 'other'
            return dc.group(1) + name + self.replace(dc.group(3), ctx)
        prop = re.match(r'\s*([-\w]+)\s*:', body)
        ctx = 'other'
        if prop and prop.group(1) in TEXT_PROPS:
            sel = selectors[-1] if selectors else ''
            ctx = 'other' if 'link' in sel else 'text'
        return self.replace(body, ctx)

    def radius(self, text):
        factor = float(self.cfg['radius'])
        if factor == 1.0:
            return text

        def scale(m):
            def px(n):
                v = float(n.group(1))
                if v >= 99:  # pills / circles stay the same
                    return n.group(0)
                return ('%g' % round(v * factor, 1)) + 'px'
            return m.group(1) + re.sub(r'([\d.]+)px', px, m.group(2))
        return re.sub(r'(border(?:-[a-z]+)*-radius\s*:)([^;}]*)', scale, text)

    def gtkrc(self, text):
        def pair(m):
            ctx = 'text' if m.group(1).endswith(('fg_color', 'text_color')) else 'other'
            if m.group(1) == 'selected_fg_color':
                ctx = 'mark'
            return m.group(1) + ':' + self.replace(m.group(2), ctx)
        return re.sub(r'(\w+_color):(#[0-9a-fA-F]{3,6})', pair, text)

    def svg(self, text, name):
        return self.replace(text, 'mark' if name in MARK_SVGS else 'other')


# ---------- extras: glass and window buttons ----------
# The extras are rules appended at the END of the CSS files. With the default
# values nothing is appended and the theme stays byte-for-byte identical.
# The editor (editor/index.html) reimplements GLYPHS, glyph_svg, button_states
# and sidebar_opacity: if you change them here, change them there too.

# symbols drawn in 16×16 (1.5px stroke, round caps)
GLYPHS = {
    'lines': {'close': 'M5 5l6 6M11 5l-6 6', 'maximize': 'M5.5 5.5h5v5h-5z',
              'minimize': 'M5 8h6', 'restore': 'M5 7.5h3.5V11H5zM7.5 7.5V5H11v3.5H8.5'},
    'arrows': {'close': 'M5 5l6 6M11 5l-6 6', 'maximize': 'M5 9.5l3-3 3 3',
               'minimize': 'M5 6.5l3 3 3-3', 'restore': 'M5.5 4l2.5 2.5L10.5 4M5.5 12l2.5-2.5 2.5 2.5'},
    'mac': {'close': 'M5.5 5.5l5 5M10.5 5.5l-5 5', 'maximize': 'M8 5v6M5 8h6',
            'minimize': 'M5 8h6', 'restore': 'M5 8h6'},
}


def glyph_svg(d, color, opacity):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="{opacity}" stroke-width="1.5" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>\n')


def sidebar_opacity(a):
    """The sidebar sits on top of the window background: lower alpha so they don't add up."""
    return round(a ** 3, 3)


def button_states(style, button, symbols, color, custom):
    """For each state: (background color or None, image, effect).

    image: 'dark' (dark symbol), 'text' (symbol in the text color),
    'custom' (the user's icon) or None."""
    halo = 'alpha(currentColor,0.12)'
    if custom:
        # a custom icon is the whole button (no circle), in any style
        return {
            '': ('transparent', 'custom', ''),
            ':hover': (halo, 'custom', ''),
            ':active': (halo, 'custom', 'darken'),
            ':backdrop': ('transparent', 'custom', 'dim'),
            ':backdrop:hover': (halo, 'custom', ''),
        }
    if style == 'circles':
        def img(show):
            return 'dark' if show else None
        always, hover = symbols == 'always', symbols != 'never'
        return {
            '': (color, img(always), ''),
            ':hover': (color, img(hover), ''),
            ':active': (color, img(hover), 'darken'),
            ':backdrop': ('alpha(currentColor,0.2)', None, ''),
            ':backdrop:hover': (color, img(hover), ''),
        }
    # plain: just the symbol; close gets colored on hover
    hot = color if button == 'close' else halo
    hot_img = 'dark' if button == 'close' else 'text'
    return {
        '': ('transparent', 'text', ''),
        ':hover': (hot, hot_img, ''),
        ':active': (hot, hot_img, 'darken'),
        ':backdrop': ('transparent', 'text', 'dim'),
        ':backdrop:hover': (hot, hot_img, ''),
    }


class Extras:
    """Builds the files and CSS rules for glass and window buttons."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.a = float(cfg['window_opacity'])
        self.b = float(cfg['content_opacity'])
        self.style = cfg['buttons']
        self.custom = {b: cfg['icon_' + b] for b in BUTTONS if cfg['icon_' + b] != 'none'}
        self.touches_buttons = self.style != 'zorin' or bool(self.custom)
        self.size = int(cfg['button_size']) if self.style != 'zorin' else 16

    def window_radius(self):
        return '%g' % round(15 * float(self.cfg['radius']), 1)

    def bg(self, original_hex):
        return rgb_hex(transform(hex_rgb(original_hex), REF['background'], self.cfg['background']))

    def button_color(self, b):
        v = self.cfg['button_' + b]
        return self.cfg[AUTO_COLOR[b]] if v == 'auto' else v

    def active(self):
        return self.a < 1 or self.b < 1 or self.touches_buttons

    # --- image files (the same in gtk-3.0/assets and gtk-4.0/assets) ---
    def files(self):
        """{file name in assets: bytes}"""
        if not self.touches_buttons:
            return {}
        out = {}
        glyphs = GLYPHS[self.cfg['glyphs']]
        for b in BUTTONS:
            if b in self.custom:
                path = self.custom[b]
                with open(path, 'rb') as f:
                    out[f'own-{b}-custom{os.path.splitext(path)[1].lower()}'] = f.read()
            if self.style != 'zorin':
                out[f'own-{b}-dark.svg'] = glyph_svg(glyphs[b], '#000000', '0.6').encode()
                out[f'own-{b}-text.svg'] = glyph_svg(glyphs[b], self.cfg['text'], '1').encode()
        return out

    def url(self, b, img):
        if img == 'custom':
            ext = os.path.splitext(self.custom[b])[1].lower()
            return f'url("assets/own-{b}-custom{ext}")'
        return f'url("assets/own-{b}-{img}.svg")'

    # --- button rules ---
    def buttons(self, gtk):
        if not self.touches_buttons:
            return ''
        t = self.size
        lines = ['', '/* own-theme: window buttons */']
        if self.style != 'zorin':
            if gtk == 4:
                lines.append('windowcontrols > button > image { -gtk-icon-size: %dpx; padding: 0; '
                             '-gtk-icon-filter: opacity(0); border-radius: 100%%; box-shadow: none; animation: none; '
                             'background-repeat: no-repeat; background-position: center; '
                             'transition: background-color 150ms ease, opacity 150ms ease; }' % t)
            else:
                lines.append('button.titlebutton.close, button.titlebutton.maximize, button.titlebutton.minimize '
                             '{ min-width: %dpx; min-height: %dpx; padding: 0; margin: 0 3px; border: none; '
                             'border-radius: 9999px; box-shadow: none; animation: none; -gtk-icon-shadow: none; '
                             'background-repeat: no-repeat; background-position: center; }' % (t, t))
        for b in ('close', 'maximize', 'minimize'):
            # maximize has a second variant: maximized window (restore)
            variants = [(False, b)] + ([(True, 'restore')] if b == 'maximize' else [])
            for maxed, name in variants:
                # custom icon for this variant; without a restore icon, use the maximize one
                custom = name if name in self.custom else (b if b in self.custom else None)
                if self.style == 'zorin' and not custom:
                    continue
                pre = ('window.maximized ' if gtk == 4 else '.maximized ') if maxed else ''
                if gtk == 4 and self.style == 'zorin':
                    lines.append(f'{pre}windowcontrols > button.{b} > image {{ -gtk-icon-filter: opacity(0); }}')
                if gtk == 3:
                    lines.append(f'{pre}button.titlebutton.{b} image {{ color: transparent; -gtk-icon-shadow: none; }}')
                states = button_states(self.style, b, self.cfg['symbols'], self.button_color(b), bool(custom))
                for state, (color, img, effect) in states.items():
                    if gtk == 4:
                        sel = f'{pre}windowcontrols > button.{b}{state} > image'
                    else:
                        sel = f'{pre}button.titlebutton.{b}{state}'
                    props = []
                    if color:
                        props.append(f'background-color: {color};')
                    if img:
                        file = custom if img == 'custom' else name
                        props.append(f'background-image: {self.url(file, img)}; background-size: {t}px {t}px; '
                                     'background-repeat: no-repeat; background-position: center;')
                    else:
                        props.append('background-image: none;')
                    if effect == 'darken':
                        props.append('box-shadow: inset 0 0 0 100px rgba(0, 0, 0, 0.15);')
                    elif color:
                        props.append('box-shadow: none;')
                    if self.style == 'plain' or custom:
                        props.append('opacity: %s;' % ('0.55' if effect == 'dim' else '1'))
                    lines.append(f'{sel} {{ {" ".join(props)} }}')
        return '\n'.join(lines) + '\n'

    # --- glass rules ---
    def glass(self, gtk):
        a, b = self.a, self.b
        if a >= 1 and b >= 1:
            return ''
        f = self.bg
        lines = ['', '/* own-theme: glass (translucent backgrounds; the blur comes from the Blur my Shell extension) */']
        if gtk == 4:
            if a < 1:
                s = sidebar_opacity(a)
                lines += [
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
                lines += [
                    f'@define-color view_bg_color alpha({f("#161c1f")},{b:g});',
                    f'@define-color view_backdrop_color alpha({f("#171c1f")},{b:g});',
                    f'@define-color card_bg_color alpha({f("#161c1f")},{b:g});',
                    f'@define-color card_backdrop_color alpha({f("#171c1f")},{b:g});',
                ]
        else:
            if a < 1:
                lines += [
                    f'.background {{ background-color: alpha({f("#222b30")},{a:g}); }}',
                    f'.background:backdrop {{ background-color: alpha({f("#1e2428")},{a:g}); }}',
                    # with a transparent title bar, the top corners come from the background
                    f'.background.csd {{ border-radius: {self.window_radius()}px; }}',
                    '.background.csd.maximized, .background.csd.fullscreen, .background.csd.tiled, '
                    '.background.csd.tiled-top, .background.csd.tiled-right, .background.csd.tiled-bottom, '
                    '.background.csd.tiled-left, .background.csd.solid-csd { border-radius: 0; }',
                    '.titlebar:not(headerbar), headerbar, .titlebar:backdrop:not(headerbar), headerbar:backdrop, '
                    'toolbar, toolbar:backdrop, searchbar > revealer > box, searchbar > revealer > box:backdrop, '
                    '.inline-toolbar, .inline-toolbar:backdrop, .location-bar, .location-bar:backdrop '
                    '{ background-color: transparent; }',
                ]
            if b < 1:
                lines += [
                    f'.view, iconview, list {{ background-color: alpha({f("#161c1f")},{b:g}); }}',
                    f'.view:backdrop, iconview:backdrop, list:backdrop {{ background-color: alpha({f("#171c1f")},{b:g}); }}',
                    '.view text, iconview text, textview text, .view text:backdrop, iconview text:backdrop, '
                    'textview text:backdrop { background-color: transparent; }',
                ]
        return '\n'.join(lines) + '\n'

    def css(self, gtk):
        return self.glass(gtk) + self.buttons(gtk)


# Builds a dedicated pipeline in Blur my Shell (static blur + rounded corners).
# Runs on the system Python, which has the gi module.
PIPELINE_SCRIPT = r"""
import sys, gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib
folder, sigma, radius = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
source = Gio.SettingsSchemaSource.new_from_directory(folder, Gio.SettingsSchemaSource.get_default(), False)
s = Gio.Settings.new_full(source.lookup('org.gnome.shell.extensions.blur-my-shell', False), None, None)
current = s.get_value('pipelines')
new = {}
for i in range(current.n_children()):
    pair = current.get_child_value(i)
    d = pair.get_child_value(1)
    new[pair.get_child_value(0).get_string()] = {
        d.get_child_value(k).get_child_value(0).get_string(): d.get_child_value(k).get_child_value(1).get_variant()
        for k in range(d.n_children())}
V = GLib.Variant
effects = V('av', [  # same format as the extension's pipelines: a list of variants
    V('a{sv}', {'type': V('s', 'native_static_gaussian_blur'), 'id': V('s', 'effect_own_theme_blur'),
                'params': V('a{sv}', {'radius': V('i', sigma), 'unscaled_radius': V('i', sigma),
                                      'brightness': V('d', 1.0)})}),
    V('a{sv}', {'type': V('s', 'corner'), 'id': V('s', 'effect_own_theme_corner'),
                'params': V('a{sv}', {'radius': V('d', radius)})}),
])
new['pipeline_own_theme'] = {'name': V('s', 'own-theme (blur + corners)'), 'effects': effects}
s.set_value('pipelines', V('a{sa{sv}}', new))
Gio.Settings.sync()
"""


def configure_blur(cfg):
    """Turn on app blur in Blur my Shell (only if blur = yes)."""
    if cfg['blur'] != 'yes':
        return
    uuid = 'blur-my-shell@aunetx'
    folders = [os.path.expanduser(f'~/.local/share/gnome-shell/extensions/{uuid}/schemas'),
               f'/usr/share/gnome-shell/extensions/{uuid}/schemas']
    folder = next((p for p in folders if os.path.exists(os.path.join(p, 'gschemas.compiled'))), None)
    if not folder:
        print('Blur: the Blur my Shell extension is not installed. '
              'Get it from https://extensions.gnome.org/extension/3193/blur-my-shell/ and run again.')
        return
    radius = round(15 * float(cfg['radius']))
    static = cfg['blur_mode'] == 'static'
    if static:
        r = subprocess.run(['/usr/bin/python3', '-c', PIPELINE_SCRIPT, folder, cfg['blur_strength'], str(radius)])
        if r.returncode:
            print('Blur: could not create the rounded-corner pipeline; falling back to dynamic mode.')
            static = False
    schema = 'org.gnome.shell.extensions.blur-my-shell.applications'
    values = {
        'blur': 'true', 'enable-all': 'true', 'customize': 'true',
        'opacity': '255',            # the window stays opaque; transparency comes from the theme
        'dynamic-opacity': 'false',
        'sigma': str(int(cfg['blur_strength'])),
        'brightness': '1.0',
        'corner-radius': str(radius),
        'static-blur': 'true' if static else 'false',
    }
    if static:
        values['pipeline'] = "'pipeline_own_theme'"
    failed = [k for k, v in values.items()
              if subprocess.run([GSETTINGS, '--schemadir', folder, 'set', schema, k, v]).returncode]
    if failed:
        print('Blur: could not set ' + ', '.join(failed) + ' (different Blur my Shell version?)')
    elif static:
        print(f"Blur: Blur my Shell is blurring the wallpaper behind apps, {radius}px corners "
              f"(strength {cfg['blur_strength']}).")
    else:
        print(f"Blur: Blur my Shell is blurring everything behind apps (strength {cfg['blur_strength']}); "
              'on GNOME 46 this mode has square corners.')


# ---------- main ----------

def read_conf(path):
    # format "key = value  # comment"; values never contain spaces,
    # so we only take the first word (the '#' of a color is not a comment)
    cfg = dict(DEFAULTS)
    if not os.path.exists(path):
        sys.exit(f'Error: {path} not found')
    with open(path) as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith(('#', ';', '[')):
                continue
            if '=' not in line:
                sys.exit(f'Error on line {n} of {path}: expected "key = value"')
            key, value = (x.strip() for x in line.split('=', 1))
            if key not in DEFAULTS:
                sys.exit(f'Error on line {n}: unknown option "{key}". '
                         f'Options: {", ".join(DEFAULTS)}')
            cfg[key] = value.split()[0] if value else ''
    for k in COLOR_KEYS:
        if not HEX.fullmatch(cfg[k]):
            sys.exit(f'Error: "{k} = {cfg[k]}" is not a valid hex color (e.g. #222b30)')
    error = validate_extras(cfg, os.path.dirname(os.path.abspath(path)))
    if error:
        sys.exit('Error: ' + error)
    on_accent = cfg['text_on_accent']
    if on_accent != 'auto' and not HEX.fullmatch(on_accent):
        sys.exit('Error: text_on_accent must be "auto" or a hex color')
    if not re.fullmatch(r'[\w.+-]+', cfg['name']):
        sys.exit('Error: the theme name may only contain letters, digits, "-", "_" and "."')
    return cfg


def validate_extras(cfg, base):
    """Check the glass and button options; resolve icon paths."""
    for k in ('window_opacity', 'content_opacity'):
        try:
            v = float(cfg[k])
        except ValueError:
            v = -1
        if not 0.3 <= v <= 1:
            return f'"{k} = {cfg[k]}" must be a number from 0.3 to 1 (1 = opaque)'
        cfg[k] = '%g' % v
    choices = {'blur': ('yes', 'no'), 'blur_mode': ('static', 'dynamic'), 'buttons': ('zorin', 'circles', 'plain'),
               'symbols': ('always', 'hover', 'never'), 'glyphs': tuple(GLYPHS)}
    for k, ok in choices.items():
        if cfg[k] not in ok:
            return f'"{k} = {cfg[k]}" must be one of: {", ".join(ok)}'
    if not cfg['blur_strength'].isdigit() or not 0 <= int(cfg['blur_strength']) <= 100:
        return 'blur_strength must be an integer from 0 to 100'
    if not cfg['button_size'].isdigit() or not 16 <= int(cfg['button_size']) <= 26:
        return 'button_size must be an integer from 16 to 26 (px)'
    for b in ('close', 'maximize', 'minimize'):
        v = cfg['button_' + b]
        if v != 'auto' and not HEX.fullmatch(v):
            return f'"button_{b} = {v}" must be "auto" or a hex color'
    for b in BUTTONS:
        k = 'icon_' + b
        v = cfg[k]
        if v in ('', 'none'):
            cfg[k] = 'none'
            continue
        path = os.path.join(base, os.path.expanduser(v))
        if not os.path.isfile(path):
            return f'"{k} = {v}": file not found (the path is relative to the palette.conf folder)'
        if os.path.splitext(path)[1].lower() not in ('.svg', '.png'):
            return f'"{k} = {v}": use a .svg or .png file'
        cfg[k] = path
    return None


def generated_by_us(folder):
    return any(os.path.exists(os.path.join(folder, m)) for m in (MARKER,) + LEGACY_MARKERS)


def generate(cfg):
    if not os.path.isdir(SOURCE):
        sys.exit(f'Error: source theme {SOURCE} not found. Install the Zorin desktop themes '
                 '(see README) or point OWN_THEME_SOURCE at a ZorinBlue-Dark folder.')
    dest = os.path.expanduser(f"~/.themes/{cfg['name']}")
    if os.path.realpath(dest) == os.path.realpath(SOURCE):
        sys.exit('Error: the destination cannot be the original theme')
    if os.path.exists(dest):
        if not generated_by_us(dest):
            sys.exit(f'Error: {dest} already exists and was not created by this script. '
                     'Pick another "name" in palette.conf.')
        shutil.rmtree(dest)
    shutil.copytree(SOURCE, dest, ignore=shutil.ignore_patterns('xfwm4'))
    open(os.path.join(dest, MARKER), 'w').close()

    g = Generator(cfg)
    for root, _, files in os.walk(dest):
        for name in files:
            p = os.path.join(root, name)
            rel = os.path.relpath(p, dest)
            if name.endswith('.css'):
                new = g.css(open(p).read())
            elif rel == 'gtk-2.0/gtkrc':
                new = g.gtkrc(open(p).read())
            elif name.endswith('.svg') and not name.endswith('-light.svg'):
                new = g.svg(open(p).read(), name)
            elif name == 'index.theme':
                new = re.sub(r'ZorinBlue-Dark', cfg['name'], open(p).read())
                new = re.sub(r'(?m)^IconTheme=.*$', 'IconTheme=ZorinBlue-Dark', new)
                new = re.sub(r'(?m)^Comment=.*$', 'Comment=Generated by own-theme (generate-theme.py)', new)
            else:
                continue
            with open(p, 'w') as f:
                f.write(new)

    extras = Extras(cfg)
    if extras.active():
        for gtk in (3, 4):
            folder = os.path.join(dest, f'gtk-{gtk}.0')
            for name, data in extras.files().items():
                with open(os.path.join(folder, 'assets', name), 'wb') as f:
                    f.write(data)
            rules = extras.css(gtk)
            for name in ('gtk.css', 'gtk-dark.css'):
                with open(os.path.join(folder, name), 'a') as f:
                    f.write(rules)
    return dest, g


def apply(cfg):
    name = cfg['name']
    cmds = [
        [GSETTINGS, 'set', 'org.gnome.desktop.interface', 'color-scheme', 'prefer-dark'],
        [GSETTINGS, 'set', 'org.gnome.desktop.interface', 'gtk-theme', name],
        [GSETTINGS, 'set', 'org.gnome.shell.extensions.user-theme', 'name', name],
    ]
    for c in cmds:
        subprocess.run(c, check=False)
    configure_blur(cfg)


def main():
    if '-h' in sys.argv or '--help' in sys.argv:
        print(__doc__)
        return
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    conf = args[0] if args else os.path.join(HERE, 'palette.conf')
    cfg = read_conf(conf)
    if '--blur' in sys.argv:  # only configure Blur my Shell (used by install.sh)
        configure_blur(cfg)
        return
    dest, g = generate(cfg)
    print(f'Theme generated in {dest}')
    print('Colors changed per family:', ', '.join(f'{k}={v}' for k, v in sorted(g.stats.items())))
    print(f"Text on accent: {g.target['on_accent']}")
    if '--apply' in sys.argv:
        apply(cfg)
        print('Theme applied. Close and reopen your apps to see the change.')
    else:
        print(f'To activate: python3 {os.path.abspath(__file__)} --apply')


if __name__ == '__main__':
    main()
