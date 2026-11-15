#!/usr/bin/env python3
"""Import a Logseq graph into Trilium using trilium-py."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from trilium_py.client import ETAPI

DEFAULT_IGNORED_FOLDERS = ("assets", "logseq", ".git")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the Markdown pages and journals of a Logseq graph into Trilium."
    )
    parser.add_argument(
        "graph",
        type=Path,
        help="Path to the Logseq graph directory (the directory containing pages/, journals/, etc.).",
    )
    parser.add_argument(
        "--server-url",
        default=os.getenv("TRILIUM_SERVER_URL", "http://localhost:8080"),
        help="Trilium ETAPI base URL (default: TRILIUM_SERVER_URL or %(default)s).",
    )
    parser.add_argument(
        "--parent-note-id",
        default="root",
        help="Trilium note ID to import under (default: root).",
    )
    parser.add_argument(
        "--ignore-folder",
        action="append",
        dest="ignored_folders",
        help=(
            "Folder name to skip. Can be repeated; default: assets, logseq, .git. "
            "When provided, these replace the defaults."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List Markdown files without connecting to Trilium or importing them.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt before importing.",
    )
    return parser.parse_args()


def markdown_files(graph: Path, ignored_folders: tuple[str, ...]) -> list[Path]:
    """Return Markdown files while pruning ignored directories."""
    files: list[Path] = []
    for current_dir, directories, filenames in os.walk(graph):
        directories[:] = sorted(
            name for name in directories if name not in ignored_folders and not name.startswith(".")
        )
        files.extend(
            Path(current_dir) / name
            for name in filenames
            if name.lower().endswith(".md")
        )
    return sorted(files)


def main() -> int:
    args = parse_args()
    graph = args.graph.expanduser().resolve()
    if not graph.is_dir():
        print(f"Fehler: Graph-Verzeichnis nicht gefunden: {graph}", file=sys.stderr)
        return 2

    ignored_folders = tuple(args.ignored_folders or DEFAULT_IGNORED_FOLDERS)
    files = markdown_files(graph, ignored_folders)
    print(f"Logseq-Graph: {graph}")
    print(f"Markdown-Dateien: {len(files)}")
    print(f"Ignorierte Ordnernamen: {', '.join(ignored_folders) or '(keine)'}")

    if args.dry_run:
        for path in files:
            print(path.relative_to(graph))
        return 0

    token = os.getenv("TRILIUM_ETAPI_TOKEN")
    if not token:
        print(
            "Fehler: Bitte das ETAPI-Token in TRILIUM_ETAPI_TOKEN setzen.",
            file=sys.stderr,
        )
        return 2
    if not files:
        print("Keine Markdown-Dateien zum Import gefunden.")
        return 0

    if not args.yes:
        answer = input("Import nach Trilium starten? [j/N] ").strip().lower()
        if answer not in {"j", "ja", "y", "yes"}:
            print("Import abgebrochen.")
            return 0

    try:
        client = ETAPI(args.server_url.rstrip("/"), token)
        client.upload_md_folder(
            parentNoteId=args.parent_note_id,
            mdFolder=str(graph),
            ignoreFolder=list(ignored_folders),
        )
    except Exception as exc:  # noqa: BLE001 - display client/API errors to CLI users
        print(f"Import fehlgeschlagen: {exc}", file=sys.stderr)
        return 1

    print("Import abgeschlossen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
