import logging
import pathlib
import csv
import os
import json
import pandas as pd
from argparse import Namespace


class Editor(object):
    def __init__(self, cmd_line_args: Namespace, csv_settings: dict):
        self.cmd_line_args: Namespace = cmd_line_args
        self.csv_settings = csv_settings

        self.delete_existing_csvs()

    def delete_existing_csvs(self):
        for f in (helpers.CSV_PATH/"2_edits").iterdir():
            if f.is_file() and ".csv" in f.name:
                os.remove(f.as_posix())

    def main(self):
        edit_rules = json.load(open(helpers.CSV_PATH/"0_rules/rules.json", "r"))

        logging.info("Beginning custom edits")
        for chapter_csv in (helpers.CSV_PATH/"1_raw").iterdir():
            fname = chapter_csv.stem
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

            df.to_csv(helpers.CSV_PATH/f"2_edits/{fname}.csv", index=False, **self.csv_settings)
            logging.info("---")
        
        # Handle custom inserts
        logging.info("Beginning custom inserts")
        self._inserts(edit_rules["inserts"])

    def _inserts(self, inserts: list):
        for i in inserts:
            fname = i+".csv"
            logging.info(f"Copying file {fname}")

            in_path = (helpers.CSV_PATH/"2_edits/custom_inserts"/fname).as_posix()
            in_file = open(in_path, "r", encoding="utf-8", newline="")
            reader = csv.reader(in_file, **self.csv_settings)

            out_path = (helpers.CSV_PATH/"2_edits"/fname).as_posix()
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
