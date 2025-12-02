import pathlib
import streamlit as st
import pandas as pd
import plotly.express as px
# custom scripts
import helpers


st.title("Emotion Classification Inspector")
st.set_page_config(
    page_title="Emotion Classification Inspector",
    layout="wide"
)
COLOR_MAP = {
    "neutral": "#818181",
    "anger": "#dd0b27",
    "sadness": "#128cbc",
    "fear": "#a3cc3f",
    "happiness": "#f0f011",
    "surprise": "#e242df",
    "ambitious": "#302C2C"
}

def custom_file_loader(key:str, options:list[pathlib.Path], chapter:str=None, **kwargs) -> dict:
    col1, col2 = st.columns([0.8, 0.2])
    with col2:
        opt = st.radio("aaa", ["Select", "Upload"], key=f"{key}_radio", label_visibility="collapsed")

    selection = None
    with col1:
        if opt == "Select":
            selection:pathlib.Path = st.selectbox(
                label=key,
                options=options,
                **kwargs
            )
            audio_path = None
            if chapter:
                audio_path = helpers.BASE_PATH/f"./audio/2_edits/{chapter}.wav"
            return {"selection": selection, "audio_path": audio_path}
        else:
            selection = st.file_uploader(
                label=key,
                type="csv"
            )
            return {"selection": selection, "audio_path": None}

# Inspect vs Compare mode: inspect a single dataframe
# or compare one to another
mode = st.segmented_control("asdf", ["Inspect", "Compare"], key="mode_select", default="Inspect",
                            selection_mode="single", label_visibility="collapsed")
if "mode" not in st.session_state or st.session_state["mode"] != mode:
    st.session_state["mode"] = mode
mode = st.session_state["mode"]

col_no = 2
if mode == "Compare":
    col_no = 3

columns = st.columns(col_no)
# Select chapter
with columns[0]:
    classified_chapters_dir = helpers.BASE_PATH/"./output/emotions_scored/"
    classified_chapters = [f for f in classified_chapters_dir.iterdir() if f.is_dir()]
    classified_chapters.sort(key=lambda x: int(x.stem.split("_")[0]))
    selected_chapter = st.selectbox(
        "Select chapter",
        classified_chapters,
        format_func=lambda x: x.stem
    )

# Select file
classified_csvs = [f for f in (classified_chapters_dir/selected_chapter).iterdir() if f.is_file()]
classified_csvs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
most_recent_file = max(classified_csvs, key=lambda x: x.stat().st_mtime)
fmt_func = lambda x: f"⭐ {x.name}" if x == most_recent_file else x.name
with columns[1]:
    selection = custom_file_loader(
        key="Select file",
        options=classified_csvs,
        format_func=fmt_func,
        chapter=selected_chapter.stem
    )
    selection_csv_path = selection["selection"]
    selection_audio_path = selection["audio_path"]

# Select second file (comparison)
try:
    with columns[2]:
        comparison = custom_file_loader(
            key="Comparison file",
            options=classified_csvs,
            format_func=fmt_func
        )
        comparison_csv_path = comparison["selection"]
except IndexError:
    pass

# Load data button
_, col_btn = st.columns([0.8, 0.2])
with col_btn:
    load_data_btn = st.button("Load data")
    if "load" not in st.session_state:
        st.session_state["load"] = False

st.divider()


# Load data, audio and plot
def load_dataframe(path_or_buffer):
    if isinstance(path_or_buffer, pathlib.Path):
        df: pd.DataFrame = pd.read_csv(path_or_buffer.as_posix(), **helpers.CSV_SETTINGS)
    else:
        df: pd.DataFrame = pd.read_csv(path_or_buffer, **helpers.CSV_SETTINGS)
    df["id"] = df["dialogue_index"].astype(str) + "_" + df["line_index"].astype(str)

    return df

def barchart(df: pd.DataFrame, title:str=None):
    emotions = [c for c in df.columns.to_list() if c in COLOR_MAP.keys()]
    color_list = [COLOR_MAP.get(e, "#B3B3B3") for e in emotions]

    if title:
        st.write(title)

    st.bar_chart(
        df,
        color=color_list,
        x="id",
        y=emotions,
    )

def audio_player(path):
    if path:
        try:
            _, audio_col, _ = st.columns([3, 2, 3])
            with audio_col:
                st.audio(path)
        except:
            pass

def filters(df):
    _, col, _ = st.columns([4, 2, 4])
    # Dialogues filter
    with col:
        dialogues = df["dialogue_index"].to_list()

        min_slider = 0
        max_slider = max(dialogues)
        if min_slider == max_slider:
            attrs = {"disabled": True}
        else:
            attrs = {"min_value": 0, "max_value": max(dialogues)}
        dialogue_filtered = st.slider(
            "Dialogue Index",
            value=(0, dialogues[len(dialogues)//2 + 1]),
            **attrs
        )
        min_ = dialogue_filtered[0]
        max_ = dialogue_filtered[1]
    
    mask = (df["dialogue_index"] >= min_) & (df["dialogue_index"] <= max_)
    
    return mask


if load_data_btn or st.session_state["load"]:
    st.session_state["load"] = True

    if mode == "Inspect":
        if selection_csv_path:
            # Audio player
            audio_player(selection_audio_path)

            df = load_dataframe(selection_csv_path)
            filters_mask = filters(df)
            df = df[filters_mask]

            col1, col2 = st.columns(2)
            with col1:
                # Chart
                barchart(df)

            # Dialogues table
            with col2:
                show_columns = ["id", "speaker", "line"]
                subs_df = df[show_columns]
                st.dataframe(subs_df, hide_index=True)

    elif mode == "Compare":
        # Show two charts, one above the other. On the side, show the dialogues table
        if selection_csv_path and comparison_csv_path:
            # Audio player
            audio_player(selection_audio_path)

            selection_df = load_dataframe(selection_csv_path)

            # Filters
            filters_mask = filters(selection_df)
            selection_df = selection_df[filters_mask]

            col1, col2 = st.columns(2)
            with col1:
                # Selection chart
                barchart(selection_df, title="Selection")

                # Comparison chart
                comparison_df = load_dataframe(comparison_csv_path)
                comparison_df = comparison_df[filters_mask]
                barchart(comparison_df, title="Comparison")

            # Dialogues table
            with col2:
                st.write("### Dialogues")
                show_columns = ["id", "speaker", "line"]
                subs_df = selection_df[show_columns]
                st.dataframe(subs_df, hide_index=True, key="table", height=700)
