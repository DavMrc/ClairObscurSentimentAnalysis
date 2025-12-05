import pathlib
import csv


BASE_PATH = pathlib.Path(__file__).parent/"data"
CSV_PATH = BASE_PATH/"csv"
AUDIO_PATH = BASE_PATH/"audio"
CSV_SETTINGS = {'quotechar': '"', 'quoting': csv.QUOTE_ALL}
