import openai
import re
import datetime
import json
import logging
import pathlib
import base64
import typing
import curses
import pandas as pd
from typing import Dict, List, Set, Optional
from pprint import pprint
# custom imports
import helpers


class ChapterSelectionUI:
    def __init__(self, data: Dict[str, List[str]]) -> None:
        self.data: Dict[str, List[str]] = data
        self.chapters: List[str] = list(data.keys())
        self.selections: Dict[str, Set[str]] = {ch: set() for ch in self.chapters}
        self.idx: int = 0

    # Utility
    @staticmethod
    def wrap_index(idx: int, total: int) -> int:
        return idx % total

    # Subchapter selection screen (scrollable)
    def select_subchapters(
        self,
        stdscr: curses.window,
        chapter: str,
        selected: Set[str],
        choices: List[str]
    ) -> Set[str]:
        idx: int = 0
        n: int = len(choices)
        max_lines: int = curses.LINES - 5  # reserve lines for header
        offset: int = 0

        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, "Arrow keys: navigate | s: toggle | a: all | d: none | q: back"[:curses.COLS-1])
            stdscr.addstr(1, 0, f"Chapter: {chapter}"[:curses.COLS-1])
            stdscr.addstr(2, 0, "-" * (curses.COLS-1))

            # adjust scroll offset
            if idx < offset:
                offset = idx
            elif idx >= offset + max_lines:
                offset = idx - max_lines + 1

            visible_choices = choices[offset:offset + max_lines]
            for display_idx, item in enumerate(visible_choices):
                mark: str = "[x]" if item in selected else "[ ]"
                hl: str = ">" if display_idx + offset == idx else " "
                stdscr.addstr(4 + display_idx, 0, f"{hl} {mark} {item}"[:curses.COLS-1])

            key: int = stdscr.getch()
            if key == curses.KEY_UP:
                idx = self.wrap_index(idx - 1, n)
            elif key == curses.KEY_DOWN:
                idx = self.wrap_index(idx + 1, n)
            elif key == ord('s'):
                item: str = choices[idx]
                if item in selected:
                    selected.remove(item)
                else:
                    selected.add(item)
            elif key == ord('a'):
                selected.clear()
                selected.update(choices)
            elif key == ord('d'):
                selected.clear()
            elif key == ord('q'):
                return selected

    # Confirmation screen
    def confirm_screen(self, stdscr: curses.window) -> bool:
        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, "Enter: confirm | q: back"[:curses.COLS-1])
            stdscr.addstr(1, 0, "Selected items:"[:curses.COLS-1])

            max_lines: int = curses.LINES - 3
            visible_items = list(self.selections.items())[:max_lines]

            line: int = 3
            for chap, items in visible_items:
                stdscr.addstr(line, 0, f"- {chap}: {list(items) if items else 'NONE'}"[:curses.COLS-1])
                line += 1

            key: int = stdscr.getch()
            if key == ord('q'):
                return False
            if key in (10, 13):
                return True

    # Main curses loop (scrollable)
    def run_curses(self, stdscr: curses.window) -> Optional[Dict[str, List[str]]]:
        curses.curs_set(0)
        offset: int = 0
        max_lines: int = curses.LINES - 3

        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, "Arrow keys: move | S: select/open | A: all (current) | D: none (current) | T: all (global) | R: none (global) | Enter: confirm | q: quit"[:curses.COLS-1])
            stdscr.addstr(1, 0, "(selected/total) | [C] = already classified")

            # aDjust scroll offset
            if self.idx < offset:
                offset = self.idx
            elif self.idx >= offset + max_lines:
                offset = self.idx - max_lines + 1

            visible_chapters = self.chapters[offset:offset + max_lines]
            for display_idx, chap in enumerate(visible_chapters):
                total: int = len(self.data[chap])
                if total == 1:
                    mark: str = "[x]" if self.selections[chap] else "[ ]"
                else:
                    mark = f"({len(self.selections[chap])}/{total})"
                
                # Check if there are existing files in the output folder
                output_folder = helpers.BASE_PATH/f"output/emotions_scored/{chap}/"
                completed_prefix = "[C]" if output_folder.exists() and any(list(output_folder.iterdir())) else "[ ]"

                hl: str = ">" if display_idx + offset == self.idx else " "
                stdscr.addstr(3 + display_idx, 0, f"{hl} {mark}\t{completed_prefix}\t{chap}"[:curses.COLS-1])

            key: int = stdscr.getch()
            if key == curses.KEY_UP:
                self.idx = self.wrap_index(self.idx - 1, len(self.chapters))
            elif key == curses.KEY_DOWN:
                self.idx = self.wrap_index(self.idx + 1, len(self.chapters))
            elif key == ord('s'):
                # Perform single selection
                chapter: str = self.chapters[self.idx]
                items: List[str] = self.data[chapter]
                if len(items) == 1:
                    if items[0] in self.selections[chapter]:
                        self.selections[chapter].clear()
                    else:
                        self.selections[chapter].add(items[0])
                else:
                    self.selections[chapter] = self.select_subchapters(
                        stdscr, chapter, self.selections[chapter], items
                    )
            elif key == ord('a'):
                # Select all subchapters
                ch: str = self.chapters[self.idx]
                self.selections[ch] = set(self.data[ch])
            elif key == ord('d'):
                # Deselect all subchapters
                ch: str = self.chapters[self.idx]
                self.selections[ch].clear()
            elif key in (10, 13):
                # Enter > Confirm selections window
                confirmed: bool = self.confirm_screen(stdscr)
                if confirmed:
                    curses.endwin()
                    return {k: list(v) for k, v in self.selections.items() if v}
            elif key == ord('t'):
                # Select all chapters and all their subchapters
                for ch, items in self.data.items():
                    self.selections[ch] = set(items)
            elif key == ord('r'):
                # Deselect all chapters
                for ch in self.chapters:
                    self.selections[ch].clear()
            elif key == ord('q'):
                # Quit without saving
                return None

    # Run the UI
    def main(self) -> Optional[Dict[str, List[str]]]:
        return curses.wrapper(self.run_curses)


