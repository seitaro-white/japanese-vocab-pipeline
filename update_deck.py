"""
Update deck from spreadsheet
"""

# %%
# Imports
import json
import os
import re
import urllib.request

import gspread
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# %%
# Functions


def request(action, **params):
    """Generic request method"""
    return {"action": action, "params": params, "version": 6}


def invoke(action, **params):
    """Handle some of the errors you can get from Anki"""

    requestJson = json.dumps(request(action, **params)).encode("utf-8")
    response = json.load(
        urllib.request.urlopen(
            urllib.request.Request("http://localhost:8765", requestJson)
        )
    )
    if len(response) != 2:
        raise ValueError("response has an unexpected number of fields")
    if "error" not in response:
        raise KeyError("response is missing required error field")
    if "result" not in response:
        raise KeyError("response is missing required result field")
    if response["error"] == "cannot create note because it is a duplicate":
        raise ValueError("cannot create note because it is a duplicate")
    return response["result"]


def prepare_word_fields(entry: dict):
    """Prepare words fields"""
    return {
        "Front": entry["kanji"] + "<br />" + "(" + entry["reading"] + ")",
        "Back": entry["meanings"],
    }


def add_note(word: dict, deck: str, field_func: callable):
    params = {
        "note": {
            "deckName": deck,
            "modelName": "Basic (and reversed card)",
            "fields": field_func(word),
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": deck,
                    "checkChildren": False,
                    "checkAllModels": False,
                },
            },
        }
    }

    resp = invoke("addNote", **params)

    return resp


# %%
# Set up sheets
print("Loading vocabulary spreadsheet...")

gc = gspread.service_account()
sh = gc.open_by_key(os.getenv("VOCAB_SHEET_KEY"))
ws = sh.worksheet("Vocabulary")

vocab = (
    pd.DataFrame(ws.get_all_records(value_render_option="FORMULA"))
    .replace("", np.nan)
    .to_dict(orient="records")
)

# %%
#
print("Creating new notes...")
invoke("createDeck", deck="VocabularyNew")

ct = 0
for i in tqdm(vocab):
    try:
        if i["type"] == "Word":
            # If it's only one character, add (W) to indicate it's a word
            add_note(i, "VocabularyNew", prepare_word_fields)

        ct += 1
    except (KeyError, ValueError) as e:
        pass

print(f"Added {ct} new vocab notes!")

# %%
