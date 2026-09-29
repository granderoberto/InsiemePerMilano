#!/usr/bin/env bash
# Rigenera docs/modello_er.{svg,pdf,png} dai dati in gen.py (E = entità, R = associazioni)
# Requisiti: python3, node, npm i elkjs, pip install cairosvg
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules/elkjs ] || npm i elkjs --silent
python3 build.py      # grafo ELK + metadati
node lay.js           # layout 1: ordine delle porte
python3 pass2.py      # fissa le porte sui lati dei rettangoli
node lay.js           # layout 2: definitivo
python3 render.py     # SVG stile Chen con lecca-lecca
python3 -c "import cairosvg;cairosvg.svg2pdf(url='er_ortho.svg',write_to='../../docs/modello_er.pdf');cairosvg.svg2png(url='er_ortho.svg',write_to='../../docs/modello_er.png',scale=1.3)"
cp er_ortho.svg ../../docs/modello_er.svg
rm -f in.json out.json meta.json er_ortho.svg
echo "OK: docs/modello_er.{svg,pdf,png}"
