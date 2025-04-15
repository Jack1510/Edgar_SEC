
import matplotlib.pyplot as plt
import pandas as pd

def plot_sentiment_over_time(data):
    print("Sentiment plot function called (placeholder)")
    fig, ax = plt.subplots()
    if isinstance(data, pd.DataFrame) and 'sentiment' in data.columns:
        ax.plot(data['sentiment'])
    return fig

def plot_word_frequency(word_counts, top_n=20):
    print("Word frequency plot function called (placeholder)")
    fig, ax = plt.subplots()
    if word_counts:
        ax.bar(word_counts.keys(), word_counts.values())
    return fig

