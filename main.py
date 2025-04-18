import json
from fastapi import FastAPI, HTTPException, Query
import time
from fastapi.middleware.cors import CORSMiddleware
from schemas import *
from crud import *
from IdiomSearcher import IdiomSearcher

app = FastAPI(title="成语搜索API", description="提供多种方式搜索中文成语")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载JSON数据
try:
    with open('res/idiom.json', 'r', encoding='utf-8') as file:
        idioms = json.load(file)
except Exception as e:
    raise RuntimeError(f"Error loading JSON file: {str(e)}")
searcher = IdiomSearcher('res/idioms.json')

pinyin_index = {}
first_char_index = {}
word_index = {}
explanation_index = {}

for item in idioms:
    # 拼音索引
    pinyin_no_tones = remove_tones(item["pinyin"])
    if pinyin_no_tones not in pinyin_index:
        pinyin_index[pinyin_no_tones] = []
    pinyin_index[pinyin_no_tones].append(item)

    # 首字符索引
    if item["word"]:
        first_char = item["word"][0]
        if first_char not in first_char_index:
            first_char_index[first_char] = []
        first_char_index[first_char].append(item)

    # 词语索引
    for char in item["word"]:
        if char not in word_index:
            word_index[char] = []
        word_index[char].append(item)

    # 解释索引
    if "explanation" in item:
        for word in item["explanation"].split():
            if word not in explanation_index:
                explanation_index[word] = []
            explanation_index[word].append(item)

def search_mixed(query: str):
    if '(' or ')' not in query:
        query = '(' + query + ')'
    return searcher.search(query)

def search_by_word(query: str, exact_match: bool = False):
    if exact_match:
        return [item for item in idioms if item["word"] == query]

    return [item for item in idioms if query in item["word"]]

def search_by_explanation(query: str, exact_match: bool = False):
    if exact_match:
        return [item for item in idioms if "explanation" in item and query == item["explanation"]]

    return [item for item in idioms if "explanation" in item and query in item["explanation"]]

def search_by_regex(pattern: str):
    try:
        regex = re.compile(translate_normal_to_regex(remove_tones(pattern)))
        results = []
        # 在拼音中搜索
        for item in idioms:
            if regex.search(remove_tones(item["pinyin"])) or regex.search(item["word"]) or regex.search(item["pinyin"]):
                results.append(item)
        return results
    except re.error:
        raise HTTPException(status_code=400, detail="无效的正则表达式")

@app.get("/")
async def get_root():
    return {"message": "成语搜索API", "time": time.time()}

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    query = request.query
    search_type = request.search_type
    exact_match = request.exact_match
    limit = request.limit
    offset = request.offset

    if not query:
        raise HTTPException(status_code=400, detail="搜索词不能为空")

    if search_type == SearchType.WORD:
        results = search_by_word(query, exact_match)
    elif search_type == SearchType.EXPLANATION:
        results = search_by_explanation(query, exact_match)
    elif search_type == SearchType.REGEX:
        results = search_by_regex(query)
    elif search_type == SearchType.MIXED:
        results = search_mixed(query)
    else:
        raise HTTPException(status_code=400, detail="不支持的搜索类型")

    total = len(results)
    paginated_results = results[offset:offset + limit]

    return {
        "results": paginated_results,
        "total": total,
        "offset": offset,
        "limit": limit,
        "query": query,
        "search_type": search_type
    }

@app.get("/idiom/{word}")
async def get_idiom_detail(word: str):
    for item in idioms:
        if item["word"] == word:
            return item

    raise HTTPException(status_code=404, detail=f"未找到成语: {word}")

@app.get("/random", response_model=Dict[str, Any])
async def get_random_idiom():
    import random
    return random.choice(idioms)