# Logseq → TriliumNext

Ein kleines Python-Gerüst, um Markdown-Dateien eines Logseq-Graphen mit [`trilium-py`](https://github.com/Nriver/trilium-py) in TriliumNext zu importieren. Der Import verwendet `ETAPI.upload_md_folder`; die Bibliothek erhält damit die Ordnerstruktur und unterstützt Markdown-Dateien mit referenzierten Bildern.

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

Zuerst optional prüfen, welche Markdown-Dateien erkannt werden, ohne eine Verbindung zu Trilium aufzubauen:

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

Das Skript zählt und listet bei `--dry-run` ausschließlich Markdown-Dateien; der eigentliche Upload und die Verarbeitung von Bild-Links erfolgen durch `trilium-py`. Vor einem produktiven Lauf empfiehlt sich ein Trilium-Backup. Wiederholte Importe können Duplikate erzeugen; dieses Gerüst führt noch keine Abgleich-/Aktualisierungslogik durch.

## Nächste Ausbauschritte

- Logseq-spezifische `[[Seitenlinks]]` und Block-Referenzen umwandeln
- Tags, Properties und Journaldaten gezielt übernehmen
- Import-Mapping für idempotente Wiederholung speichern
- Fortschrittsanzeige und detailliertes Importprotokoll ergänzen
