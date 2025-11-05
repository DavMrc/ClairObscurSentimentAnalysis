import argparse
import logging
from editor import Editor
from scraper import Scraper


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Run the scraper and editor.")
    parser.add_argument("--no-scraper", action="store_true", help="Do not run the Scraper")
    parser.add_argument("--no-editor", action="store_true", help="Do not run the Editor")
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
        parser = Scraper("html.parser")
        parser.load_page(starting_webpage)
        parser.main()

    if args.no_editor is False:
        editor = Editor(args)
        editor.main()
