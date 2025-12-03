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

To avoid downloading large files (WAV and MP3) you can skip them using
```bash
$ GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/DavMrc/ClairObscurSentimentAnalysis
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
Coming soon! I promise!
