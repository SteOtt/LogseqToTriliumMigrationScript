#!/usr/bin/env python3
"""Import a Logseq graph into Trilium using trilium-py."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from trilium_py.client import ETAPI

DEFAULT_IGNORED_FOLDERS = ("assets", "logseq", ".git")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
TAG_RE = re.compile(r"(?<![\w#])#(?!\+)([^\s\[\]{}()<>,;.!?]+)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)[^`\n]*?\1")
ATX_HEADING_RE = re.compile(r"^( {0,3})(#{1,6})(?=[ \t]|$)")
SETEXT_HEADING_RE = re.compile(r"^(?P<title>.+?)\n(?P<underline>=+|-+)[ \t]*$")


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
        help="List Markdown files and missing linked pages without connecting to Trilium.",
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


def shift_heading_level(level: int) -> int:
    """Map Markdown heading levels to Trilium-compatible levels starting at H2."""
    return min(level + 1, 6)


def shift_markdown_headings(text: str) -> str:
    """Shift Markdown headings down one level because Trilium does not support H1."""
    shifted_lines: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    lines = text.splitlines(keepends=True)
    index = 0

    while index < len(lines):
        line = lines[index]
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_char is None:
                fence_char, fence_length = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char, fence_length = None, 0
            shifted_lines.append(line)
            index += 1
            continue

        if fence_char is None:
            heading = ATX_HEADING_RE.match(line)
            if heading:
                level = len(heading.group(2))
                replacement_level = shift_heading_level(level)
                remainder = line[heading.end():]
                shifted_lines.append(f"{heading.group(1)}{'#' * replacement_level}{remainder}")
                index += 1
                continue

            setext_match = SETEXT_HEADING_RE.match("".join(lines[index : index + 2]))
            if setext_match:
                title = setext_match.group("title").rstrip()
                underline = setext_match.group("underline")
                level = 1 if underline.startswith("=") else 2
                replacement_level = shift_heading_level(level)
                shifted_lines.append(f"{'#' * replacement_level} {title.rstrip()}\n")
                index += 2
                continue

        shifted_lines.append(line)
        index += 1

    return "".join(shifted_lines)


def stage_markdown_files(files: list[Path], graph: Path, destination: Path) -> None:
    """Copy Markdown files into an import tree, decoding Logseq's `___` page hierarchy."""
    destinations: set[Path] = set()
    for source in files:
        relative = source.relative_to(graph)
        # Logseq encodes slashes in page titles as three underscores. Turn those
        # into directories so Trilium imports the page as a note hierarchy.
        title_parts = tuple(part for part in relative.stem.replace("___", "/").split("/") if part)
        if not title_parts:
            title_parts = (relative.stem,)
        staged_path = destination / relative.parent / Path(*title_parts).with_suffix(relative.suffix)
        if staged_path in destinations:
            raise ValueError(f"Multiple Markdown files map to the same import path: {staged_path}")
        destinations.add(staged_path)
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, staged_path)
        content = staged_path.read_text(encoding="utf-8")
        staged_path.write_text(shift_markdown_headings(content), encoding="utf-8")


def without_code(text: str) -> str:
    """Remove fenced and inline code so examples are not interpreted as links or tags."""
    kept_lines: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    for line in text.splitlines():
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_char is None:
                fence_char, fence_length = marker[0], len(marker)
            elif marker[0] == fence_char and len(marker) >= fence_length:
                fence_char, fence_length = None, 0
            continue
        if fence_char is None:
            kept_lines.append(line)
    return INLINE_CODE_RE.sub(" ", "\n".join(kept_lines))


def link_targets(files: list[Path]) -> set[str]:
    """Extract Logseq page links and tags from Markdown outside code blocks."""
    targets: set[str] = set()
    for path in files:
        text = without_code(path.read_text(encoding="utf-8", errors="replace"))
        for match in WIKILINK_RE.finditer(text):
            # Logseq supports [[page|display text]]; only the page name is a target.
            target = match.group(1).split("|", 1)[0].strip()
            if target:
                targets.add(target)
        targets.update(match.group(1).strip() for match in TAG_RE.finditer(text) if match.group(1).strip())
    return targets