class Chapter:
    def __init__(self, name:str, splits: list[pathlib.Path], type=typing.Literal["csv", "mp3"]):
        self.name = name
        self.splits = splits
        self.type = type

    def keep_splits(self, ixs: list[int]) -> list[pathlib.Path]:
        if len(self.splits) == 1:
            # Do not try to filter anything: current Chapter only has one split
            return self.splits
        else:
            splits = []
            for i in ixs:
                for split in self.splits:
                    if split.stem.endswith(str(i)):
                        splits.append(split)

            self.splits = splits
            return splits

    def __len__(self):
        return len(self.splits)

    def __repr__(self):
        return f"Chapter(name={self.name}, type={self.type}, splits={[spl.name for spl in self.splits]})"


class Pair:
    def __init__(self, chapter:str, csv: Chapter, mp3: Chapter):
        self.chapter = chapter
        self.csv = csv
        self.mp3 = mp3

    def keep_only_splits(self, indices: list[int]):
        self.mp3.splits = self.mp3.keep_splits(indices)
        self.csv.splits = self.csv.keep_splits(indices)

    def to_aux_dict(self) -> dict:
        return {
            self.chapter: [i for i in range(len(self.csv.splits))]
        }

    def __iter__(self):
        return zip(range(len(self.csv.splits)), iter(self.csv.splits), iter(self.mp3.splits))

    def __len__(self):
        return len(self.mp3)

    def __repr__(self):
        return f"Pair(chapter='{self.chapter}', csv={self.mp3}, mp3={self.mp3})"


