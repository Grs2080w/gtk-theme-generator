# own-theme — contexto para continuar o trabalho

Este arquivo é a passagem de bastão: tudo o que a sessão anterior descobriu e
decidiu. Leia antes de mexer em qualquer coisa. O README é o guia do usuário;
este arquivo é o guia de quem desenvolve.

## Quem é o usuário e o que ele quer

- Fala português (BR). Responda em português.
- Usa **Zorin OS 17** (GNOME Shell 46, Wayland, shell `fish`). E-mail: gabriel.2008grs@gmail.com.
- Objetivo: ter um tema próprio, **só escuro (Dark)**, onde ele escolhe as cores facilmente.
- Decisões que ele já tomou (não pergunte de novo):
  1. Só a variante Dark; nada de Light.
  2. **O destaque é separado do tom do fundo** (no Zorin original os dois têm o mesmo tom).
  3. Quer o editor visual (página interativa), além do script.
  4. Quer que o tema gerado vá para a **pasta do sistema** (`/usr/share/themes`), feito pelo `instalar.sh`.
- Tema ativo quando a primeira sessão começou: ZorinBlue-Light. Em 2026-10-11 ele já tinha rodado
  o `instalar.sh --aplicar`: **ZorinCustom-Dark está ativo** (gtk-theme, user-theme, `prefer-dark`),
  instalado em `/usr/share/themes` (o caminho com sudo funciona). Tema de ícones: ZorinBlue-Light.
  Ordem dos botões: `appmenu:minimize,maximize,close`.
- O `palette.conf` da pasta é **dele** (cores próprias). Para testes use um conf temporário com
  outro `nome` (ex: `OwnTeste-Dark`); nunca gere `~/.themes/ZorinCustom-Dark`, porque ele esconderia
  o tema ativo em `/usr/share/themes`.
- 5. Pediu (2026-10-11): fundos com blur, trocar os ícones dos botões de janela, tudo pelo HTML,
  e dicas de onde conseguir/como fazer ícones. Feito; ver "Extras" abaixo.

## Estado atual (2026-10-11)

Pronto e testado:
- `gerar-tema.py`: gerador completo.
- `palette.conf`: as cores do usuário (a paleta padrão do código reproduz o ZorinBlue-Dark).
- `instalar.sh`: gera, move para /usr/share/themes e ativa com `--aplicar`.
  Testado com `OWN_THEME_DESTINO=<pasta temporária>`; o caminho com sudo o próprio usuário já rodou com sucesso.
- `pagina/estudio.html`: editor visual. Publicado como artifact privado em
  https://claude.ai/artifact/1SudfjPBKYWFqHy62aCgxA.
  - Para atualizar o artifact, use a ferramenta Artifact com `url` desse link; leia o artifact antes (`action: read`).
  - Versão 5 publicada em 2026-10-11 (vidro, blur_modo, botões, ícones próprios, temas prontos, harmonia).
    Depois de editar o HTML, republique.
- `ferramentas/`: exportar-cores, comparar-variantes, renderizar-gtk3, renderizar-gtk4.

Não verificado ainda:
- Apps **GTK4/libadwaita** (Configurações, Arquivos) rodando de verdade com o tema gerado. Só o CSS foi conferido.
- **GNOME Shell** rodando de verdade com o tema gerado. Só o CSS foi conferido.
- A ativação real com os extras (vidro/botões/blur): só renders offscreen.

O projeto ficava em `~/zorin-tema`; o usuário vai movê-lo para uma pasta de trabalho com o nome
`own-theme` e transformar em repositório git. Nenhum caminho do projeto é fixo,
**exceto** a origem `/usr/share/themes/ZorinBlue-Dark` (que é do sistema).

## Extras: vidro e botões da janela (2026-10-11)

Opções novas no `palette.conf` (todas em `PADRAO`; com o valor padrão **nada é acrescentado** e a
regressão byte a byte continua valendo). A classe `Extras` do gerador **acrescenta regras no fim**
de `gtk-3.0/gtk(-dark).css` e `gtk-4.0/gtk(-dark).css` e grava SVGs `own-*.svg` em `assets/`.
O gnome-shell.css não é tocado.

