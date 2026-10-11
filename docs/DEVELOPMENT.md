# Developer guide

The README is the user guide; this file is for whoever changes the code. Read it before
touching the parser, the color math or the editor.

## Layout

| Path | What it is |
|---|---|
| `generate-theme.py` | the generator (standard library only) |
| `install.sh` | generate + move to `/usr/share/themes` + optionally activate (`--apply`) |
| `palette.conf` | default palette; reproduces ZorinBlue-Dark exactly |
| `examples/*.conf` | ready-made palettes |
| `editor/index.html` | visual editor, a single HTML file with no build step (also published with GitHub Pages) |
| `icons/example-*.svg` | custom button icon templates |
| `tools/` | maintenance and test scripts |
| `docs/images/` | README screenshots |

## Anatomy of the Zorin theme

Source: `/usr/share/themes/ZorinBlue-Dark` (from the Zorin OS package; **never modify it**).
`OWN_THEME_SOURCE` can point somewhere else.

| Folder | Controls | Color format |
|---|---|---|
| `gtk-3.0/gtk.css` (2384 lines) | GTK3 apps | compiled SASS, colors written inline (84 distinct). The `@define-color` at the end are only exports |
| `gtk-4.0/gtk.css` (2773 lines) | GTK4/libadwaita apps | libadwaita-style `@define-color` on lines 2–105 (accent_bg_color, window_bg_color…) plus inline colors |
| `gnome-shell/gnome-shell.css` | top bar, overview, menus, Quick Settings | inline colors, many `rgba(189,230,251,α)` |
| `gnome-shell/assets/*.svg` | toggles, checkboxes, calendar | inline `fill="#…"` |
| `gtk-2.0/gtkrc` | GTK2 apps | one `gtk_color_scheme = "fg_color:#…\n…"` line |
| `xfwm4/` | XFCE window borders | PNG/XPM; **useless on GNOME, dropped from generated themes** |
| `index.theme` | metadata | name, IconTheme, ButtonLayout |

Facts:
- `gtk.css` and `gtk-dark.css` are identical (for both GTK versions).
- There is no SCSS source. The strategy is to rewrite the compiled CSS.
- `gtk-4.0/.libadwaita` is an empty marker. **Zorin's libadwaita is patched**
  (`libadwaita-1-0 1.5.0-1ubuntu2+zorin1`) to load `/usr/share/themes/%s/gtk-4.0` from the active GTK
  theme; the binary also contains the string `.themes`. Installing to `/usr/share/themes` is the
  reliable route, which is why `install.sh` exists.
- GNOME Shell loads the theme through the **user-theme** extension
  (`org.gnome.shell.extensions.user-theme name`), which reads `<theme>/gnome-shell/gnome-shell.css`.
  `gnome-shell-theme.gresource` is copied unchanged.
- The shell's `*-light.svg` files belong to light mode; the dark CSS doesn't use them. They are copied unchanged.
- `#add` in gtk-4.0 **is not a color**: it is part of the `colorswatch#add-color-button` selector.
  The generator's regex already ignores it.

### The key finding

Every Zorin variant (Blue, Green, Purple, Red, Orange, Yellow, Brown, Grey) is **the same theme
with the hue rotated**. Lightness stays the same and saturation changes (Grey = saturation 0).
Blue: hue 200°, Green 158°, Red 0°, Purple 267°. Official base colors (background / accent):
Blue `#222b30/#bde6fb`, Green `#202b27/#bbf1dd`, Purple `#28232d/#d8c4f1`, Red `#2e1f1f/#fdb4b4`,
Orange `#2e231f/#fcc8b4`, Yellow `#2c281d/#fce8ad`, Brown `#292523/#e5d3ca`, Grey `#2a2a2a/#ffffff`.
Error `#fb7c7c`, warning `#faa483` and success `#6ee1b6`/`#4cd9a4` **don't change** between variants.

Roles of the main colors (Blue-Dark):

| Color | Role |
|---|---|
| `#bde6fb` | accent **and** main text (same literal; told apart by context) |
| `#222b30` | window background, headerbar |
| `#161c1f` | content background (lists, entries, popovers) **and** dark text on the accent |
| `#2d3940` | normal button, sidebar, troughs, borders |
| `#35434a` | hovered button |
| `#2b343a` | borders |
| `#415159` | switch off, checkbox border |
| `#1e2428`, `#171c1f` | unfocused window (backdrop) |
| `#71848d`, `#6f8896`, `#69818d`, `#3f4b54` | dimmed / disabled / placeholder text |
| `#8097a3` | selection in an unfocused window |
| `rgba(26,33,37,.7)` | Shell top bar |

Stock Zorin uses the same hue for background and accent; own-theme **separates** them.

## How the generator works

