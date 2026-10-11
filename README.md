# own-theme

Seu próprio tema escuro para o Zorin OS, gerado a partir de poucas cores.
Você escolhe fundo, destaque, texto e cores de status, e o projeto recalcula
as ~140 cores do tema ZorinBlue-Dark para GTK3, GTK4/libadwaita, GNOME Shell e GTK2.

```
own-theme/
├── palette.conf          ← suas cores (o único arquivo que você precisa editar)
├── gerar-tema.py         ← gera o tema em ~/.themes/<nome>
├── instalar.sh           ← gera + move para /usr/share/themes (+ ativa com --aplicar)
├── pagina/estudio.html   ← editor visual (cores, vidro, botões), com prévia
├── icones/               ← seus ícones de botão (tem modelos exemplo-*.svg)
└── ferramentas/          ← scripts de manutenção e teste
```

## 1. Escolher as cores (editor visual)

O editor é um único arquivo HTML. Abra no navegador:

```sh
xdg-open pagina/estudio.html
```

Também está publicado em https://claude.ai/artifact/1SudfjPBKYWFqHy62aCgxA (privado, só a sua conta abre).

No editor:
- clique num tema pronto: variantes do Zorin, paletas famosas (Catppuccin, Dracula, Tokyo Night, Nord,
  Gruvbox…), combinações, ou um tema **completo**, que também traz vidro, cantos e botões;
- ou escolha cada cor. Com **Ajustar as outras cores sozinho** ligado, mudar o fundo ou o destaque
  recalcula texto, erro, aviso e sucesso para combinarem; desligue para controlar cada cor à mão;
- passe o mouse sobre uma cor para ver o que ela pinta na prévia;
- confira os selos de contraste (verde = legível);
- clique em **Copiar palette.conf** e cole por cima do `palette.conf` desta pasta.

Funciona offline. Sem internet, só as fontes da página mudam.

Você também pode editar o `palette.conf` direto à mão:

| Opção | O que muda |
|---|---|
| `nome` | nome da pasta do tema (ex: `ZorinCustom-Dark`) |
| `fundo` | fundo da janela; os outros tons escuros derivam dele |
| `destaque` | seleção, botão principal, foco, switches, sliders |
| `texto` | texto principal |
| `texto_sobre_destaque` | texto em cima do destaque; `auto` escolhe escuro ou branco |
| `erro`, `aviso`, `sucesso` | cores de status |
| `raio` | multiplicador dos cantos arredondados (`0` = quadrado, `1` = original) |
| `opacidade_janela` | `0.3` a `1`; abaixo de 1 o fundo das janelas (e sidebar/barra de título) fica translúcido |
| `opacidade_conteudo` | `0.3` a `1`; o mesmo para listas, campos e cartões |
| `blur` | `sim` faz o `instalar.sh --aplicar` ligar o blur de apps na extensão Blur my Shell |
| `blur_forca` | `0` a `100`; quanto o Blur my Shell borra (padrão 30) |
| `blur_modo` | `estatico` (padrão): borra o papel de parede, cantos arredondados; `dinamico`: borra tudo atrás, mas no GNOME 46 com cantos retos |
| `botoes` | `zorin` (original), `circulos` (bolinhas coloridas) ou `simples` (só o símbolo) |
| `glifos` | desenho do símbolo: `linhas`, `setas` ou `mac` |
| `simbolos` | no estilo círculos: mostrar o símbolo `sempre`, no `hover` ou `nunca` |
| `botao_tamanho` | `16` a `26` (px) |
| `botao_fechar`, `botao_maximizar`, `botao_minimizar` | cor de cada botão; `auto` = erro, sucesso e aviso |
| `icone_fechar`, `icone_maximizar`, `icone_minimizar`, `icone_restaurar` | caminho de um `.svg`/`.png` seu (relativo a esta pasta, sem espaços) ou `nenhum`; o arquivo vira o botão inteiro |

Com os valores padrão dessas opções extras nada muda no tema.

## Vidro (fundo translúcido com blur)

O CSS do GTK e do GNOME Shell não sabe borrar o que está atrás da janela. Por isso o
efeito tem duas partes:
1. o **tema** deixa os fundos translúcidos (`opacidade_janela`, `opacidade_conteudo`);
   texto, botões e menus continuam opacos;
2. a extensão **Blur my Shell** borra o que aparece atrás. Com `blur = sim`, o
   `./instalar.sh --aplicar` liga *Aplicativos → Borrar* para todos os apps, deixa a
   janela em si opaca (a transparência vem do tema) e usa `blur_forca`.
   Para desligar: preferências da extensão → Aplicativos.