- **Vidro**: `opacidade_janela`, `opacidade_conteudo` (0.3–1).
  - GTK4: redefine `@define-color` no fim do arquivo (o último vence; testado). window/backdrop com alfa,
    `headerbar_*` transparente (fica sobre o fundo da janela), sidebar com alfa `a³` (`opacidade_sidebar`,
    porque soma por cima da janela), `dialog_bg_color` opaco, view/card com o alfa do conteúdo.
  - GTK3: regras para `.background`, headerbar/toolbar/searchbar transparentes, `.view`/`iconview`/`list`.
  - **O blur não é do tema** (CSS do GTK/Shell não tem backdrop-filter). Vem da extensão **Blur my Shell
    v74** (instalada em `~/.local/share/gnome-shell/extensions/blur-my-shell@aunetx`). `blur = sim` +
    `instalar.sh --aplicar` → `gerar-tema.py --blur` ajusta `...blur-my-shell.applications` via
    `gsettings --schemadir`: blur, enable-all, opacity 255 (a opacidade dela deixaria o texto translúcido),
    dynamic-opacity false, sigma = `blur_forca`, corner-radius = 15×raio. `blur = nao` não mexe em nada.
    Teste sem efeito real: `GSETTINGS_BACKEND=memory python3 gerar-tema.py --blur conf`.
  - **Cantos**: no GNOME 46 o `Shell.BlurEffect` não tem `corner-radius`, então o blur **dinâmico** de apps da
    extensão é sempre um retângulo reto (o usuário viu e reclamou). `blur_modo = estatico` (padrão) liga
    `static-blur` e cria o pipeline `pipeline_own_theme` (native_static_gaussian_blur + corner com 15×raio)
    via `SCRIPT_PIPELINE`, que roda em `/usr/bin/python3` com gi e preserva os outros pipelines (formato `av`).
    Estático borra só o papel de parede. Aplicado de verdade na máquina dele em 2026-10-11.
  - GTK3 com vidro: `.background.csd` ganha raio nos 4 cantos (a barra transparente deixava os de cima retos).
  - Painel/menus do Shell: a extensão já borra e troca o fundo (`override-background true`), por isso
    não existe opção de opacidade do painel.
- **Botões**: `botoes` (zorin|circulos|simples), `glifos` (linhas|setas|mac), `simbolos` (sempre|hover|nunca),
  `botao_tamanho` (16–26; GTK3 não deixa o botão menor que o ícone de 16), `botao_<b>` (auto = erro/sucesso/aviso),
  `icone_<b>` para fechar/maximizar/minimizar/restaurar (caminho relativo à pasta do conf; vira o botão
  inteiro em qualquer estilo; restaurar cai no de maximizar).
  - GTK4: desenha no nó `windowcontrols > button.X > image` (fundo + background-image) e esconde o
    símbolo com `-gtk-icon-filter: opacity(0)` (não usar `color: transparent`: o círculo do Zorin usa currentColor).
    Maximizada: `window.maximized …`.
  - GTK3: desenha no próprio `button.titlebutton.X` e esconde o `image` com `color: transparent`. Maximizada: `.maximized …`.
  - Estados: '', :hover, :active, :backdrop, :backdrop:hover (`estados_botao`).
- `icones/exemplo-*.svg`: modelos de ícone próprio (losangos).
- Página: temas prontos em grupos (Zorin, Paletas famosas, Combinações, Completos). Os "completos" também
  definem raio/vidro/botões (`EXTRAS_KEYS`); os outros trocam só as cores. **Harmonia** (`st.harmonia`, só
  da página, não vai para o conf): ao mudar fundo/destaque, `harmonizar()` recalcula texto (quase branco no
  tom do destaque), erro/aviso/sucesso (tons 0/18/157 na intensidade do destaque) e sobe a luminosidade do
  destaque até contraste 3:1 com o fundo. Pedido do usuário: poder ligar e desligar.