def normalize_target(target: str) -> str:
    """Normalize a Logseq target, including its `___` encoding for page-title slashes."""
    decoded = target.replace("\\", "/").replace("___", "/")
    return "/".join(part.strip().casefold() for part in decoded.split("/") if part.strip())


def page_keys(files: list[Path], graph: Path) -> set[str]:
    """Build normalized names for pages already represented by Markdown files."""
    keys: set[str] = set()
    for path in files:
        relative = path.relative_to(graph).with_suffix("")
        variants = {relative.as_posix(), path.stem}
        parts = relative.parts
        if len(parts) > 1 and parts[0].casefold() in {"pages", "journals"}:
            variants.add(Path(*parts[1:]).as_posix())
        keys.update(normalize_target(value) for value in variants)
    return keys


def local_file_targets(targets: set[str], graph: Path) -> dict[str, Path]:
    """Return wikilink targets that point to files inside the graph, not pages."""
    files: dict[str, Path] = {}
    graph = graph.resolve()
    for target in targets:
        candidate = (graph / target.replace("\\", "/")).resolve()
        try:
            candidate.relative_to(graph)
        except ValueError:
            continue
        if candidate.is_file():
            files[target] = candidate
    return files


def missing_link_targets(targets: set[str], files: list[Path], graph: Path) -> list[str]:
    known_pages = page_keys(files, graph)
    local_files = local_file_targets(targets, graph)
    missing: dict[str, str] = {}
    for target in targets:
        if target in local_files:
            continue
        normalized = normalize_target(target)
        if normalized and normalized not in known_pages:
            missing.setdefault(normalized, target.replace("\\", "/").strip("/"))
    return sorted(missing.values(), key=str.casefold)


def find_child_note(client: ETAPI, parent_note_id: str, title: str) -> str | None:
    """Find an existing note with this title under the requested parent subtree."""
    escaped_title = title.replace("'", "''")
    result = client.search_note(
        f"note.title = '{escaped_title}'",
        ancestorNoteId=parent_note_id,
        fastSearch=False,
    )
    for note in result.get("results", []):
        if note.get("title") == title:
            return note["noteId"]
    return None


def create_note_and_get_id(client: ETAPI, parent_note_id: str, title: str) -> str:
    """Create a note and return its ID, with a useful error if ETAPI rejects it."""
    response = client.create_note(
        parentNoteId=parent_note_id,
        title=title,
        type="text",
        content="<p></p>",
    )
    if "note" not in response or "noteId" not in response["note"]:
        raise RuntimeError(
            f"Trilium create_note failed for title {title!r} under parent "
            f"{parent_note_id!r}. API response: {response!r}"
        )
    return response["note"]["noteId"]


def upload_markdown_files(client: ETAPI, parent_note_id: str, staged_graph: Path) -> None:
    """Upload Markdown files individually while preserving their directory hierarchy."""
    path_note_ids: dict[tuple[str, ...], str] = {(): parent_note_id}
    markdown_paths = sorted(
        (path for path in staged_graph.rglob("*") if path.is_file() and path.suffix.lower() == ".md"),
        key=lambda path: path.as_posix().casefold(),
    )

    for markdown_path in markdown_paths:
        relative = markdown_path.relative_to(staged_graph)
        parent_parts: tuple[str, ...] = ()
        for part in relative.parts[:-1]:
            current_parts = parent_parts + (part,)
            if current_parts not in path_note_ids:
                parent_id = path_note_ids[parent_parts]
                note_id = find_child_note(client, parent_id, part)
                if note_id is None:
                    note_id = create_note_and_get_id(client, parent_id, part)
                path_note_ids[current_parts] = note_id
            parent_parts = current_parts

        client.upload_md_file(file=str(markdown_path), parentNoteId=path_note_ids[parent_parts])


