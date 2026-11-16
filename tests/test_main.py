import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import main


class LogseqGraphTests(unittest.TestCase):
    def test_triple_underscore_decodes_to_page_path(self):
        self.assertEqual(main.normalize_target("Support___SR___Nummer1234"), "support/sr/nummer1234")

    def test_encoded_page_is_not_reported_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            graph = Path(temporary_directory)
            page = graph / "pages" / "Support___SR___Nummer1234.md"
            page.parent.mkdir()
            page.write_text("- Test", encoding="utf-8")
            self.assertEqual(
                main.missing_link_targets({"Support/SR/Nummer1234"}, [page], graph),
                [],
            )

    def test_code_examples_are_not_extracted_as_links_or_tags(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            markdown = Path(temporary_directory) / "page.md"
            markdown.write_text(
                """[[Real Page]] #real
```md
[[Fake Page]] #fake
```
`[[Inline Fake]] #inline`
#+BEGIN_QUOTE
""",
                encoding="utf-8",
            )
            self.assertEqual(main.link_targets([markdown]), {"Real Page", "real"})

    def test_local_wikilink_file_is_not_a_missing_note_and_uploads_as_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            graph = Path(temporary_directory)
            whiteboard = graph / "draws" / "board.excalidraw"
            whiteboard.parent.mkdir()
            whiteboard.write_text("{}", encoding="utf-8")
            targets = {"draws/board.excalidraw"}
            self.assertEqual(main.missing_link_targets(targets, [], graph), [])

            client = Mock()
            client.search_note.return_value = {"results": []}
            client.create_note.return_value = {"note": {"noteId": "draws-id"}}
            self.assertEqual(main.upload_local_file_targets(client, "root", targets, graph), 2)
            client.create_file_note.assert_called_once_with(
                parentNoteId="draws-id",
                title="board.excalidraw",
                file_path=str(whiteboard.resolve()),
            )


if __name__ == "__main__":
    unittest.main()