No GNOME 46 (Zorin 17) o blur **dinâmico** da extensão não arredonda os cantos: aparece um
retângulo atrás da janela. Por isso o padrão é o **estático**, em que o instalador cria um pipeline
próprio na extensão (`pipeline_own_theme`: blur + cantos com o mesmo raio das janelas).

Sem o blur, a área de trabalho aparece nítida atrás das janelas. O painel e os menus
do Shell já são borrados pela extensão (opção *Painel* e *Pop-ups* dela).

## Botões da janela e ícones próprios

No editor, em **Botões da janela**, escolha o estilo, as cores e o tamanho, ou carregue
um SVG/PNG para cada botão. Copie esses arquivos para `own-theme/icones/` com o mesmo
nome que aparece no `palette.conf`. As dicas completas (formato, onde baixar ícones,
como criar um tema de ícones que o sistema reconheça) estão na seção
**Ícones dos botões** do editor. O essencial:

- SVG quadrado (`viewBox="0 0 16 16"`) ou PNG 64×64+ transparente; o arquivo é o botão inteiro;
- sem texto/fontes/imagens embutidas (Inkscape: *Objeto para caminho* e *Contorno para caminho*);
- fontes de ícones: apps *Icon Library* e *Icon Preview* (Flathub), Phosphor, Tabler, Lucide,
  Material Symbols; botões de temas do gnome-look.org (WhiteSur, Orchis, Colloid…);
- alternativa sem tema GTK: um tema de ícones em `~/.local/share/icons/` com
  `window-close-symbolic.svg`, `window-maximize-symbolic.svg`, `window-minimize-symbolic.svg`
  e `window-restore-symbolic.svg` (vale só para o estilo `zorin`).

Os botões funcionam em apps GTK3 e GTK4/libadwaita. Apps que desenham a própria barra
(Chrome, VS Code e outros Electron, Qt) não usam o tema.

## 2. Gerar e instalar o tema

**Jeito recomendado: gera, instala no sistema e ativa:**

```sh
./instalar.sh --aplicar
```

O `instalar.sh`:
1. roda o `gerar-tema.py`, que cria o tema em `~/.themes/<nome>`;
2. **move** a pasta para `/usr/share/themes/<nome>` (pede sua senha de administrador);
3. com `--aplicar`, ativa o tema no GTK e no GNOME Shell e liga o modo escuro.

Sem `--aplicar`, ele só instala; depois você escolhe o tema no Zorin Appearance.
Por segurança, ele se recusa a sobrescrever qualquer tema que não tenha sido criado por este projeto.

**Só gerar, sem instalar no sistema** (o tema fica em `~/.themes`, que só vale para o seu usuário):

```sh
python3 gerar-tema.py            # usa palette.conf
python3 gerar-tema.py outro.conf # usa outra paleta
python3 gerar-tema.py --aplicar  # gera e ativa a partir de ~/.themes
```

Depois de aplicar, o painel muda na hora. Feche e reabra os apps para ver o resto.

## Voltar ao tema padrão do Zorin

```sh
gsettings set org.gnome.desktop.interface gtk-theme ZorinBlue-Light
gsettings set org.gnome.shell.extensions.user-theme name ZorinBlue-Light
```

Para apagar um tema instalado: `sudo rm -rf /usr/share/themes/<nome>`.

## Ferramentas

| Script | Para quê |
|---|---|
| `ferramentas/exportar-cores.py` | atualiza a lista de cores dentro do editor; rode depois de mudar a classificação no `gerar-tema.py` |
| `ferramentas/comparar-variantes.py` | valida a matemática contra os temas oficiais Green/Purple/Red/Orange |
| `ferramentas/renderizar-gtk3.py` | tira um "print" de uma janela GTK3 de teste com o tema, sem abrir nada na tela |
| `ferramentas/renderizar-gtk4.py` | o mesmo para uma janela libadwaita (GTK4), via broadway; aceita os estados `hover`, `backdrop`, `maximizada` |

Exemplo de print:

```sh
GDK_BACKEND=x11 GTK_THEME=ZorinCustom-Dark /usr/bin/python3 ferramentas/renderizar-gtk3.py teste.png

gtk4-broadwayd --address 127.0.0.1 :5 &
GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 GTK_THEME=ZorinCustom-Dark /usr/bin/python3 ferramentas/renderizar-gtk4.py teste4.png hover
```

## Como funciona (resumo)

Cada cor do tema original pertence a uma família (fundo, destaque, texto, texto
sobre destaque, erro, aviso, sucesso) ou é fixa (pretos, brancos, sombras).
Quando você troca a cor-base de uma família, todas as cores dela recebem o mesmo
deslocamento de tom, saturação proporcional e luminosidade remapeada. Com o
`palette.conf` padrão, o resultado é idêntico byte a byte ao ZorinBlue-Dark.
Os detalhes estão no `CLAUDE.md`.