1. Copies the source theme to `~/.themes/<name>` (without `xfwm4/`) and creates the
   `.generated-by-own-theme` marker. The generator and `install.sh` only overwrite/delete folders
   that carry this marker (the legacy `.gerado-por-zorin-tema` marker is accepted too).
   **Don't rename the marker** without handling already generated themes.
2. For every color found (3- or 6-digit hex, `rgb()`/`rgba()`), `family(rgb, context)` decides the
   **family** by looking at the **original** color:
   - hue 188–208° and S ≥ 5%: a Zorin-derived color
     - S ≥ 30% → `accent`, or `text` if the context is text
     - S < 30% and L ≤ 20% in a text/mark context → `on_accent` (text on the accent)
     - otherwise → `background`
   - L ≥ 55% and S ≥ 50%: hue ≥350° or ≤8° → `error`; 14–20° → `warning`; 154–160° → `success`
   - everything else → `fixed` (unchanged)
3. **Context**: the CSS is walked declaration by declaration (comments are protected first).
   - `color`, `caret-color`, `-gtk-secondary-caret-color` → `text`, unless the selector contains `link`.
   - `@define-color X`: with `accent` + `fg`, or `selected_fg` → `mark`; with `fg`/`text`/`title` → `text`; otherwise → other.
   - The GNOME named palette (`blue_1`…`dark_5`) is skipped.
   - gtkrc: `*fg_color`/`*text_color` keys → text; `selected_fg_color` → mark.
   - The `toggle-on`, `checkbox`, `checkbox-focused` SVGs → `mark` context (the dark part is the "dot" on the accent).
4. **Transformation** (`transform`): each family has a reference color (`REF`) and a chosen color.
   - hue: `h + (h_chosen − h_ref)`
   - saturation: `s × s_chosen / s_ref`, capped at 1
   - lightness: piecewise map `0→0`, `L_ref→L_chosen`, `1→1`
   - the `rgba` alpha is preserved.
5. `text_on_accent = auto` → if the accent's luminance is > 0.3, use `#161c1f` transformed by the
   background family; otherwise `#ffffff`.
6. `radius`: multiplies px values of `border*-radius` properties below 99px (pills stay the same).
7. `index.theme`: replaces the name and keeps `IconTheme=ZorinBlue-Dark`.

### Tests you must keep passing

- **Byte-for-byte regression.** With the default palette, the output equals the original; only
  `index.theme` differs. Use a test name so you don't shadow an installed theme:

  ```sh
  printf 'name = OwnTest-Dark\n' > /tmp/t.conf
  python3 generate-theme.py /tmp/t.conf && diff -rq /usr/share/themes/ZorinBlue-Dark ~/.themes/OwnTest-Dark
  rm -rf ~/.themes/OwnTest-Dark
  ```

  Expected differences: `index.theme`, `xfwm4` and the marker.
- `tools/compare-variants.py`: median 0 and p95 of 2–5 (RGB distance) against the official themes
  on the files that align. The high values come from token misalignment, not errors.

> Never generate into `~/.themes/<name>` when a theme with the same name is installed in
> `/usr/share/themes`: `~/.themes` takes precedence and would hide it.

## Extras: glass and window buttons

Options in `palette.conf` (all in `DEFAULTS`; with the default value **nothing is appended**, so the
byte-for-byte regression still holds). The `Extras` class **appends rules at the end** of
`gtk-3.0/gtk(-dark).css` and `gtk-4.0/gtk(-dark).css` and writes `own-*.svg` files into `assets/`.
gnome-shell.css is not touched.

