import json
from fastapi import FastAPI, HTTPException, Query
import time
from fastapi.middleware.cors import CORSMiddleware
from tokenizer import *
from schemas import *
from crud import *

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


pinyin_index = {}
first_char_index = {}
word_index = {}
explanation_index = {}

# 初始化索引
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



def search_single_term(query, item):
    """搜索单个词项"""
    tone = []
    if has_number_tone(query):
        converted = convert_number_to_tone(query)
        query, tone = converted[0], converted[1]

    # 使用正则表达式进行匹配
    try:
        pattern = translate_normal_to_regex(remove_tones(query))
        regex = re.compile(pattern)

        if regex.search(remove_tones(item["pinyin"])) or regex.search(item["word"]) or regex.search(item["pinyin"]):
            # 有声调时需要进一步过滤
            if not tone:
                return True
            for t in tone:
                if t in str(item):
                    return True
            return False
        return False
    except re.error:
        return False


def evaluate_query(node, item):
    """评估查询表达式树，判断item是否符合查询条件"""
    if isinstance(node, LeafNode):
        # 处理叶子节点的单个查询条件
        return search_single_term(node.value, item)

    elif isinstance(node, OperatorNode):
        # 处理逻辑运算符
        left_result = evaluate_query(node.left, item)

        # 短路评估以提高性能
        if node.type == "AND" and not left_result:
            return False
        if node.type == "OR" and left_result:
            return True

        right_result = evaluate_query(node.right, item)

        if node.type == "AND":
            return left_result and right_result
        else:  # OR
            return left_result or right_result

    elif isinstance(node, GroupNode):
        combined_query = ' '.join(node.items)
        return search_single_term(combined_query, item)
    return False


def search_mixed(query: str):
    # 检查查询是否包含逻辑运算符
    if "&&" in query or "||" in query or "(" in query:
        try:
            # 解析查询表达式
            query_tree = parse_query(query)

            # 评估并收集结果
            results = []
            for item in idioms:
                if evaluate_query(query_tree, item):
                    results.append(item)

            return results
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"查询表达式解析错误: {str(e)}")

    tone = []
    if has_number_tone(query):
        converted = convert_number_to_tone(query)
        query, tone = converted[0], converted[1]
    result = search_by_regex(query)

    # 声调过滤
    if not tone:
        return result

    final = []
    for item in result:
        for i in tone:
            if i in str(item):
                final.append(item)
                break
    return final

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