#!/usr/bin/python3
"""Renderiza uma janela libadwaita (GTK4) de teste FORA da tela e salva um PNG.

Usa o broadway (servidor GTK em memória), então nada aparece na sua tela.
Precisa do Python do sistema (o python3 do linuxbrew não tem o módulo gi):
  gtk4-broadwayd :5 &
  GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 GTK_THEME=OwnTeste-Dark \
      /usr/bin/python3 ferramentas/renderizar-gtk4.py saida.png [estado]
estado: normal (padrão), hover (mouse em cima do fechar), backdrop (janela sem
foco) ou maximizada. O fundo do PNG fica transparente onde o tema é translúcido.
"""
import sys, gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

saida = sys.argv[1] if len(sys.argv) > 1 else 'gtk4.png'
estado = sys.argv[2] if len(sys.argv) > 2 else 'normal'


def montar(app):
    # o relógio de quadros do broadway fica parado: transições nunca terminariam
    Gtk.Settings.get_default().props.gtk_enable_animations = False
    win = Adw.ApplicationWindow(application=app, title='Arquivos')
    win.set_default_size(680, 420)
    split = Adw.NavigationSplitView(min_sidebar_width=160, max_sidebar_width=160)

    lado = Adw.ToolbarView()
    lado.add_top_bar(Adw.HeaderBar(show_title=False))
    lista = Gtk.ListBox(css_classes=['navigation-sidebar'])
    for t in ('Início', 'Documentos', 'Downloads', 'Imagens', 'Lixeira'):
        lista.append(Gtk.Label(label=t, xalign=0))
    lista.select_row(lista.get_row_at_index(1))
    lado.set_content(lista)
    split.set_sidebar(Adw.NavigationPage(title='Lugares', child=lado))

    conteudo = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_decoration_layout(':minimize,maximize,close')
    hb.pack_start(Gtk.Button(icon_name='go-previous-symbolic'))
    conteudo.add_top_bar(hb)
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                    margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
    grupo = Adw.PreferencesGroup(title='Arquivos recentes')
    for t, s in (('Planilha de gastos.ods', '12 KB'), ('Contrato assinado.pdf', '340 KB')):
        grupo.add(Adw.ActionRow(title=t, subtitle=s))
    caixa.append(grupo)
    caixa.append(Gtk.Entry(text='relatorio-final.odt'))
    linha = Gtk.Box(spacing=8)
    for rot, cls in (('Cancelar', None), ('Salvar', 'suggested-action'), ('Apagar', 'destructive-action')):
        b = Gtk.Button(label=rot)
        if cls:
            b.add_css_class(cls)
        linha.append(b)
    linha.append(Gtk.Switch(active=True, valign=Gtk.Align.CENTER))
    caixa.append(linha)
    conteudo.set_content(caixa)
    split.set_content(Adw.NavigationPage(title='Documentos', child=conteudo))
    # Sem navegador conectado o broadway nunca pinta um quadro, então o
    # WidgetPaintable sai vazio. snapshot_child() monta a árvore de desenho
    # direto. A janela em si não entra, por isso o conteúdo fica numa caixa
    # com a classe .background (a mesma regra de fundo da janela).
    moldura = Gtk.Box(css_classes=['background'])
    split.set_hexpand(True)
    moldura.append(split)
    win.set_content(moldura)
    if estado == 'maximizada':
        win.maximize()
    win.present()

    def botao_fechar(w):
        if w.get_css_name() == 'button' and w.has_css_class('close'):
            return w
        c = w.get_first_child()
        while c:
            r = botao_fechar(c)
            if r:
                return r
            c = c.get_next_sibling()
        return None

    def foto():
        if estado == 'hover':
            b = botao_fechar(win)
            if b:
                b.set_state_flags(Gtk.StateFlags.PRELIGHT, False)
        if estado == 'backdrop':
            win.set_state_flags(Gtk.StateFlags.BACKDROP, False)
        GLib.timeout_add(300, salvar)
        return False

    def salvar():
        try:
            snap = Gtk.Snapshot()
            moldura.get_parent().snapshot_child(moldura, snap)
            tex = win.get_native().get_renderer().render_texture(snap.to_node(), None)
            tex.save_to_png(saida)
        finally:
            app.quit()
        return False

    GLib.timeout_add(500, foto)


app = Adw.Application(application_id='own.theme.Renderizar', flags=Gio.ApplicationFlags.NON_UNIQUE)
app.connect('activate', montar)
app.run([])
