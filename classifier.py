import openai
import re
import datetime
import json
import logging
import pathlib
import base64
import typing
import pandas as pd
# custom imports
import helpers


class Chapters:
    def __init__(self, name:str, parts: list[pathlib.Path], type=typing.Literal["csv", "wav"]):
        self.name = name
        self.parts = parts
        self.type = type

    def __repr__(self):
        return f"Chapters(name={self.name}, type={self.type}, parts={self.parts})"


class Pair:
    def __init__(self, chapter:str, csv: Chapters, wav: Chapters):
        self.chapter = chapter
        self.csv = csv
        self.wav = wav

    def __iter__(self):
        return zip(range(len(self.csv.parts)), iter(self.csv.parts), iter(self.wav.parts))

    def __repr__(self):
        return f"Pair(chapter='{self.chapter}', csv={self.csv}, wav={self.wav})"


class Classifier(object):
    def __init__(self):
        self.pairs = self.csv_wav_split_pairs()
        self.csv_settings = helpers.CSV_SETTINGS

        in_notebook = helpers.in_notebook()
        if in_notebook:
            # Configure so that logs appear also in the notebook cells
            logger = logging.getLogger()
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)

        # OpenAI client
        __openai_key = open(helpers.BASE_PATH/"open_ai_token.txt", "r").read()
        self.__openai_client = openai.OpenAI(api_key = __openai_key)

        # Target emotions
        self._negative_emotions = ["anger", "sadness", "fear"]
        self._positive_emotions = ["happiness", "ambitious", "surprise"]
        self.target_emotions = self._negative_emotions + self._positive_emotions

        # Prompt
        self.system_message = f"""
        ## TASK
        Evaluate the likelihood of the emotions in the dialogue.
        Consider the actor's interpretation, the background music and the meaning of the words.
        Only classify the following emotions:
        - positive: [{', '.join(self._positive_emotions)}]
        - negative: [{', '.join(self._negative_emotions)}]
        - neutral: [neutral]

        ## REQUIREMENTS
        - You will have the transcript of the dialogue. Use the row index as key when returning the estimate for the voice line.
        - Make sure to not classify any other emotion apart from those listed.
        - Don't mix positive and negative emotions in a single voice line.
        - Your estimate should be between 0 and 1, and the total should add up to 1.
        - If an emotion has a score lower than 0.1 , ignore it and add that score to the highest valued emotions.
        - If an emotion is not scored, return it with a score of 0.0
        - When you reply, do not add any other text. Just reply with a JSON formatted string.
        """

    def csv_wav_split_pairs(self) -> list[Pair]:
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
        wavs = list_files(helpers.AUDIO_PATH/"3_splits")

        csvs_df = pd.DataFrame(csvs).groupby("stem").agg({"path": list})
        wavs_df = pd.DataFrame(wavs).groupby("stem").agg({"path": list})

        merged_df = pd.merge(
            left=csvs_df,
            right=wavs_df,
            on="stem",
            how="inner",
            suffixes=["_csv", "_wav"]
        ).reset_index()

        pairs = []
        for _, row in merged_df.iterrows():
            stem = row["stem"]
            csv_parts = Chapters(name=stem, parts=row["path_csv"], type="csv")
            wav_parts = Chapters(name=stem, parts=row["path_wav"], type="wav")
            pair = Pair(chapter=stem, csv=csv_parts, wav=wav_parts)
            pairs.append(pair)

        return pairs

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
                audio_data = open(wav_file.as_posix(), "rb").read()

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

    def set_chapters(self, chapters:list[str]) -> list[Pair]:
        """
        (Optional) Manually define which chapters to classify.
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

                logging.info(f"Chapters set correctely: {[p.chapter for p in self.pairs]}")

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
                
                logging.info(f"Chapters and splits set correctely: {self.pairs}")

            else:
                raise ValueError("`chapters` must be a list of chapter names, or a dict like {'chapter1': [0,1...], 'chapter2': [1,2...]}")

            self.pairs: list[Pair] = sub_pairs
            return sub_pairs

        else:
            raise ValueError("`chapters` parameter must be a list of chapter names. It can not be empty or null")

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
            messages=[
                {
                "role": "system",
                "content": self.system_message
                },
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": dialogues_text
                    },
                    {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_b64,
                        "format": "wav"
                    }
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
    # Test run
    classifier.set_chapters(["11_Monocos_Station"])

    # classifier.set_chapters({
    #     "11_Monocos_Station": [0],
    #     "16_The_Monolith": [0,2]
    # })
    classifier.main()
