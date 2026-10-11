#!/usr/bin/env bash
# Gera o tema a partir do palette.conf e move para /usr/share/themes,
# onde o sistema todo (inclusive apps GTK4/libadwaita) enxerga o tema.
#
# Uso:
#   ./instalar.sh                    # gera + move para /usr/share/themes
#   ./instalar.sh --aplicar          # gera + move + ativa o tema
#   ./instalar.sh outro.conf         # usa outro arquivo de paleta
#
# Pede a senha de administrador (sudo) para escrever em /usr/share/themes.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SISTEMA="${OWN_THEME_DESTINO:-/usr/share/themes}"   # destino; a variável existe para testes
MARCA=.gerado-por-zorin-tema   # arquivo que o gerar-tema.py coloca em todo tema que ele cria
# o gsettings do linuxbrew (primeiro no PATH) grava num arquivo que o GNOME não lê;
# o do sistema grava no dconf
GSETTINGS=gsettings
[ -x /usr/bin/gsettings ] && GSETTINGS=/usr/bin/gsettings

APLICAR=0
CONF="$DIR/palette.conf"
for arg in "$@"; do
    case "$arg" in
        --aplicar) APLICAR=1 ;;
        -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "Opção desconhecida: $arg (use --aplicar)" >&2; exit 1 ;;
        *) CONF="$arg" ;;
    esac
done
[ -f "$CONF" ] || { echo "Erro: $CONF não encontrado" >&2; exit 1; }

# mesmo critério do gerar-tema.py: primeira palavra depois de "nome ="
NOME="$(sed -nE 's/^[[:space:]]*nome[[:space:]]*=[[:space:]]*([^[:space:]]+).*/\1/p' "$CONF" | tail -1)"
NOME="${NOME:-ZorinCustom-Dark}"
GERADO="$HOME/.themes/$NOME"
DESTINO="$SISTEMA/$NOME"

# nunca sobrescrever temas que não foram criados por este projeto (Zorin*, Adwaita…)
if [ -e "$DESTINO" ] && [ ! -e "$DESTINO/$MARCA" ]; then
    echo "Erro: $DESTINO já existe e não foi criado por este projeto." >&2
    echo "Troque o \"nome\" no $(basename "$CONF")." >&2
    exit 1
fi

echo "==> Gerando o tema \"$NOME\""
python3 "$DIR/gerar-tema.py" "$CONF" | grep -v '^Para ativar'

SUDO=sudo
[ -w "$SISTEMA" ] && SUDO=   # destino gravável (testes): sem sudo
echo "==> Movendo $GERADO -> $DESTINO${SUDO:+ (pode pedir sua senha)}"
$SUDO rm -rf --one-file-system "$DESTINO"
$SUDO mv "$GERADO" "$DESTINO"
[ -n "$SUDO" ] && sudo chown -R root:root "$DESTINO"
$SUDO chmod -R u=rwX,go=rX "$DESTINO"
echo "    Instalado em $DESTINO"

if [ "$APLICAR" = 1 ]; then
    echo "==> Ativando"
    $GSETTINGS set org.gnome.desktop.interface color-scheme prefer-dark
    # zera antes de setar para o GNOME recarregar mesmo se o nome não mudou
    $GSETTINGS set org.gnome.desktop.interface gtk-theme 'Adwaita'
    $GSETTINGS set org.gnome.desktop.interface gtk-theme "$NOME"
    if $GSETTINGS list-schemas | grep -qx org.gnome.shell.extensions.user-theme; then
        $GSETTINGS set org.gnome.shell.extensions.user-theme name ''
        $GSETTINGS set org.gnome.shell.extensions.user-theme name "$NOME"
    fi
    # blur = sim no palette.conf: liga o blur de apps no Blur my Shell
    python3 "$DIR/gerar-tema.py" --blur "$CONF"
    echo "    Pronto. O painel muda na hora; feche e reabra os apps para ver o resto."
else
    echo "Para ativar: ./instalar.sh --aplicar  (ou escolha \"$NOME\" no Ajustes/Zorin Appearance)"
fi
