#!/usr/bin/python3
"""Render a GTK3 test window OFF-SCREEN and save it as PNG.

Needs a Python with the gi module (PyGObject), usually the system one:
  GDK_BACKEND=x11 GTK_THEME=ZorinCustom-Dark /usr/bin/python3 tools/render-gtk3.py out.png
To compare side by side:  convert a.png b.png +append side.png
"""
import sys, gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

w = Gtk.OffscreenWindow()
outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
hb = Gtk.HeaderBar(title='Files', subtitle='GTK3 test'); hb.set_show_close_button(True)
hb.set_decoration_layout('menu:minimize,maximize,close')
hb.pack_start(Gtk.Button.new_from_icon_name('go-previous-symbolic', 1))
sw = Gtk.Box(); sw.get_style_context().add_class('linked')
for t in ('List', 'Grid'): sw.add(Gtk.ToggleButton(label=t))
hb.pack_end(sw); outer.add(hb)
inner = Gtk.Box(); outer.add(inner)
side = Gtk.ListBox(); side.get_style_context().add_class('sidebar'); side.set_size_request(150, -1)
for t in ('Home', 'Documents', 'Downloads', 'Pictures', 'Trash'): side.add(Gtk.Label(label=t, xalign=0, margin=8))
side.select_row(side.get_row_at_index(1)); inner.add(side)
g = Gtk.Grid(row_spacing=10, column_spacing=10, margin=16); inner.pack_start(g, True, True, 0)
g.attach(Gtk.Entry(text='Typed text'), 0, 0, 2, 1)
g.attach(Gtk.Entry(placeholder_text='Placeholder'), 2, 0, 1, 1)
for i, (label, cls) in enumerate((('Normal', None), ('Suggested', 'suggested-action'), ('Delete', 'destructive-action'))):
    b = Gtk.Button(label=label)
    if cls: b.get_style_context().add_class(cls)
    g.attach(b, i, 1, 1, 1)
s = Gtk.Switch(active=True); s.set_halign(1); g.attach(s, 0, 2, 1, 1)
s2 = Gtk.Switch(); s2.set_halign(1); g.attach(s2, 1, 2, 1, 1)
g.attach(Gtk.CheckButton(label='Checked', active=True), 2, 2, 1, 1)
sc = Gtk.Scale.new_with_range(0, 0, 100, 1); sc.set_value(60); sc.set_draw_value(False); g.attach(sc, 0, 3, 3, 1)
g.attach(Gtk.ProgressBar(fraction=0.4), 0, 4, 3, 1)
l = Gtk.Label(); l.set_markup('Normal text  <a href="#">link</a>'); g.attach(l, 0, 5, 2, 1)
g.attach(Gtk.Label(label='Disabled', sensitive=False), 2, 5, 1, 1)
ib = Gtk.InfoBar(message_type=Gtk.MessageType.WARNING); ib.get_content_area().add(Gtk.Label(label='Sample warning'))
g.attach(ib, 0, 6, 3, 1)
w.add(outer); w.set_size_request(620, 380); w.show_all()


def shot():
    w.get_pixbuf().savev(sys.argv[1] if len(sys.argv) > 1 else 'gtk3.png', 'png', [], [])
    Gtk.main_quit()


GLib.timeout_add(400, shot)
Gtk.main()