- **Glass**: `window_opacity`, `content_opacity` (0.3–1).
  - GTK4: redefines `@define-color` at the end of the file (the last one wins). window/backdrop with
    alpha, `headerbar_*` transparent (it sits on the window background), sidebar with alpha `a³`
    (`sidebar_opacity`, because it adds up on top of the window), opaque `dialog_bg_color`,
    view/card with the content alpha.
  - GTK3: rules for `.background`, transparent headerbar/toolbar/searchbar, `.view`/`iconview`/`list`.
    With glass, `.background.csd` gets a radius on all 4 corners (the transparent bar would leave the top ones square).
  - **The blur is not part of the theme** (GTK/Shell CSS has no backdrop-filter). It comes from
    **Blur my Shell** (tested with v74). `blur = yes` + `install.sh --apply` → `generate-theme.py --blur`
    sets `...blur-my-shell.applications` via `gsettings --schemadir`: blur, enable-all, opacity 255
    (the extension's own opacity would make text translucent), dynamic-opacity false,
    sigma = `blur_strength`, corner-radius = 15×radius. `blur = no` changes nothing.
    Dry run: `GSETTINGS_BACKEND=memory python3 generate-theme.py --blur my.conf`.
  - **Corners**: on GNOME 46 `Shell.BlurEffect` has no `corner-radius`, so the extension's
    **dynamic** app blur is always a square rectangle. `blur_mode = static` (default) turns on
    `static-blur` and creates the `pipeline_own_theme` pipeline (native_static_gaussian_blur + corner
    with 15×radius) via `PIPELINE_SCRIPT`, which runs on `/usr/bin/python3` with gi and keeps the other
    pipelines (`av` format). Static only blurs the wallpaper.
  - Top bar/menus: the extension already blurs them and replaces their background
    (`override-background true`), so there is no top bar opacity option.
- **Buttons**: `buttons` (zorin|circles|plain), `glyphs` (lines|arrows|mac), `symbols` (always|hover|never),
  `button_size` (16–26; GTK3 won't make the button smaller than the 16px icon), `button_<b>`
  (auto = error/success/warning), `icon_<b>` for close/maximize/minimize/restore (path relative to the
  conf folder; becomes the whole button in any style; restore falls back to maximize).
  - GTK4: draws on the `windowcontrols > button.X > image` node (background + background-image) and hides
    the symbol with `-gtk-icon-filter: opacity(0)` (don't use `color: transparent`: Zorin's circle uses
    currentColor). Maximized: `window.maximized …`.
  - GTK3: draws on `button.titlebutton.X` itself and hides the `image` with `color: transparent`.
    Maximized: `.maximized …`.
  - States: '', :hover, :active, :backdrop, :backdrop:hover (`button_states`).

## The editor (`editor/index.html`)

- A single HTML file with no build. Its JS reimplements `transform`, `map_l`, `luminance`,
  `GLYPHS`, `glyph_svg`, `button_states` and `sidebar_opacity` from Python.
  **If you change the math in Python, change the JS too** and check parity (run both on the same
  inputs with node; the last check covered 911 cases with 0 differences).
- `const SOURCE = [...]` holds the source colors `[hex, family, uses]`. It is generated by
  `tools/export-colors.py`; don't edit it by hand.
- The preview uses the exact original color of each widget (table above) passed through the transformation.
- Hovering a control outlines the parts of the preview it affects (`data-r` attributes).
- State is saved in `localStorage`; the page emits `palette.conf` text and can import a pasted one.
- Ready-made themes come in groups. The "complete" ones also set radius/glass/buttons (`EXTRAS_KEYS`);
  the others only change colors. **Harmony** (`st.harmony`, page-only) recomputes text (almost white
  in the accent's hue), error/warning/success (hues 0/18/157 at the accent's intensity) and raises the
  accent's lightness until it reaches 3:1 contrast against the background.
- The page is dark on purpose (it edits a dark theme).
- GitHub Pages publishes the `editor/` folder (see `.github/workflows/pages.yml`).

## Visual tests

- GTK4: `gtk4-broadwayd --address 127.0.0.1 :5` (without `--address` it listens on all interfaces).
  With no browser connected, broadway **never paints frames**: `WidgetPaintable` comes out empty and
  transitions never finish. That's why `tools/render-gtk4.py` uses `snapshot_child()` and disables animations.
- The README screenshots were made with `tools/render-gtk3.py` / `tools/render-gtk4.py` on themes
  generated from `examples/`, composed with ImageMagick, plus a headless Chromium capture of the editor.

## Environment pitfalls

- A `gsettings` that comes first in `PATH` (e.g. linuxbrew's) may use the **keyfile** backend: it
  writes to a file GNOME never reads. The scripts use `/usr/bin/gsettings`. To check the real state:
  `dconf dump /org/gnome/shell/extensions/blur-my-shell/`.
- Some `python3` builds (e.g. linuxbrew) lack the `gi` module. For GTK use `/usr/bin/python3`.
  The generator only uses the standard library, so it runs on any Python 3.
- In `palette.conf`, `#` is a color **and** a comment. The parser takes only the first word after
  `=`, so `background = #222b30  # comment` works. Lines starting with `#` are comments.
- `install.sh` uses `sudo` only when the destination isn't writable. `OWN_THEME_DEST=/tmp/x ./install.sh`
  tests it without sudo.
- `~/.themes/<name>` takes precedence over `/usr/share/themes/<name>`. That's why `install.sh`
  **moves** (not copies); otherwise a stale copy in `~/.themes` would hide the system one.
- Careful with `pkill -f <pattern>`: it matches the shell running the command itself.

## Ideas

- A window background image (an already blurred wallpaper); a separate sidebar color; a separate
  dimmed-text color; a matching icon theme; generating a `palette.conf` from the wallpaper.
- For colors that don't follow the "same shift" pattern, add new families to `family()` / `REF` /
  `DEFAULTS` (and to the editor's JS).
