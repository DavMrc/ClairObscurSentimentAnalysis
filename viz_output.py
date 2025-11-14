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

# Select chapter and file
_, center, _ = st.columns([2, 6, 2])
with center:
    col1, col2 = st.columns([0.5, 0.5])
    with col1:
        classified_chapters_dir = helpers.BASE_PATH/"./output/emotions_scored/"
        classified_chapters = [f for f in classified_chapters_dir.iterdir() if f.is_dir()]
        classified_chapters.sort(key=lambda x: x.stem.split("_")[0])
        selected_chapter = st.selectbox(
            "Select chapter",
            classified_chapters,
            format_func=lambda x: x.stem
        )

    with col2:
        classified_csvs = [f for f in (classified_chapters_dir/selected_chapter).iterdir() if f.is_file()]
        classified_csvs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        most_recent_file = max(classified_csvs, key=lambda x: x.stat().st_mtime)
        
        selected_file = st.selectbox(
            "Select file",
            classified_csvs,
            format_func=lambda x: f"⭐ {x.name}" if x == most_recent_file else x.name
        )

    with st.expander("Custom file"):
        custom_file = st.file_uploader(
            "Custom csv",
            type="csv"
        )

    _, col_btn = st.columns([0.8, 0.2])
    with col_btn:
        load_data_btn = st.button("Load data")

st.divider()

# Load data, audio and plot
if load_data_btn:
    # Audio player
    if custom_file:
        pass
    else:
        _, audio_col, _ = st.columns([3, 2, 3])
        with audio_col:
            audio_path = helpers.BASE_PATH/f"./audio/2_edits/{selected_chapter.stem}.wav"
            st.audio(audio_path)

    # Chart
    if custom_file:
        df: pd.DataFrame = pd.read_csv(custom_file, **helpers.CSV_SETTINGS)
    else:
        df: pd.DataFrame = pd.read_csv(selected_file.as_posix(), **helpers.CSV_SETTINGS)
    df["id"] = df["dialogue_index"].astype(str) + "_" + df["line_index"].astype(str)

    col1, col2 = st.columns(2)
    with col1:
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
            height=500
        )
        # Enable horizontal scrolling (range slider)
        fig.update_layout(
            xaxis= {
                "rangeslider": {"visible": True},
                "type": "category",
                "range": [0, 30],
                "tickangle": -90
            },
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

    # Dialogues table
    with col2:
        show_columns = ["id", "speaker", "line"]
        subs_df = df[show_columns]
        st.dataframe(subs_df, hide_index=True)
