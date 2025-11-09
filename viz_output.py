import streamlit as st
import pandas as pd
# custom scripts
import helpers


st.set_page_config(layout="wide")
COLOR_MAP = {
    "neutral": "#818181",
    "anger": "#dd0b27",
    "sadness": "#128cbc",
    "fear": "#a3cc3f",
    "happiness": "#f0f011",
    "surprise": "#e242df",
    "ambitious": "#302C2C"
}

# Select chapter and file
_, col1, col2, _ = st.columns([0.3, 0.2, 0.2, 0.3])
with col1:
    classified_chapters_dir = helpers.BASE_PATH/"./output/emotions_scored/"
    classified_chapters = [f for f in classified_chapters_dir.iterdir() if f.is_dir()]
    selected_chapter = st.selectbox(
        "Select chapter",
        classified_chapters,
        format_func=lambda x: x.stem
    )

with col2:
    classified_csvs = [f for f in (classified_chapters_dir/selected_chapter).iterdir() if f.is_file()]
    selected_file = st.selectbox(
        "Select file",
        classified_csvs,
        format_func=lambda x: x.name
    )

_, col_btn, _ = st.columns([0.7, 0.1, 0.2])
with col_btn:
    load_data_btn = st.button("Load data")

st.divider()

# Load data, audio and plot
if load_data_btn:
    # Audio player
    _, audio_col, _ = st.columns([3, 2, 3])
    with audio_col:
        audio_path = helpers.BASE_PATH/f"./audio/2_edits/{selected_chapter.stem}.wav"
        st.audio(audio_path)

    # Chart
    df: pd.DataFrame = pd.read_csv(selected_file.as_posix(), **helpers.CSV_SETTINGS)
    df[["chapter_index", "dialogue_index", "line_index"]] = df[["chapter_index", "dialogue_index", "line_index"]].astype(str)

    col1, col2 = st.columns(2)
    with col1:
        df["id"] = df["dialogue_index"] + "_" + df["line_index"]
        emotions = [c for c in df.columns.to_list() if c in COLOR_MAP.keys()]
        color_list = [COLOR_MAP.get(e, "#B3B3B3") for e in emotions]
        st.bar_chart(
            df,
            x="id",
            y=emotions,
            color=color_list,
            sort=False,
            height=500
        )

    # Dialogues table
    with col2:
        show_columns = ["dialogue_index", "line_index", "speaker", "line"]
        subs_df = df[show_columns]
        st.dataframe(subs_df, hide_index=True)