- Paridade JS↔Python das funções novas (`GLIFOS`, `svg_glifo`, `estados_botao`, `opacidade_sidebar`):
  conferida com node, 45 casos, 0 diferenças. Se mudar uma, mude a outra.

Testado: GTK3 (renderizar-gtk3) e **libadwaita real** (renderizar-gtk4) com vidro, círculos, simples,
ícone próprio e estilo zorin + ícone próprio, nos estados normal/hover/backdrop/maximizada; fluxo página →
palette.conf → gerar-tema.py com ícone; importação ida e volta na página. **Não testado**: blur real na
sessão dele (não liguei o Blur my Shell de apps na máquina) e apps rodando de verdade com o tema novo.

### Testes visuais
- GTK4: `gtk4-broadwayd --address 127.0.0.1 :5` (sem `--address` ele escuta em todas as interfaces).
  Sem navegador conectado o broadway **não pinta quadros**: `WidgetPaintable` sai vazio e transições
  nunca terminam. Por isso a ferramenta usa `snapshot_child()` e desliga animações.
- Página: o Chromium headless do Playwright está em `~/.cache/ms-playwright/chromium_headless_shell-1243`
  (não há o pacote node do playwright); dá para dirigir via CDP com o WebSocket nativo do Node 22.
- Cuidado com `pkill -f <padrão>`: ele casa com o próprio shell do comando.
- Sem commits no repositório, o EnterWorktree falha (não há HEAD).

## Anatomia do tema Zorin (o que foi descoberto)

Fonte: `/usr/share/themes/ZorinBlue-Dark` (pacote do Zorin; **nunca altere**).
Existia uma cópia idêntica em `~/.themes/ZorinBlue-Dark`; ela não é necessária.

| Pasta | Controla | Formato das cores |
|---|---|---|
| `gtk-3.0/gtk.css` (2384 linhas) | apps GTK3 | CSS compilado de SASS, cores escritas direto (84 distintas). `@define-color` no fim são só exportações |
| `gtk-4.0/gtk.css` (2773 linhas) | apps GTK4/libadwaita | `@define-color` estilo libadwaita nas linhas 2–105 (accent_bg_color, window_bg_color…) mais cores escritas direto |
| `gnome-shell/gnome-shell.css` | painel, overview, menus, quick settings | cores escritas direto, muitos `rgba(189,230,251,α)` |
| `gnome-shell/assets/*.svg` | toggles, checkboxes, calendário | `fill="#…"` escrito direto |
| `gtk-2.0/gtkrc` | apps GTK2 | uma linha `gtk_color_scheme = "fg_color:#…\n…"` |
| `xfwm4/` | bordas de janela do XFCE | PNG/XPM; **inútil no GNOME, removido no tema gerado** |
| `index.theme` | metadados | nome, IconTheme, ButtonLayout |

Fatos importantes:
- `gtk.css` e `gtk-dark.css` são idênticos (nas duas versões do GTK).
- Não existe código-fonte SCSS. A estratégia é reescrever o CSS compilado.
- `gtk-4.0/.libadwaita` é um marcador vazio. O **libadwaita do Zorin é modificado** (`libadwaita-1-0 1.5.0-1ubuntu2+zorin1`)
  para carregar `/usr/share/themes/%s/gtk-4.0` do tema GTK ativo; o binário também contém a string `.themes`.
  Instalar em `/usr/share/themes` é o caminho garantido, e é por isso que o `instalar.sh` existe.
- O GNOME Shell carrega o tema pela extensão **user-theme** (`org.gnome.shell.extensions.user-theme name`),
  que lê `<tema>/gnome-shell/gnome-shell.css`. O `gnome-shell-theme.gresource` é copiado sem alteração.
- Os `*-light.svg` do shell são do modo claro e o CSS do Dark não usa esses arquivos; são copiados sem alteração.
- `#add` no gtk-4.0 **não é cor**: é parte do seletor `colorswatch#add-color-button`. A regex do gerador já ignora isso.

### A descoberta central

