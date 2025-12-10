import argparse
import logging
import textwrap
# custom scripts
from editor import Editor
from scraper import Scraper
from splitter import Splitter


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description=textwrap.dedent(
            """
            Run the data preparation pipeline. Does not include classification (i.e. model prompting).
            To run the data classification, use 'python classifier.py' which will have a cmd-line UI
            """
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--no-scraper", action="store_true", help="Do not run the Scraper")
    parser.add_argument("--no-editor", action="store_true", help="Do not run the Editor")
    parser.add_argument("--no-splitter", action="store_true", help="Do not run the Splitter")
    parser.add_argument("--keep-narrator", action="store_true", help="Keep the narrator lines")
    parser.add_argument("--keep-gibberish", action="store_true", help="Do not add a \"(gibberish)\" prefix to all the lines in gibberish")
    args = parser.parse_args()
    logging.info(f"Running with arguments: {args}")

    starting_webpage = (
        "https://www.dawnborn.com/game-transcripts/"
        "clair-obscur-expedition-33-game-transcript-all-dialogues/"
        "clair-obscur-expedition-33-the-gommage-dawnborn/"
    )

    if args.no_scraper is False:
        logging.info("### BEGIN SCRAPER ###")
        parser = Scraper(parser="html.parser")
        parser.load_page(starting_webpage)
        parser.main()

    if args.no_editor is False:
        logging.info("### BEGIN EDITOR ###")
        editor = Editor(cmd_line_args=args)
        editor.main()

    if args.no_splitter is False:
        logging.info("### BEGIN SPLITTER ###")
        splitter = Splitter()
        splitter.main()
