# Logseq → TriliumNext

Ein kleines Python-Gerüst, um Markdown-Dateien eines Logseq-Graphen mit [`trilium-py`](https://github.com/Nriver/trilium-py) in TriliumNext zu importieren. Zusätzlich werden fehlende Ziele von Logseq-Links und Tags ergänzt. Lokal verlinkte Dateien in Wikilinks (z. B. Excalidraw-Whiteboards) werden als Datei-Notizen importiert.

## Voraussetzungen

- Python 3.9 oder neuer
- TriliumNext mit aktiviertem ETAPI und einem ETAPI-Token
- Zugriff auf den lokalen Logseq-Graphen

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

Token und optional Server-URL als Umgebungsvariablen setzen (Token nicht im Skript speichern):

```bash
export TRILIUM_SERVER_URL="http://localhost:8080"
export TRILIUM_ETAPI_TOKEN="<dein-etapi-token>"
```

## Verwendung

Zuerst optional prüfen, welche Markdown-Dateien erkannt, welche lokalen Dateien importiert und welche verlinkten Notizen ergänzt werden, ohne eine Verbindung zu Trilium aufzubauen:

```bash
python main.py /pfad/zum/logseq-graph --dry-run
```

Import unter die Trilium-Wurzel (`root`):

```bash
python main.py /pfad/zum/logseq-graph
```

Für einen anderen Zielknoten dessen Note-ID angeben. Mit `--yes` wird die Sicherheitsabfrage übersprungen:

```bash
python main.py /pfad/zum/logseq-graph --parent-note-id ABC123 --yes
```

Standardmäßig werden Verzeichnisse namens `assets`, `logseq` und `.git` vom Markdown-Upload ausgeschlossen. Verlinkte Anhänge unter `assets/` werden vom Markdown-Importer übernommen, wenn sie in Markdown als Bild oder Datei verlinkt sind. Per Logseq-Wikilink referenzierte lokale Dateien, beispielsweise Zeichnungen unter `draws/`, werden zusätzlich als Datei-Notizen importiert. Codeblöcke werden bei der Erkennung von Links und Tags ignoriert.

Eigene Ausschlussliste:

```bash
python main.py /pfad/zum/logseq-graph \\
  --ignore-folder assets --ignore-folder logseq --ignore-folder .git --ignore-folder private
```

Logseq-Seitennamen, in denen Schrägstriche als `___` kodiert sind, werden beim Abgleich mit Wikilinks dekodiert, damit vorhandene Seiten nicht fälschlich als fehlend erkannt werden.

Tests ausführen:

```bash
python -m unittest discover -s tests
```

## Nächste Ausbauschritte

- Block-Referenzen umwandeln
- Tags, Properties und Journaldaten gezielt übernehmen
- Import-Mapping für idempotente Wiederholung speichern
- Fortschrittsanzeige und detailliertes Importprotokoll ergänzen