Todas as variantes do Zorin (Blue, Green, Purple, Red, Orange, Yellow, Brown, Grey) são **o mesmo
tema com o tom girado**. A luminosidade fica igual e a saturação muda (Grey = saturação 0).
Blue: tom 200°, Green 158°, Red 0°, Purple 267°. Cores-base oficiais (fundo / destaque):
Blue `#222b30/#bde6fb`, Green `#202b27/#bbf1dd`, Purple `#28232d/#d8c4f1`, Red `#2e1f1f/#fdb4b4`,
Orange `#2e231f/#fcc8b4`, Yellow `#2c281d/#fce8ad`, Brown `#292523/#e5d3ca`, Grey `#2a2a2a/#ffffff`.
Erro `#fb7c7c`, aviso `#faa483` e sucesso `#6ee1b6`/`#4cd9a4` **não mudam** entre as variantes.

Papéis das cores principais (Blue-Dark):

| Cor | Papel |
|---|---|
| `#bde6fb` | destaque **e** texto principal (o mesmo literal; separamos pelo contexto) |
| `#222b30` | fundo da janela, headerbar |
| `#161c1f` | fundo do conteúdo (listas, entries, popovers) **e** texto escuro sobre o destaque |
| `#2d3940` | botão normal, sidebar, trilhos, bordas |
| `#35434a` | botão em hover |
| `#2b343a` | bordas |
| `#415159` | switch desligado, borda de checkbox |
| `#1e2428`, `#171c1f` | janela sem foco (backdrop) |
| `#71848d`, `#6f8896`, `#69818d`, `#3f4b54` | texto apagado / desabilitado / placeholder |
| `#8097a3` | seleção em janela sem foco |
| `rgba(26,33,37,.7)` | painel superior do Shell |

## Como o gerador funciona (`gerar-tema.py`)

1. Copia `/usr/share/themes/ZorinBlue-Dark` para `~/.themes/<nome>` (sem `xfwm4/`) e cria o
   marcador `.gerado-por-zorin-tema`. O gerador e o `instalar.sh` só sobrescrevem/apagam pastas que tenham esse marcador.
   **Não renomeie o marcador** sem tratar os temas já gerados.
2. Para cada cor encontrada (hex de 3 ou 6 dígitos, `rgb()`/`rgba()`), decide a **família** com
   `familia(rgb, contexto)`, olhando a cor **original**:
   - tom 188–208° e S ≥ 5%: cor derivada do Zorin
     - S ≥ 30% → `destaque`, ou `texto` se o contexto for texto
     - S < 30% e L ≤ 20% em contexto texto/marca → `sobre` (texto sobre destaque)
     - senão → `fundo`
   - L ≥ 55% e S ≥ 50%: tom ≥350° ou ≤8° → `erro`; 14–20° → `aviso`; 154–160° → `sucesso`
   - o resto → `fixa` (não muda)
3. **Contexto**: o CSS é percorrido declaração por declaração (os comentários são protegidos antes).
   - `color`, `caret-color`, `-gtk-secondary-caret-color` → `texto`, a não ser que o seletor contenha `link`.
   - `@define-color X`: com `accent` + `fg`, ou `selected_fg` → `marca`; com `fg`/`text`/`title` → `texto`; senão → outro.
   - Paleta nomeada do GNOME (`blue_1`…`dark_5`) é ignorada.
   - gtkrc: as chaves `*fg_color`/`*text_color` → texto; `selected_fg_color` → marca.
   - SVGs `toggle-on`, `checkbox`, `checkbox-focused` → contexto `marca` (o escuro é a "bolinha" sobre o destaque).
4. **Transformação** (`transformar`): cada família tem uma cor de referência (`REF`) e uma cor escolhida.
   - tom: `h + (h_escolhida − h_ref)`
   - saturação: `s × s_escolhida / s_ref`, limitada a 1
   - luminosidade: mapa por partes `0→0`, `L_ref→L_escolhida`, `1→1`
   - o alfa do `rgba` é preservado.
5. `texto_sobre_destaque = auto` → se a luminância do destaque for > 0.3, usa o `#161c1f`
   transformado pela família fundo; senão, `#ffffff`.
6. `raio`: multiplica os valores em px das propriedades `border*-radius` menores que 99px (pílulas ficam iguais).
7. `index.theme`: troca o nome e mantém `IconTheme=ZorinBlue-Dark`.

