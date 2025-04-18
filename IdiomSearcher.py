import re
import json
from typing import List, Dict, Any, Tuple

# Mapping of accented pinyin vowels to (base vowel, tone number)
ACCENTED_MAP = {
    'ā': ('a', '1'), 'á': ('a', '2'), 'ǎ': ('a', '3'), 'à': ('a', '4'),
    'ē': ('e', '1'), 'é': ('e', '2'), 'ě': ('e', '3'), 'è': ('e', '4'),
    'ī': ('i', '1'), 'í': ('i', '2'), 'ǐ': ('i', '3'), 'ì': ('i', '4'),
    'ō': ('o', '1'), 'ó': ('o', '2'), 'ǒ': ('o', '3'), 'ò': ('o', '4'),
    'ū': ('u', '1'), 'ú': ('u', '2'), 'ǔ': ('u', '3'), 'ù': ('u', '4'),
    'ǖ': ('ü', '1'), 'ǘ': ('ü', '2'), 'ǚ': ('ü', '3'), 'ǜ': ('ü', '4')
}

class ASTNode:
    pass

class SeqNode(ASTNode):
    def __init__(self, slots: List[str]):
        self.slots = slots

    def match(self, idiom: Dict[str, Any]) -> bool:
        word = idiom['word']
        pinyin_parts = idiom.get('pinyin_numeric_parts', [])
        strokes = idiom['strokes']
        # Ensure same length
        if len(self.slots) != len(word) or len(pinyin_parts) != len(word):
            return False
        for idx, slot in enumerate(self.slots):
            if slot == '#':
                continue
            # Combined #[n]
            m_hash_stroke = re.match(r"^#\[(\d+)\]$", slot)
            # Stroke-only [n]
            m_stroke_only = re.match(r"^\[(\d+)\]$", slot)
            # Any-tone-only slot #3
            m_hash_tone = re.match(r"^#([1-5])$", slot)
            # PinyinPattern + optional tone + optional stroke
            m_pinyin = re.match(r"^([a-z@%]+)([1-5]?)(?:\[(\d+)\])?$", slot)

            if m_hash_stroke:
                req = int(m_hash_stroke.group(1))
                if strokes[idx] != req:
                    return False
            elif m_stroke_only:
                req = int(m_stroke_only.group(1))
                if strokes[idx] != req:
                    return False
            elif m_hash_tone:
                req_tone = m_hash_tone.group(1)
                # ensure pinyin numeric part ends with this tone
                if not pinyin_parts[idx].endswith(req_tone):
                    return False
            elif m_pinyin:
                pat, tone, stroke_str = m_pinyin.groups()
                # build regex for pinyin: '@' -> any letter, '%' -> 1-4 letters
                regex_parts = []
                for c in pat:
                    if c == '@':
                        regex_parts.append('[a-z]')
                    elif c == '%':
                        regex_parts.append('[a-z]{1,4}')
                    else:
                        regex_parts.append(c)
                regex_pat = ''.join(regex_parts)
                tone_pattern = tone if tone else '[1-5]'
                full_pattern = re.compile(f"^{regex_pat}{tone_pattern}$")
                if not full_pattern.match(pinyin_parts[idx]):
                    return False
                if stroke_str:
                    if strokes[idx] != int(stroke_str):
                        return False
            else:
                return False
        return True

class AndNode(ASTNode):
    def __init__(self, children: List[ASTNode]):
        self.children = children
    def match(self, idiom: Dict[str, Any]) -> bool:
        return all(child.match(idiom) for child in self.children)

class OrNode(ASTNode):
    def __init__(self, children: List[ASTNode]):
        self.children = children
    def match(self, idiom: Dict[str, Any]) -> bool:
        return any(child.match(idiom) for child in self.children)

class IdiomSearcher:
    def __init__(self, json_path: str):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.idioms: List[Dict[str, Any]] = json.load(f)
        # Convert diacritic pinyin vowels to numeric parts
        for idiom in self.idioms:
            parts = idiom['pinyin'].split()
            numeric = []
            for token in parts:
                tone = '5'
                letters = []
                for ch in token:
                    if ch in ACCENTED_MAP:
                        base, t = ACCENTED_MAP[ch]
                        letters.append(base)
                        tone = t
                    else:
                        letters.append(ch)
                base_token = ''.join(letters)
                numeric.append(base_token + tone)
            idiom['pinyin_numeric_parts'] = numeric

    def _tokenize(self, dsl: str) -> List[str]:
        spaced = dsl.replace('(', ' ( ').replace(')', ' ) ')
        return spaced.split()

    def _parse(self, tokens: List[str], pos: int = 0) -> Tuple[ASTNode, int]:
        node, pos = self._parse_term(tokens, pos)
        while pos < len(tokens) and tokens[pos] == 'OR':
            pos += 1
            right, pos = self._parse_term(tokens, pos)
            node = OrNode([node, right])
        return node, pos

    def _parse_term(self, tokens: List[str], pos: int) -> Tuple[ASTNode, int]:
        node, pos = self._parse_factor(tokens, pos)
        while pos < len(tokens) and tokens[pos] == 'AND':
            pos += 1
            right, pos = self._parse_factor(tokens, pos)
            node = AndNode([node, right])
        return node, pos

    def _parse_factor(self, tokens: List[str], pos: int) -> Tuple[ASTNode, int]:
        token = tokens[pos]
        if token == '(':
            nxt = tokens[pos+1]
            if re.match(r'^[#\[a-z@%]', nxt):
                # sequence
                end = pos + 1
                depth = 0
                while end < len(tokens):
                    if tokens[end] == '(':
                        depth += 1
                    elif tokens[end] == ')':
                        if depth == 0:
                            break
                        depth -= 1
                    end += 1
                slots = tokens[pos+1:end]
                return SeqNode(slots), end+1
            else:
                node, newpos = self._parse(tokens, pos+1)
                return node, newpos+1
        raise ValueError(f"Unexpected token: {token}")

    def _compile_ast(self, dsl: str) -> ASTNode:
        tokens = self._tokenize(dsl)
        ast, pos = self._parse(tokens)
        if pos != len(tokens):
            raise ValueError('Extra tokens')
        return ast

    def search(self, dsl: str) -> List[Dict[str, Any]]:
        ast = self._compile_ast(dsl)
        return [idiom for idiom in self.idioms if ast.match(idiom)]

# if __name__ == '__main__':
#     searcher = IdiomSearcher('res/idioms.json')
#     examples = ['(#3 # # #)', '(y% # # #)']
#     for dsl in examples:
#         print(f"DSL: {dsl}")
#         for idiom in searcher.search(dsl):
#             print("  ", idiom['word'], idiom['pinyin_numeric_parts'], idiom['strokes'])
#         print()
