# Clair Obscur - Expedition 33 Sentiment Analysis
<img src="./imgs/e33-default-bkgr.jpeg" height="350">

## What is it?
In this project, I have developed a data pipeline that scrapes, prepares and estimates the emotions from audio dialogues of the videogame [Clair Obscur Expedition 33](https://www.expedition33.com/) by [Sandfall Interactive](https://www.sandfall.co/).

My goal was to associate at each line of dialogue a set of emotions, evaluating them in an automated, artificially-intelligent way. With this result, I wanted to create a dashboard to analyze the trend of emotion during a game scene.

## Quick links
- <a href="https://www.kaggle.com/datasets/davidemarcantoni/clair-obscur-expedition-33-dialogues-emotions"><img src="./imgs/kaggle.png" >Kaggle Free Dataset</a>
- <a href="https://public.tableau.com/views/ClairObscurExpedition33EmotionClassification/Dashboard"><img src="./imgs/tableau.png" >Tableau Public Free Dashboard</a>
- <img src="./imgs/youtube.png" > Walkthrough explaination (coming soon!)

## How to use
You can freely clone the repo and use the data contained in it. In particular, I recommend taking a look at the [result folder](.data/output/result/) where you can find a ready-to-use dataset (also published on [Kaggle](https://www.kaggle.com/datasets/davidemarcantoni/clair-obscur-expedition-33-dialogues-emotions))

To avoid downloading large files (WAV and MP3) you can skip them by running the following command

Linux:
```bash
$ GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/DavMrc/ClairObscurSentimentAnalysis
$ cd ClairObscurSentimentAnalysis
```

Windows:
```bash
$ set GIT_LFS_SKIP_SMUDGE=1
$ git clone https://github.com/DavMrc/ClairObscurSentimentAnalysis
$ cd ClairObscurSentimentAnalysis
```

If, at a later stage, you want to also download large files, you can install [git lfs](https://git-lfs.com/) and pull them
```bash
$ git lfs pull
```

If you want to run Python code, create a virtual environment, activate it and install the requirements
```bash
$ python -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```

## Documentation
Check out the [Wiki tab](https://github.com/DavMrc/ClairObscurSentimentAnalysis/wiki)

## Classified chapters
For technical reasons discussed in the documentation, I have classified only some chapters of the game. Specifically, only the **required** chapters were classified, all the optional ones have only been scraped.

Here is a table to summarize

| Chapter                                   | Scraped   | Classified   |
|:------------------------------------------|:-------------|:----------------|
| 0_The_Gommage                             | ✅           | ✅              |
| 1_Festival_de_lExpedition                 | ✅           | ✅              |
| 2_The_Beach                               | ✅           | ✅              |
| 3_Spring_Meadows                          | ✅           | ✅              |
| 4_Flying_Waters                           | ✅           | ✅              |
| 5_Ancient_Sanctuary                       | ✅           | ✅              |
| 6_Gestral_Village                         | ✅           | ✅              |
| 7_Esquies_Nest                            | ✅           | ✅              |
| 8_Stone_Wave_Cliffs                       | ✅           | ✅              |
| 9_Meet_Verso                              | ✅           | ✅              |
| 10_Forgotten_Battlefields                 | ✅           | ✅              |
| 11_Monocos_Station                        | ✅           | ✅              |
| 12_Old_Lumiere                            | ✅           | ✅              |
| 13_Falling_Leaves                         | ✅           | ❌              |
| 14_Visages                                | ✅           | ✅              |
| 15_Sirene                                 | ✅           | ✅              |
| 16_The_Monolith                           | ✅           | ✅              |
| 17_A_glimpse_in_the_past_Monolith_Year_49 | ✅           | ✅              |
| 18_Back_to_Lumiere                        | ✅           | ✅              |
| 19_Frozen_Hearts                          | ✅           | ❌              |
| 20_Endless_Night_Sanctuary                | ✅           | ❌              |
| 21_The_Reacher                            | ✅           | ❌              |
| 22_Sacred_River                           | ✅           | ❌              |
| 23_Sirenes_Dress                          | ✅           | ❌              |
| 24_Flying_Manor                           | ✅           | ❌              |
| 25_Painting_Workshop                      | ✅           | ❌              |
| 26_Endless_Tower                          | ✅           | ❌              |
| 27_Renoirs_Drafts                         | ✅           | ❌              |
| 28_Lets_save_Lumiere                      | ✅           | ✅              |
| 29_A_Life_to_Paint                        | ✅           | ✅              |
| 30_A_Life_to_Love                         | ✅           | ✅              |