Garantias que foram testadas:
- Com a paleta padrão, a saída é **byte a byte igual** ao original. Só o `index.theme` muda.
  Use isso como teste de regressão sempre que mexer no parser:
  `python3 gerar-tema.py && diff -rq /usr/share/themes/ZorinBlue-Dark ~/.themes/ZorinCustom-Dark`
  (as diferenças esperadas são só `index.theme`, `xfwm4` e o marcador).
- `ferramentas/comparar-variantes.py`: mediana 0 e p95 de 2–5 (distância RGB) contra os temas oficiais,
  nos arquivos que se alinham. Os valores altos vêm de desalinhamento de tokens, não de erro.
- Render GTK3 com fundo `#262626`, destaque `#c4a7ff`, texto `#e8e8e8`, erro `#ff6b8a` e raio 1.6:
  fundo e destaque ficaram independentes e corretos.
- A matemática do JS da página é **idêntica** à do Python: as 140 cores foram conferidas, diferença 0.

## O editor (`pagina/estudio.html`)

- É um HTML único, sem build. O JS reimplementa `transformar`, `mapL` e `luminancia` do Python.
  **Se mudar a matemática no Python, mude no JS também** e confira a paridade.
- `const SOURCE = [...]` são as cores-fonte `[hex, família, usos]`. Esse dado é gerado por
  `ferramentas/exportar-cores.py`; não edite à mão.
- A prévia usa as cores originais exatas de cada widget (tabela acima) passadas pela transformação.
- Ao passar o mouse num controle, as partes da prévia afetadas são contornadas (atributo `data-r` nos elementos).
- Salva o estado no `localStorage` e gera o texto do `palette.conf`; também importa um `palette.conf` colado.
- O visual da página é escuro de propósito (é um editor de tema escuro).

## Armadilhas do ambiente

- **`gsettings` do linuxbrew** (`/home/linuxbrew/.linuxbrew/bin/gsettings`, primeiro no PATH, também no fish)
  usa o backend **keyfile** (`~/.config/glib-2.0/settings/keyfile`), não o dconf: grava num arquivo que o
  GNOME nunca lê. Foi por isso que o blur não funcionou na primeira versão. Os scripts usam
  `/usr/bin/gsettings`. Para conferir o estado real: `dconf dump /org/gnome/shell/extensions/blur-my-shell/`.
  O keyfile ficou com entradas antigas dos scripts; não é lido pelo GNOME.

- O `python3` do PATH é do **linuxbrew** e não tem o módulo `gi` (PyGObject). Para GTK use `/usr/bin/python3`.
  O gerador só usa a biblioteca padrão, então roda em qualquer um.
- O shell do usuário é `fish`; os scripts têm shebang próprio (bash/python).
- No `palette.conf`, `#` é cor **e** comentário. O parser pega só a primeira palavra depois do `=`,
  então `fundo = #222b30  # comentário` funciona. Linhas que começam com `#` são comentário.
- `instalar.sh` usa `sudo` só quando o destino não é gravável. `OWN_THEME_DESTINO=/tmp/x ./instalar.sh` testa sem sudo.
- `~/.themes/<nome>` tem prioridade sobre `/usr/share/themes/<nome>`. Por isso o instalar.sh **move** (não copia);
  senão uma cópia velha em `~/.themes` esconderia a do sistema.

## Próximos passos sugeridos

1. Conferir com o usuário, no tema ativo, Arquivos/Configurações (libadwaita), uma janela GTK3 e, se ele
   usar os extras, o blur real dos apps pelo Blur my Shell.
2. Ideias que ainda não foram pedidas: imagem de fundo nas janelas (papel de parede já borrado); escolher a cor da sidebar separadamente;
   cor do texto apagado separada; tema de ícones combinando; gerar um `palette.conf` a partir do wallpaper.
3. Se o usuário quiser cores que não seguem o padrão "mesmo deslocamento", a saída é adicionar novas
   famílias em `familia()` / `REF` / `PADRAO` (e no JS da página).
