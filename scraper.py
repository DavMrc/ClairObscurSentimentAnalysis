import requests
import pathlib
import unicodedata
import re
import datetime
import logging
import csv
import json
import bs4
from typing import Literal


BASE_PATH = pathlib.Path(__file__).parent/"data"


class Parser:
    def __init__(self, parser: str, output_type: Literal["json", "csv"]="csv"):
        self.parser = parser
        self.output_type = output_type

        self._page_scraped_ix = 0
        self.__soup: bs4.BeautifulSoup = None
        self.__main_container: bs4.element.Tag = None
        self.__paragraphs: list[bs4.element.Tag] = None

    def load_page(self, url: str):
        res = requests.get(url)
        soup = bs4.BeautifulSoup(res.text, self.parser)

        # Main container
        classes = [
            "wp-block-group__inner-container",
            "is-layout-constrained",
            "wp-container-core-group-is-layout-5ca99053",
            "wp-block-group-is-layout-constrained"
        ]
        main_container: bs4.element.Tag = soup.find(class_=" ".join(classes))

        paragraphs = main_container.find_all("p")
        # Paragraphs with lines don't have a class attribute
        paragraphs = [p for p in paragraphs if not p.has_attr("class")]

        self.__soup = soup
        self.__main_container = main_container
        self.__paragraphs = paragraphs

    def main(self):
        if self.__soup is None or self.__main_container is None or self.__paragraphs is None:
            raise RuntimeError("No page loaded. Call load_page(url) first.")

        title = self.get_title()
        logging.info(f"Parsing chapter: '{title}'")

        dialogues = self.parse_dialogues(chapter=title)
        self.write(dialogues, chapter=title)
        self._page_scraped_ix += 1

        next_page = self.next_page_link()
        if next_page:
            logging.info(f"Next chapter link found: {next_page}")
            self.load_page(next_page)
            self.main()
        else:
            logging.error("No next chapter link found.")

    def get_title(self) -> str:
        return self.__soup.find("h1", class_="has-text-align-center").text.strip()

    def next_page_link(self) -> str:
        links = self.__main_container.find("p", class_="has-text-align-right").find_all("a")
        next_page_link = None

        for link in links:
            if "next chapter" in link.text.strip().lower():
                next_page_link = link['href']
                break

        return next_page_link
    
    def parse_dialogues(self, chapter: str=None) -> list:
        dialogues = []
        last_speaker = None
        for i, p in enumerate(self.__paragraphs):
            try:
                parent_class = " ".join(p.parent.attrs["class"])
                if "wp-block-group info-card" in parent_class:
                    # Dialogue from the narrator
                    last_speaker = "narrator"
            except KeyError:
                pass

            lines = []
            index = 0
            for child_ix, child in enumerate(list(p.children)):
                if child.name == "strong":
                    # New speaker
                    last_speaker = child.text.strip().replace(":", "")
                elif child.name is None or child.name == "em":
                    # Dialogue line
                    line:str = child.text.strip()

                    if child.name == "em":
                        if not (line.startswith("(") and line.endswith(")")):
                            # Lines of the narrator are not enclosed between parenthesis. If they are, they
                            # are considered a "line of thought" of the character
                            speaker = "narrator"
                        
                        if child_ix != 0:
                            # Sometimes, in a line, italics can be used as reinforcement. In the website,
                            # italics is also used to highlight narrator speaking. We consider the narrator
                            # speaking only if the line in italics is the first (and only) line in the paragraph
                            speaker = last_speaker
                    else:
                        speaker = last_speaker

                    if line:
                        if self.output_type == "json":
                            lines.append({
                                "line_index": index,
                                "speaker": speaker,
                                "line": line
                            })
                        elif self.output_type == "csv":
                            lines.append([self._page_scraped_ix, chapter, i, index, speaker, line])
                        index += 1
                else:
                    # Line breaks or other tags
                    pass

            if self.output_type == "json":
                dialogue = {}
                dialogue["dialogue_index"] = i
                dialogue["lines"] = lines
                dialogues.append(dialogue)
            elif self.output_type == "csv":
                dialogues.append(lines)

        if self.output_type == "json":
            return {
                "chapter_index": self._page_scraped_ix,
                "chapter": chapter,
                "dialogues": dialogues
            }
        elif self.output_type == "csv":
            return dialogues

    def write(self, dialogues: list, chapter: str=None):
        if chapter is None:
            chapter = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        outfile = open(
            BASE_PATH/self.output_type/f"{self._page_scraped_ix}_{chapter}.{self.output_type}",
            "w",
            encoding="utf-8",
            newline=""
        )
        chapter = self.__file_name_safe(chapter)
        if self.output_type == "json":
            # Write JSON
            json.dump(
                dialogues,
                outfile,
                indent=2,
                ensure_ascii=False
            )
        elif self.output_type == "csv":
            # Write CSV
            writer = csv.writer(outfile, quotechar='"', quoting=csv.QUOTE_ALL)
            writer.writerow(["chapter_index", "chapter", "dialogue_index", "line_index", "speaker", "line"])
            # Unpack list of lists
            for dialogue in dialogues:
                writer.writerows(dialogue)

    def __file_name_safe(self, title: str):
        # Normalize accents (e.g., é → e)
        normalized = unicodedata.normalize('NFKD', title)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        # Replace non-alphanumeric characters (except space, dash, underscore)
        cleaned = re.sub(r'[^a-zA-Z0-9\s\-_]', '', ascii_text)
        # Replace spaces with underscores
        cleaned = re.sub(r'\s+', '_', cleaned.strip())
        # Limit filename length for safety
        return cleaned[:255]


class Inserter:
    def __init__(self, output_type="csv"):
        self.output_type = output_type
    
    def insert_custom(self):
        if self.output_type == "csv":
            for f in (BASE_PATH/"custom_lines").iterdir():
                logging.info(f"Copying file {f.name} to csv/ directory")

                in_path = (f).as_posix()
                in_file = open(in_path, "r", encoding="utf-8", newline="")
                reader = csv.reader(in_file, quotechar='"', quoting=csv.QUOTE_ALL)

                out_path = (BASE_PATH/"csv"/f.name).as_posix()
                out_file = open(out_path, "w", encoding="utf-8", newline="")
                writer = csv.writer(out_file, quotechar='"', quoting=csv.QUOTE_ALL)

                # Track the last dialogue index and current line index across rows
                last_dialogue_index = None
                line_index = 0
                for i, row in enumerate(list(reader)):
                    if i == 0:
                        # Insert header
                        row.insert(3, "line_index")
                    else:
                        curr_dialogue_index = row[2]
                        if last_dialogue_index is None or curr_dialogue_index != last_dialogue_index:
                            # New dialogue: reset counter
                            line_index = 0
                        else:
                            # Same dialogue: increment
                            line_index += 1

                        row.insert(3, str(line_index))
                        last_dialogue_index = curr_dialogue_index

                    writer.writerow(row)
        else:
            logging.error("Inserter only supports csv files")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    starting_webpage = (
        "https://www.dawnborn.com/game-transcripts/"
        "clair-obscur-expedition-33-game-transcript-all-dialogues/"
        "clair-obscur-expedition-33-the-gommage-dawnborn/"
    )
    
    parser = Parser("html.parser", output_type="csv")
    parser.load_page(starting_webpage)

    parser.main()

    inserter = Inserter(output_type="csv")
    inserter.insert_custom()
