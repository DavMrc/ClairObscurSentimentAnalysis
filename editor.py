import logging
import pathlib
import csv
import os
import json
import pandas as pd
from argparse import Namespace


BASE_PATH = pathlib.Path(__file__).parent/"data"
CSV_PATH = BASE_PATH/"csv"


class Editor(object):
    def __init__(self, cmd_line_args: Namespace):
        self.cmd_line_args: Namespace = cmd_line_args
        self.csv_settings = {'quotechar': '"', 'quoting': csv.QUOTE_ALL}

        self.delete_existing_csvs()

    def delete_existing_csvs(self):
        for f in (CSV_PATH/"edits").iterdir():
            if f.is_file() and ".csv" in f.name:
                os.remove(f.as_posix())

    def main(self):
        edit_rules = json.load(open(CSV_PATH/"edits/rules/rules.json", "r"))

        logging.info("Beginning custom edits")
        for chapter_csv in (CSV_PATH/"raw").iterdir():
            fname = chapter_csv.name.split(".")[0]
            logging.info(fname)
            df = pd.read_csv(chapter_csv.as_posix(), **self.csv_settings)

            # 1. Delete custom row ranges
            for split_rule in edit_rules["deletes"]:
                if fname == split_rule["source"]:
                    ranges = split_rule['ranges']
                    logging.info(f"Deleting rows from {fname} based on ranges:\n{ranges}")
                    df = self._deletes(df, ranges)

            # 2. Delete narrator
            if self.cmd_line_args.keep_narrator is False:
                logging.info(f"Removing narrator dialogues from {fname}")
                df = self._delete_narrator(df)

            # 3. Prefix gibberish
            if self.cmd_line_args.keep_gibberish is False:
                logging.info(f"Prefixing gibberish lines in {fname}")
                df = self._prefix_gibberish(df)
            
            # 4. Split into multiple files
            file_was_written_as_splits = False
            for split_rule in edit_rules["splits"]:
                if fname == split_rule["source"]:
                    splits = split_rule["ranges"]
                    logging.info(f"Splitting {fname} in multiple files according to:\n{splits}")

                    slices = self._splits(df, splits)
                    for i, slice in enumerate(slices):
                        slice.to_csv(CSV_PATH/f"edits/{fname}_{i}.csv", index=False, **self.csv_settings)
                    
                    file_was_written_as_splits = True
                    break

            if not file_was_written_as_splits:
                df.to_csv(CSV_PATH/f"edits/{fname}.csv", index=False, **self.csv_settings)
            logging.info("---")
        
        # Handle custom inserts
        logging.info("Beginning custom inserts")
        self._inserts(edit_rules["inserts"])

    def _inserts(self, inserts: list):
        for i in inserts:
            fname = i+".csv"
            logging.info(f"Copying file {fname}")

            in_path = (CSV_PATH/"edits/custom_inserts"/fname).as_posix()
            in_file = open(in_path, "r", encoding="utf-8", newline="")
            reader = csv.reader(in_file, **self.csv_settings)

            out_path = (CSV_PATH/"edits"/fname).as_posix()
            out_file = open(out_path, "w", encoding="utf-8", newline="")
            writer = csv.writer(out_file, **self.csv_settings)

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

    def _splits(self, df: pd.DataFrame, splits: list) -> list[pd.DataFrame]:        
        slices = []
        for split in splits:
            dial_s, line_s = split["dial_s"], split["line_s"]
            dial_e, line_e = split["dial_e"], split["line_e"]

            # start condition
            start_mask = (df["dialogue_index"] > dial_s) | (
                (df["dialogue_index"] == dial_s) & (df["line_index"] >= line_s)
            )
            # end condition
            if dial_e == -1 and line_e == -1:
                # take everything after start
                mask = start_mask
            else:
                end_mask = (df["dialogue_index"] < dial_e) | (
                    (df["dialogue_index"] == dial_e) & (df["line_index"] <= line_e)
                )
                mask = start_mask & end_mask

            slices.append(df[mask].copy())
        
        return slices

    def _deletes(self, df: pd.DataFrame, ranges: list[dict]):
        del_ranges = pd.DataFrame(ranges)

        mask = pd.Series(True, index=df.index)
        for _, r in del_ranges.iterrows():
            to_delete = (
                ((df["dialogue_index"] > r["dial_s"]) |
                ((df["dialogue_index"] == r["dial_s"]) & (df["line_index"] >= r["line_s"])))
                &
                ((df["dialogue_index"] < r["dial_e"]) |
                ((df["dialogue_index"] == r["dial_e"]) & (df["line_index"] <= r["line_e"])))
            )
            mask &= ~to_delete  # remove these rows

        df_filtered = df[mask].reset_index(drop=True)
        return df_filtered

    def _delete_narrator(self, df: pd.DataFrame):
        return df[df["speaker"] != "narrator"]

    def _prefix_gibberish(self, df: pd.DataFrame):
        gibberish_classes = [
            'fading', 'gestral', 'grandis', 'faceless'
        ]
        gibberish_speakers = [
            'The Curator', 'Noco', 'Young boy', 'Lady of Sap', 'Golgra', 'Jar', '???',
            'Karatom', 'Tropa', 'Peron', 'Olivierso', 'Jujubree', 'Berrami',
            'Eesda', 'Alexcyclo', 'Victorifo', 'Limonsol'
        ]

        # Add "(gibberish) " prefix to lines where speaker is in gibberish_speakers
        # or contains any word in speaker_classes
        prefix = "(gibberish) "
        mask = ((
                df["speaker"].isin(gibberish_speakers) |
                df["speaker"].str.contains('|'.join(gibberish_classes), case=False, na=False)
            ) &
            ~df["line"].str.contains(prefix, case=False, na=False, regex=False)
        )
        df.loc[mask, "line"] = prefix + df.loc[mask, "line"]
        return df
