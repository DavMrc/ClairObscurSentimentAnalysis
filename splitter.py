import wave
import pathlib
import logging
import json
import shutil
import os
import contextlib
import pandas as pd
# custom scripts
import helpers


class Splitter(object):
    def __init__(self):
        self.split_rules = json.load(open(helpers.CSV_PATH/"0_rules/splits.json", "r"))
        self.csv_settings = helpers.CSV_SETTINGS

        self.delete_existing_files()

    def delete_existing_files(self):
        logging.info("Deleting existing csv splits")
        
        for f in (helpers.CSV_PATH/"3_splits").iterdir():
            if f.is_file():
                os.remove(f.as_posix())
        
        logging.info("Deleting existing wav splits")
        for f in (helpers.AUDIO_PATH/"3_splits").iterdir():
            if f.is_file():
                os.remove(f.as_posix())

    def _csv_wav_edit_pairs(self) -> list[dict]:
        csvs = [f for f in (helpers.CSV_PATH/"2_edits").iterdir() if f.is_file()]
        wavs = [f for f in (helpers.AUDIO_PATH/"2_edits").iterdir() if f.is_file()]

        # Link each wav to its matching csv
        pairs = []
        for csv in csvs:
            for wav in wavs:
                if csv.stem == wav.stem:
                    pairs.append({
                        "csv": csv,
                        "wav": wav
                    })

        return pairs

    def main(self):
        # Link each wav to its matching csv
        pairs = self._csv_wav_edit_pairs()
        for pair in pairs:
            logging.info(f"Splitting csv for {pair['csv'].stem}")
            self._split_csv(pair["csv"])
            logging.info(f"Splitting audio for {pair['wav'].stem}")
            self._split_wav(pair["wav"])
            logging.info("---")

    def _split_csv(self, path:pathlib.Path):
        df = pd.read_csv(path.as_posix(), **self.csv_settings)
        file_has_split_rules = False
        splits = []
        for split_rule in self.split_rules:
            if path.stem == split_rule["source"]:
                splits = split_rule["ranges"]
                file_has_split_rules = True

        if file_has_split_rules:
            logging.info(f"Splitting {path.stem} in multiple csvs according to:\n{splits}")
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

            for i, slice in enumerate(slices):
                slice.to_csv(helpers.CSV_PATH/f"3_splits/{path.stem}_{i}.csv", index=False, **self.csv_settings)

        else:
            logging.info(f"{path.stem} copied as-is")
            df.to_csv(helpers.CSV_PATH/f"3_splits/{path.stem}.csv", index=False, **self.csv_settings)

    def _split_wav(self, path:pathlib.Path):
        # Convert timestamps to seconds
        timestamps = []
        for split_rule in self.split_rules:
            if split_rule["source"] == path.stem:
                timestamps = [self.__time_to_seconds(t) for t in split_rule["timestamps"]]

        if timestamps:
            with contextlib.closing(wave.open(path.as_posix(), 'rb')) as wav:
                frame_rate = wav.getframerate()
                n_channels = wav.getnchannels()
                sampwidth = wav.getsampwidth()
                n_frames = wav.getnframes()
                total_duration = n_frames / frame_rate

                # Add start and end points
                split_points = [0] + timestamps + [total_duration]

                for i in range(len(split_points) - 1):
                    start_sec = split_points[i]
                    end_sec = split_points[i + 1]

                    start_frame = int(start_sec * frame_rate)
                    end_frame = int(end_sec * frame_rate)

                    wav.setpos(start_frame)
                    frames = wav.readframes(end_frame - start_frame)

                    out_name = f"{path.parent.parent}/3_splits/{path.stem}_{i}.wav"
                    with wave.open(out_name, 'wb') as out:
                        out.setnchannels(n_channels)
                        out.setsampwidth(sampwidth)
                        out.setframerate(frame_rate)
                        out.writeframes(frames)

                    start_timestamp = self.__seconds_to_time(start_sec)
                    end_timestamp = self.__seconds_to_time(end_sec)
                    logging.info(f"Wrote audio split {path.stem}_{i}: {start_timestamp}s → {end_timestamp}s")
        else:
            cur_path = path.as_posix()
            dest_path = path.parent.parent/"3_splits"/path.name
            shutil.copy(cur_path, dest_path)
            logging.info(f"{path.name} copied as-is")

    def __time_to_seconds(self, t:str):
        """Convert 'MM:SS' or 'HH:MM:SS' string to seconds"""
        parts = [int(p) for p in t.split(":")]
        if len(parts) == 2:
            m, s = parts
            return m * 60 + s
        elif len(parts) == 3:
            h, m, s = parts
            return h * 3600 + m * 60 + s
        else:
            raise ValueError("Invalid time format")
    
    def __seconds_to_time(self, seconds):
        """Convert seconds to 'MM:SS' string"""
        seconds = int(seconds)
        m = (seconds % 3600) // 60
        s = seconds % 60

        return f"{m:02d}:{s:02d}"
