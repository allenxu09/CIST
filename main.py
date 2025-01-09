import json
import re
from fastapi import FastAPI, HTTPException
import time
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load JSON data
try:
    with open('res/idiom.json', 'r', encoding='utf-8') as file:
        idioms = json.load(file)
except Exception as e:
    raise RuntimeError(f"Error loading JSON file: {str(e)}")

# Function to remove tones from pinyin
def remove_tones(pinyin):
    tone_map = str.maketrans("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü", "aaaaeeeeiiiioooouuuuvvvvv")
    return pinyin.translate(tone_map)

def search_items(expr: str):
    try:
        # Remove tones from input expression
        expr_no_tones = remove_tones(expr)
        pattern = re.compile(expr_no_tones)

        filtered_items = [
            item["word"]
            for item in idioms
            if pattern.search(remove_tones(item["pinyin"]))
        ]
        return filtered_items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def match(expr: str):
    # Convert the input expression to a regex
    # "*" is replaced with a match for a pinyin word of 2 to 6 characters (syllables)
    result = expr
    result = result.replace('"', '\\b')  # Replace " with word boundaries
    result = result.replace('*', '\\S{1,6}')  # Replace * with a non-whitespace syllable of length 2 to 6
    result = result.replace(' ', '\\s+')  # Ensure spaces between syllables are handled correctly
    result = result.replace('?', '\\S')
    return result

@app.post("/")
async def getRoot():
    # Return current time
    return {"result": time.time()}

@app.post("/get/{expr}")
async def getResults(expr: str):
    # Pass the expression through the match function
    regex_pattern = match(expr)
    results = search_items(regex_pattern)
    return {"results": results}