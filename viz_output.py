import pathlib
import streamlit as st
import pandas as pd
import plotly.express as px
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
    classified_chapters.sort(key=lambda x: x.stem.split("_")[0])
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

def plotly_barchart(df: pd.DataFrame, title:str=None):
    emotions = [c for c in df.columns.to_list() if c in COLOR_MAP.keys()]
    color_list = [COLOR_MAP.get(e, "#B3B3B3") for e in emotions]

    df_melt = df.melt(
        id_vars="id",
        value_vars=emotions,
        var_name="emotion",
        value_name="value"
    )
    # Create Plotly bar chart
    fig = px.bar(
        df_melt,
        x="id",
        y="value",
        color="emotion",
        color_discrete_sequence=color_list,
        title=title,
        height=500
    )
    # Enable horizontal scrolling (range slider)
    fig.update_layout(
        xaxis= {
            "rangeslider": {"visible": True},
            "type": "category",
            "range": [-0.5, 30],
            "tickangle": -90
        },
        height=500
    )

    return fig

def audio_player(path):
    if path:
        try:
            _, audio_col, _ = st.columns([3, 2, 3])
            with audio_col:
                st.audio(path)
        except:
            pass


if load_data_btn or st.session_state["load"]:
    st.session_state["load"] = True

    if mode == "Inspect":
        if selection_csv_path:
            # Audio player
            audio_player(selection_audio_path)

            col1, col2 = st.columns(2)
            with col1:
                # Chart
                df = load_dataframe(selection_csv_path)
                fig = plotly_barchart(df)
                st.plotly_chart(fig, use_container_width=True)

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

            col1, col2 = st.columns(2)
            with col1:
                for m, path in zip(["Selection", "Comparison"], [selection_csv_path, comparison_csv_path]):
                    # Chart
                    df = load_dataframe(path)
                    fig = plotly_barchart(df, title=m)
                    st.plotly_chart(fig, use_container_width=True, key=f"{m}_chart")

            # Dialogues table
            with col2:
                st.write("### Dialogues")
                show_columns = ["id", "speaker", "line"]
                subs_df = df[show_columns]
                st.dataframe(subs_df, hide_index=True, key=f"{m}_table", height=700)
