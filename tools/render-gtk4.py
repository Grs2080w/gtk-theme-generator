#!/usr/bin/python3
"""Render a libadwaita (GTK4) test window OFF-SCREEN and save it as PNG.

Uses broadway (an in-memory GTK server), so nothing shows up on your screen.
Needs a Python with the gi module (PyGObject), usually the system one:
  gtk4-broadwayd --address 127.0.0.1 :5 &
  GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 GTK_THEME=MyTheme-Dark \
      /usr/bin/python3 tools/render-gtk4.py out.png [state]
state: normal (default), hover (pointer over close), backdrop (unfocused
window) or maximized. The PNG background is transparent where the theme is translucent.
"""
import sys, gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

out = sys.argv[1] if len(sys.argv) > 1 else 'gtk4.png'
state = sys.argv[2] if len(sys.argv) > 2 else 'normal'


def build(app):
    # broadway's frame clock never ticks: transitions would never finish
    Gtk.Settings.get_default().props.gtk_enable_animations = False
    win = Adw.ApplicationWindow(application=app, title='Files')
    win.set_default_size(680, 420)
    split = Adw.NavigationSplitView(min_sidebar_width=160, max_sidebar_width=160)

    side = Adw.ToolbarView()
    side.add_top_bar(Adw.HeaderBar(show_title=False))
    places = Gtk.ListBox(css_classes=['navigation-sidebar'])
    for t in ('Home', 'Documents', 'Downloads', 'Pictures', 'Trash'):
        places.append(Gtk.Label(label=t, xalign=0))
    places.select_row(places.get_row_at_index(1))
    side.set_content(places)
    split.set_sidebar(Adw.NavigationPage(title='Places', child=side))

    content = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_decoration_layout(':minimize,maximize,close')
    hb.pack_start(Gtk.Button(icon_name='go-previous-symbolic'))
    content.add_top_bar(hb)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                  margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
    group = Adw.PreferencesGroup(title='Recent files')
    for t, s in (('Expenses.ods', '12 KB'), ('Signed contract.pdf', '340 KB')):
        group.add(Adw.ActionRow(title=t, subtitle=s))
    box.append(group)
    box.append(Gtk.Entry(text='final-report.odt'))
    row = Gtk.Box(spacing=8)
    for label, cls in (('Cancel', None), ('Save', 'suggested-action'), ('Delete', 'destructive-action')):
        b = Gtk.Button(label=label)
        if cls:
            b.add_css_class(cls)
        row.append(b)
    row.append(Gtk.Switch(active=True, valign=Gtk.Align.CENTER))
    box.append(row)
    content.set_content(box)
    split.set_content(Adw.NavigationPage(title='Documents', child=content))
    # Without a connected browser broadway never paints a frame, so the
    # WidgetPaintable comes out empty. snapshot_child() builds the render
    # tree directly. The window itself is not included, so the content sits
    # in a box with the .background class (the same rule as the window background).
    frame = Gtk.Box(css_classes=['background'])
    split.set_hexpand(True)
    frame.append(split)
    win.set_content(frame)
    if state == 'maximized':
        win.maximize()
    win.present()

    def close_button(w):
        if w.get_css_name() == 'button' and w.has_css_class('close'):
            return w
        c = w.get_first_child()
        while c:
            r = close_button(c)
            if r:
                return r
            c = c.get_next_sibling()
        return None

    def prepare():
        if state == 'hover':
            b = close_button(win)
            if b:
                b.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        if state == 'backdrop':
            win.set_state_flags(Gtk.StateFlags.BACKDROP, False)
        GLib.timeout_add(300, save)
        return False

    def save():
        try:
            snap = Gtk.Snapshot()
            frame.get_parent().snapshot_child(frame, snap)
            tex = win.get_native().get_renderer().render_texture(snap.to_node(), None)
            tex.save_to_png(out)
        finally:
            app.quit()
        return False

    GLib.timeout_add(500, prepare)


app = Adw.Application(application_id='io.github.own_theme.Render', flags=Gio.ApplicationFlags.NON_UNIQUE)
app.connect('activate', build)
app.run([])
