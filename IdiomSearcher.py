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

# Initials and Finals for pinyin segmentation
INITIALS = [
    'b','p','m','f','d','t','n','l','g','k','h',
    'j','q','x','zh','ch','sh','r','z','c','s','y','w'
]
FINALS = [
    'a','o','e','i','u','ai','ei','ui','ao','ou','iu','ie','üe','er',
    'an','en','in','un','ian','uan','üan','ang','eng','ing','ong'
]

class ASTNode:
    pass

class RegexNode(ASTNode):
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    def match(self, idiom: Dict[str, Any]) -> bool:
        line = f"{idiom['word']}|{' '.join(idiom['pinyin_numeric_parts'])}|{'-'.join(map(str, idiom['strokes']))}"
        return bool(self.pattern.search(line))

class SeqNode(ASTNode):
    def __init__(self, slots: List[str]):
        self.slots = slots

    def match(self, idiom: Dict[str, Any]) -> bool:
        word = idiom['word']
        pinyin_parts = idiom.get('pinyin_numeric_parts', [])
        strokes = idiom['strokes']

        if len(self.slots) != len(word) or len(pinyin_parts) != len(word):
            return False

        for idx, slot in enumerate(self.slots):
            if slot == '#':
                continue

            m_hash_stroke = re.match(r"^#\[(\d+)\]$", slot)
            m_stroke_only = re.match(r"^\[(\d+)\]$", slot)
            m_hash_tone = re.match(r"^#([1-5])$", slot)
            m_pinyin = re.match(r"^([a-z@%?*]+)([1-5]?)(?:\[(\d+)\])?$", slot)

            if m_hash_stroke:
                if strokes[idx] != int(m_hash_stroke.group(1)):
                    return False

            elif m_stroke_only:
                if strokes[idx] != int(m_stroke_only.group(1)):
                    return False

            elif m_hash_tone:
                if not pinyin_parts[idx].endswith(m_hash_tone.group(1)):
                    return False

            elif m_pinyin:
                pat, tone, stroke_str = m_pinyin.groups()
                regex_parts = []
                for c in pat:
                    if c == '@':
                        regex_parts.append('[a-z]')
                    elif c == '%':
                        regex_parts.append('[a-z]{1,4}')
                    elif c == '?':
                        regex_parts.append(f"(?:{'|'.join(INITIALS)})")
                    elif c == '*':
                        regex_parts.append(f"(?:{'|'.join(FINALS)})")
                    else:
                        regex_parts.append(c)
                regex_body = ''.join(regex_parts)
                tone_pattern = tone if tone else '[1-5]'
                full_pattern = f"^{regex_body}{tone_pattern}$"
                if not re.match(full_pattern, pinyin_parts[idx]):
                    return False
                if stroke_str and strokes[idx] != int(stroke_str):
                    return False

            else:
                return False

        return True

class NotNode(ASTNode):
    def __init__(self, child: ASTNode):
        self.child = child

    def match(self, idiom: Dict[str, Any]) -> bool:
        return not self.child.match(idiom)

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
                numeric.append(''.join(letters) + tone)
            idiom['pinyin_numeric_parts'] = numeric

    def _tokenize(self, dsl: str) -> List[str]:
        tokens = []
        i, L = 0, len(dsl)
        while i < L:
            c = dsl[i]
            if c.isspace():
                i += 1
                continue
            if dsl.startswith('AND', i) and (i+3 == L or not dsl[i+3].isalpha()):
                tokens.append('AND')
                i += 3
                continue
            if dsl.startswith('OR', i) and (i+2 == L or not dsl[i+2].isalpha()):
                tokens.append('OR')
                i += 2
                continue
            if dsl.startswith('NOT', i) and (i+3 == L or not dsl[i+3].isalpha()):
                tokens.append('NOT')
                i += 3
                continue
            if c in '()':
                tokens.append(c)
                i += 1
                continue
            if c == '/':
                j = i + 1
                while j < L and not (dsl[j] == '/' and dsl[j-1] != '\\'):
                    j += 1
                if j >= L:
                    raise ValueError('Unterminated regex literal')
                tokens.append(dsl[i:j+1])
                i = j + 1
                continue
            j = i
            while j < L and not dsl[j].isspace() and dsl[j] not in '()':
                j += 1
            tokens.append(dsl[i:j])
            i = j
        return tokens

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
        tok = tokens[pos]
        if tok == 'NOT':
            child, newpos = self._parse_factor(tokens, pos + 1)
            return NotNode(child), newpos
        if tok.startswith('/') and tok.endswith('/'):
            return RegexNode(tok[1:-1]), pos + 1
        if tok == '(':
            nxt = tokens[pos+1]
            if re.match(r'^[#\[a-z@%?*]', nxt):
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
                return SeqNode(slots), end + 1
            else:
                node, newpos = self._parse(tokens, pos + 1)
                return node, newpos + 1
        raise ValueError(f"Unexpected token: {tok}")

    def _compile_ast(self, dsl: str) -> ASTNode:
        tokens = self._tokenize(dsl)
        ast, pos = self._parse(tokens)
        if pos != len(tokens):
            raise ValueError('Extra tokens after parsing')
        return ast

    def search(self, dsl: str) -> List[Dict[str, Any]]:
        ast = self._compile_ast(dsl)
        return [idiom for idiom in self.idioms if ast.match(idiom)]


# searcher = IdiomSearcher('res/idioms.json')
# for idiom in searcher.search('(b* #2 da4 #4)'):
#     print(idiom['word'], idiom['pinyin_numeric_parts'], idiom['strokes'])