class Classifier(object):
    def __init__(self):
        self.pairs = self.csv_mp3_split_pairs()
        self.csv_settings = helpers.CSV_SETTINGS

        in_notebook = helpers.in_notebook()
        if in_notebook:
            # Configure so that logs appear also in the notebook cells
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)

        # Target emotions
        self._negative_emotions = ["anger", "sadness", "fear"]
        self._positive_emotions = ["happiness", "ambitious", "surprise"]
        self.target_emotions = self._negative_emotions + self._positive_emotions

        # Prompt
        self.system_message = f"""
        ## TASK
        Evaluate the likelihood of the emotions in the audio dialogue.
        Consider the actor's interpretation, the background music and the meaning of the words.
        Only classify the following emotions:
        - positive: [{', '.join(self._positive_emotions)}]
        - negative: [{', '.join(self._negative_emotions)}]
        - neutral: [neutral]

        ## REQUIREMENTS
        - You will have the transcript of the dialogue. Use the row index as key when returning the estimate for the voice line.
        - Your analysis must rely EXCLUSIVELY on the audio. The transcript is provided ONLY to map voice lines by their row index.
        - Do NOT use the text to infer tone, emotion, or meaning.
        - Make sure to not classify any other emotion apart from those listed.
        - Don't mix positive and negative emotions in a single voice line.
        - Your estimate should be between 0 and 1, and the total should add up to 1.
        - If an emotion has a score lower than 0.1 , ignore it and add that score to the highest valued emotions.
        - If an emotion is not scored, return it with a score of 0.0
        - When you reply, do not add any other text. Just reply with a JSON formatted string.
        """

    def csv_mp3_split_pairs(self) -> list[Pair]:
        def list_files(path: pathlib.Path) -> list[dict]:
            pattern = r"(.+)_([0-9]+)$"
            ls = []
            for f in (path).iterdir():
                if f.is_file():
                    match = re.match(pattern, f.stem)
                    if match:
                        ls.append({
                            "stem": match.group(1),
                            "part": match.group(2),
                            "path": f,
                        })
                    else:
                        ls.append({
                            "stem": f.stem,
                            "part": 0,
                            "path": f,
                        })
            
            return ls

        csvs = list_files(helpers.CSV_PATH/"3_splits")
        mp3s = list_files(helpers.AUDIO_PATH/"3_splits")

        csvs_df = pd.DataFrame(csvs).groupby("stem").agg({"path": list})
        mp3s_df = pd.DataFrame(mp3s).groupby("stem").agg({"path": list})

        merged_df = pd.merge(
            left=csvs_df,
            right=mp3s_df,
            on="stem",
            how="inner",
            suffixes=["_csv", "_mp3"]
        ).reset_index()

        pairs = []
        for _, row in merged_df.iterrows():
            stem = row["stem"]
            csv_parts = Chapter(name=stem, splits=row["path_csv"], type="csv")
            mp3_parts = Chapter(name=stem, splits=row["path_mp3"], type="mp3")
            pair = Pair(chapter=stem, csv=csv_parts, mp3=mp3_parts)
            pairs.append(pair)

        return pairs

    def authorize(self, key: str=None):
        if not key:
            key = open(helpers.BASE_PATH/"open_ai_token.txt", "r").read()
        self.__openai_client = openai.OpenAI(api_key = key)

    def main(self):
        logging.info("Beginning classification")
        logging.info("---")
        for pair in self.pairs:
            chapter = pair.chapter

            logging.info(chapter)
            out_dfs = []
            out_responses = []
            for i, csv_file, mp3_file in pair:
                logging.info(f"Opening dataframe and audio for split #{i}")
                dialogues_df: pd.DataFrame = pd.read_csv(csv_file.as_posix(), **self.csv_settings)
                audio_data = open(mp3_file.as_posix(), "rb").read()

                logging.info(f"Preparing concat dialogue text and base64 audio for split #{i}")
                dialogue = self.prep_dialogue(dialogues_df)
                audio_b64 = self.prep_audio(audio_data)

                logging.info(f"Prompting GPT for split #{i}")
                chunk_response = self.prompt_model(dialogue, audio_b64)
                chunk_df = self.merge_response_and_dialogues(dialogues_df, chunk_response)
                out_dfs.append(chunk_df)
                out_responses.append(chunk_response)

            logging.info(f"Writing outputs")
            self.write_outputs(out_responses, out_dfs, chapter)
            logging.info("---")

    def set_chapters(self, chapters:typing.Union[list[str], dict]) -> list[Pair]:
        """
        (Optional) Manually define which chapters to classify.

        If `chapters` is a list of strings: keep only the chapters that match the same name and all its splits.
        
        If `chapters` is a dict: must be in the form of `{"chapter_name": [list_of_split_indexes]}`

        Example:
        ```
        {
            "chapter1": [0,1,2...],
            "chapter2": [0,1,2...]
        }
        ```
        """
        if chapters:
            sub_pairs = []
            if isinstance(chapters, list):
                for chapt in chapters:
                    found_match = False
                    for pair in self.pairs:
                        if chapt == pair.chapter:
                            sub_pairs.append(pair)
                            found_match = True
                        
                    if not found_match:
                        logging.warning(f"Chapter '{chapt}' unknown")

                logging.info(f"Chapters set correctely: {[p.chapter for p in sub_pairs]}")

            elif isinstance(chapters, dict):
                for chapter, splits in chapters.items():
                    found_match = False
                    for pair in self.pairs:
                        if chapter == pair.chapter:
                            pair.keep_only_splits(splits)
                            sub_pairs.append(pair)
                            found_match = True
                        
                    if not found_match:
                        logging.warning(f"Chapter '{chapt}' unknown")
                
                logging.info(f"Chapters and splits set correctely: {sub_pairs}")

            else:
                raise ValueError("`chapters` must be a list of chapter names, or a dict like {'chapter1': [0,1...], 'chapter2': [1,2...]}")

            self.pairs: list[Pair] = sub_pairs
            return sub_pairs

        else:
            raise ValueError("`chapters` can not be empty or null")

    def prep_dialogue(self, df: pd.DataFrame) -> str:
        """
        Prepares the input DataFrame to return the dialogues to be passed to the OpenAI chat model.
        """
        df.sort_values(by=["chapter_index", "dialogue_index", "line_index"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        df["id"] = df["dialogue_index"].astype(str) +"_"+ df["line_index"].astype(str)
        df["outc"] = df["id"] + " | " + df["speaker"] + ": " + df["line"]

        return "\n".join(df["outc"].to_list())

    def prep_audio(self, audio_data: bytes) -> str:
        """
        Encodes audio data to base64 string
        """
        return base64.b64encode(audio_data).decode("utf-8")

    def prompt_model(self, dialogues_text: str, audio_b64: str) -> dict:
        """
        Prompts the model and returns its response as dict

        Output structure: https://platform.openai.com/docs/api-reference/chat/object
        """

        # https://platform.openai.com/docs/api-reference/chat/create
        response = self.__openai_client.chat.completions.create(
            model="gpt-audio",
            temperature=0.1,
            max_completion_tokens=16384,
            messages=[
                {
                    "role": "system",
                    "content": self.system_message
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_b64,
                                "format": "mp3"
                            }
                        },
                        {
                            "type": "text",
                            "text": "TRANSCRIPT (DO NOT USE FOR CLASSIFICATION):\n" + dialogues_text
                        }
                    ]
                }
            ]
        )

        res_dict = response.to_dict()
        if res_dict['choices'][0]['finish_reason'] != 'stop':
            logging.error(json.dumps(res_dict, indent=2))
            raise ValueError("API response was not complete. Exiting...")

        return res_dict

    def merge_response_and_dialogues(self, dialogues_df: pd.DataFrame, res_dict: dict) -> pd.DataFrame:
        out_content = json.loads(res_dict['choices'][0]['message']['content'])
        emotions_df = pd.DataFrame.from_dict(out_content, orient='index')

        joined_df = pd.merge(
            dialogues_df,
            emotions_df,
            "left",
            left_on="id",
            right_on=emotions_df.index
        )
        joined_df.drop(["outc", "id"], axis=1, inplace=True)
        return joined_df

    def write_outputs(self, responses_list:list[dict], df_list: list[pd.DataFrame], chapter:str):
        emotions_short = "-".join([e[:3] for e in self.target_emotions])
        now = datetime.datetime.now().strftime("%d-%m-%YT%H-%M")
        fname = f"{now}_{emotions_short}"

        # Write API response
        api_response_path = helpers.BASE_PATH/f"./output/api_responses/{chapter}/{fname}.json"
        if not api_response_path.parent.exists():
            api_response_path.parent.mkdir()

        with open(api_response_path.as_posix(), "w") as f:
            json.dump(responses_list, f, indent=2)
            logging.info(f"Written API response '{fname}.json'")

        # Write dataframe
        emotions_df_path = helpers.BASE_PATH/f"./output/emotions_scored/{chapter}/{fname}.csv"
        if not emotions_df_path.parent.exists():
            emotions_df_path.parent.mkdir()

        out_df = pd.concat(df_list)
        out_df.sort_values(["dialogue_index", "line_index"], inplace=True)
        out_df.to_csv(emotions_df_path.as_posix(), **self.csv_settings, index=False)
        logging.info(f"Written file '{fname}.csv'")


if __name__ == "__main__":
    classifier = Classifier()
    classifier.authorize()

    # Get a dictionary of all chapters and sub-chapters
    # in the form of {"chapter": [0,1,2]}
    d = {}
    for p in classifier.csv_mp3_split_pairs():
        d.update(p.to_aux_dict())

    order_fn = lambda x: int(x[0].split("_")[0])
    d = dict(sorted(d.items(), key=order_fn))

    curses_ui = ChapterSelectionUI(data=d)
    selected_chapters = curses_ui.main()
    if selected_chapters:
        selected_chapters = dict(sorted(selected_chapters.items(), key=order_fn))

        print("Selected chapters and splits:")
        pprint(selected_chapters)
        print()

        y_n = input("Proceed with classification? (y): ")
        if y_n.lower() == "y":
            classifier.set_chapters(selected_chapters)
            classifier.main()
        else:
            print("Exiting...")
