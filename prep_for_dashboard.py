import pathlib
import logging
import datetime
import io
import pandas as pd
# custom scripts
import helpers


logging.basicConfig(level=logging.INFO)
logging.getLogger(__name__)


emotions_scored_dir = helpers.BASE_PATH/"output/emotions_scored/"

dfs = []
logging.info("Beginning selection of latest classification file for each chapter")
logging.info("---")
for item in emotions_scored_dir.iterdir():
    if item.is_dir() and item.stem != "Z_Final":
        chapter = item.stem
        files = list((emotions_scored_dir/item).iterdir())

        if len(files) > 0:
            most_recent_file = max(files, key=lambda f: f.stat().st_ctime)
            logging.info(f"Chapter '{chapter}': selected file '{most_recent_file.name}'")

            df = pd.read_csv(most_recent_file.as_posix(), **helpers.CSV_SETTINGS)
            dfs.append(df)
        else:
            logging.warning(f"Chapter '{chapter}' does not have any classification file. Skipped.")

full_df = pd.concat(dfs)
full_df.sort_values(["chapter_index", "dialogue_index", "line_index"], inplace=True)
logging.info("Concatenated all files into one:\n")

buffer = io.StringIO()
full_df.info(buf=buffer)
info_str = buffer.getvalue()
logging.info(info_str)

out_path = emotions_scored_dir/f"Z_Final/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
full_df.to_csv(out_path.as_posix(), **helpers.CSV_SETTINGS, index_label="row_index")
logging.info(f"File exported at {out_path.as_posix()}")
