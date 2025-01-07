""" Temp script for pushing existing kanji up to gsheet """

# %%
# Imports

import os
import re

import gspread
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from jisho_api.kanji import Kanji
from jisho_api.word import Word
from tqdm import tqdm

load_dotenv()


# %%
# Set up sheets
print("Loading vocabulary spreadsheet...")

gc = gspread.service_account()
sh = gc.open_by_key(os.getenv("VOCAB_SHEET_KEY"))
ws = sh.worksheet("Vocabulary")

# %%
# Pull current vocab
vocab = (pd.DataFrame(ws.get_all_records(value_render_option="FORMULA"))
        .replace("", np.nan)
        .to_dict(orient="records"))


# %%
# Lookup meanings

def wrap_hyperlink(url:str, label:str) -> str:
    """Wrap URL to a google sheets hyperlink formula"""

    hyperlink = f'=HYPERLINK("{url}", "{label}")'
    return hyperlink


def lookup_word(word:str):
    """Lookup a word and return the relevant fields"""

    def get_item(obj, idx:int):
        """Handle empty lists instead of throwing an IndexError"""

        try:
            return obj[idx]
        except IndexError:
            return None

    r = Word.request(word)


    # Let's assume it's going to be the top result
    result = r.data[0]

    return {
        "reading": get_item(result.japanese, 0).reading,
        "level": get_item(result.jlpt, 0),
        "parts_of_speech": ", ".join(get_item(result.senses, 0).parts_of_speech),
        "meanings": ", ".join(get_item(result.senses, 0).english_definitions),
        "link": wrap_hyperlink(f"https://jisho.org/word/{word}", word)
    }

def lookup_character(char:str):
    """Lookup a kanji character and return the relevant fields"""
    r = Kanji.request(char)

    # Let's assume it's going to be the top result
    result = r.data
    if on := result.main_readings.on:
        on = ", ".join(on)
    if kun := result.main_readings.kun:
        kun = ", ".join(kun)

    return {
        "on": on,
        "kun": kun,
        "meanings": ", ".join(result.main_meanings),
        "link": wrap_hyperlink(f"https://jisho.org/search/{char}%20%23kanji", char)
    }

print("Looking up new 漢字...")
new_vocab = []
for i in tqdm(vocab):
    if all([pd.isnull(i[k]) for k in ["kun", "on", "reading", "meanings"]]):
        kanji = i["kanji"]
        type_ = i["type"]

        if type_ == "Kanji":
            # Temporary arrangement - will refine later
            entry = i | lookup_character(kanji)
        elif type_ == "Word":
            entry = i | lookup_word(kanji)
        else:
            print(f"No type specified for {kanji}")

        new_vocab.append(entry)

    else:
        new_vocab.append(i)



# %%
print("Updating spreadsheet...")
new_vocab_df = pd.DataFrame(new_vocab).fillna("-")

ws.update(
    [new_vocab_df.columns.values.tolist()] +
    new_vocab_df.values.tolist(),
    value_input_option="user_entered")
# %%
