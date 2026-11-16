# Logseq → TriliumNext

Ein kleines Python-Gerüst, um Markdown-Dateien eines Logseq-Graphen mit [`trilium-py`](https://github.com/Nriver/trilium-py) in TriliumNext zu importieren. Zusätzlich werden fehlende Ziele von Logseq-Seitenlinks (`[[Seite]]`) und Tags (`#Tag`) als Trilium-Notizen angelegt. Schrägstriche in einem Link erzeugen eine entsprechende Notiz-Hierarchie, zum Beispiel `[[Projekt/Planung]]` → `Projekt` → `Planung`.

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

Zuerst optional prüfen, welche Markdown-Dateien erkannt und welche verlinkten Notizen ergänzt werden, ohne eine Verbindung zu Trilium aufzubauen:

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

Standardmäßig werden Verzeichnisse namens `assets`, `logseq` und `.git` an die Bibliothek zum Ignorieren übergeben. Eigene Ausschlussliste:

```bash
python main.py /pfad/zum/logseq-graph \\
  --ignore-folder assets --ignore-folder logseq --ignore-folder .git --ignore-folder private
```

Das Skript zählt und listet bei `--dry-run` Markdown-Dateien sowie Links, für die keine Markdown-Seite im Graphen existiert. Beim Import werden zunächst Markdown-Dateien hochgeladen; anschließend werden fehlende Seitenziele und Tags erstellt. Vor einem produktiven Lauf empfiehlt sich ein Backup der Trilium-Datenbank.

## Nächste Ausbauschritte

- Block-Referenzen umwandeln
- Tags, Properties und Journaldaten gezielt übernehmen
- Import-Mapping für idempotente Wiederholung speichern
- Fortschrittsanzeige und detailliertes Importprotokoll ergänzen