def create_link_notes(client: ETAPI, parent_note_id: str, targets: list[str]) -> int:
    """Create missing linked notes, using slash-separated targets as note hierarchies."""
    created = 0
    path_note_ids: dict[tuple[str, ...], str] = {(): parent_note_id}

    for target in targets:
        parts = tuple(part.strip() for part in target.split("/") if part.strip())
        parent_parts: tuple[str, ...] = ()
        for part in parts:
            current_parts = parent_parts + (part,)
            if current_parts not in path_note_ids:
                parent_id = path_note_ids[parent_parts]
                note_id = find_child_note(client, parent_id, part)
                if note_id is None:
                    note_id = create_note_and_get_id(client, parent_id, part)
                    created += 1
                path_note_ids[current_parts] = note_id
            parent_parts = current_parts
    return created


def upload_local_file_targets(
    client: ETAPI, parent_note_id: str, targets: set[str], graph: Path
) -> int:
    """Import local files referenced by wikilinks (for example Logseq whiteboards)."""
    created = 0
    path_note_ids: dict[tuple[str, ...], str] = {(): parent_note_id}
    for target, file_path in sorted(local_file_targets(targets, graph).items()):
        relative = file_path.relative_to(graph.resolve())
        parent_parts: tuple[str, ...] = ()
        for part in relative.parts[:-1]:
            current_parts = parent_parts + (part,)
            if current_parts not in path_note_ids:
                parent_id = path_note_ids[parent_parts]
                note_id = find_child_note(client, parent_id, part)
                if note_id is None:
                    note_id = create_note_and_get_id(client, parent_id, part)
                    created += 1
                path_note_ids[current_parts] = note_id
            parent_parts = current_parts
        parent_id = path_note_ids[parent_parts]
        title = file_path.name
        if find_child_note(client, parent_id, title) is None:
            client.create_file_note(
                parentNoteId=parent_id,
                title=title,
                file_path=str(file_path),
            )
            created += 1
    return created


def main() -> int:
    args = parse_args()
    graph = args.graph.expanduser().resolve()
    if not graph.is_dir():
        print(f"Fehler: Graph-Verzeichnis nicht gefunden: {graph}", file=sys.stderr)
        return 2

    ignored_folders = tuple(args.ignored_folders or DEFAULT_IGNORED_FOLDERS)
    files = markdown_files(graph, ignored_folders)
    targets = link_targets(files)
    missing_targets = missing_link_targets(targets, files, graph)
    file_targets = local_file_targets(targets, graph)
    print(f"Logseq-Graph: {graph}")
    print(f"Markdown-Dateien: {len(files)}")
    print(f"Erkannte Links und Tags: {len(targets)}")
    print(f"Lokal verlinkte Dateien: {len(file_targets)}")
    print(f"Fehlende verlinkte Notizen: {len(missing_targets)}")
    print(f"Ignorierte Ordnernamen: {', '.join(ignored_folders) or '(keine)'}")

    if args.dry_run:
        for path in files:
            relative = path.relative_to(graph)
            decoded_stem = "/".join(part for part in relative.stem.replace("___", "/").split("/") if part)
            print(relative.parent / f"{decoded_stem or relative.stem}{relative.suffix}")
        for target in sorted(file_targets, key=str.casefold):
            print(f"[Datei importieren] {target}")
        for target in missing_targets:
            print(f"[Notiz erstellen] {target}")
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
        with tempfile.TemporaryDirectory(prefix="logseq-trilium-") as staging_dir:
            staged_graph = Path(staging_dir)
            stage_markdown_files(files, graph, staged_graph)
            upload_markdown_files(client, args.parent_note_id, staged_graph)
        pages_note_id = find_child_note(client, args.parent_note_id, "pages")
        if pages_note_id is None:
            pages_note_id = create_note_and_get_id(client, args.parent_note_id, "pages")
        created = create_link_notes(client, pages_note_id, missing_targets)
        created += upload_local_file_targets(client, args.parent_note_id, targets, graph)
    except Exception as exc:  # noqa: BLE001 - display client/API errors to CLI users
        print(f"Import fehlgeschlagen: {exc}", file=sys.stderr)
        return 1

    print(f"Import abgeschlossen. Zusätzliche Notizen und Dateien erstellt: {created}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
