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

# Pinyin initials (声母) and finals (韵母)
INITIALS = [
    'b', 'p', 'm', 'f',
    'd', 't', 'n', 'l',
    'g', 'k', 'h',
    'j', 'q', 'x',
    'zh', 'ch', 'sh', 'r',
    'z', 'c', 's',
    'y', 'w'
]

FINALS = [
    'a','e','i',
    'o','u','v',
    'ai','an','ao',
    'ei','en','er',
    'ia','ie','in',
    'io','iu','ou',
    'ua','ui','un',
    'uo','ve','vn',
    'ang','eng','ian',
    'iao','ing','ong',
    'uai','uan','van',
    'iang','iong','uang',
    'ueng'
]


class ASTNode:
    def match(self, idiom: Dict[str, Any]) -> bool:
        raise NotImplementedError

class RegexNode(ASTNode):
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    def match(self, idiom: Dict[str, Any]) -> bool:
        line = (
            f"{idiom['word']}|{' '.join(idiom['pinyin_numeric_parts'])}|"
            f"{'-'.join(map(str, idiom['strokes']))}"
        )
        return bool(self.pattern.search(line))

class SeqNode(ASTNode):
    def __init__(self, slots: List[str]):
        self.slots = slots
        # compile a single regex to parse slot DSL
        self.slot_re = re.compile(r'''
            ^(?:
                # tone+stroke, e.g. #3[10]
                \#(?P<h_p>[1-5])?\[(?P<h_s>\d+)(?:-(?P<h_s2>\d+))?\]
                |
                # tone only, e.g. #3
                \#(?P<h_only>[1-5])
                |
                # wildcard any char #
                \#
                |
                # pinyin pattern e.g. y%, ?*, abc3[5-8]
                (?P<pat>[a-z@%?*]+)(?P<t>[1-5]?)
                (?:\[(?P<s>\d+)(?:-(?P<s2>\d+))?\])?
            )$
        ''', re.VERBOSE)

    def match(self, idiom: Dict[str, Any]) -> bool:
        word = idiom['word']
        pinyin_parts = idiom['pinyin_numeric_parts']
        strokes = idiom['strokes']
        # all lengths must match
        if not (len(self.slots) == len(word) == len(pinyin_parts) == len(strokes)):
            return False
        for idx, slot in enumerate(self.slots):
            m = self.slot_re.match(slot)
            if not m:
                return False
            gd = m.groupdict()
            # handle tone+stroke or tone-only or wildcard #
            if slot.startswith('#'):
                # tone-only
                if gd['h_only']:
                    if not pinyin_parts[idx].endswith(gd['h_only']):
                        return False
                # tone+stroke
                if gd['h_p']:
                    if not pinyin_parts[idx].endswith(gd['h_p']):
                        return False
                # stroke constraint
                if gd['h_s']:
                    low = int(gd['h_s'])
                    high = int(gd['h_s2']) if gd['h_s2'] else low
                    if strokes[idx] < low or strokes[idx] > high:
                        return False
                # wildcard matches any char
                continue
            # pinyin pattern
            pat = gd['pat']
            tone = gd['t'] if gd['t'] else '[1-5]'
            s_low = gd['s']
            s_high = gd['s2']
            # build pinyin regex
            parts = []
            for c in pat:
                if c == '@':
                    parts.append('[a-z]')
                elif c == '%':
                    parts.append('[a-z]{1,4}')
                elif c == '?':
                    parts.append(f"(?:{'|'.join(INITIALS)})")
                elif c == '*':
                    parts.append(f"(?:{'|'.join(FINALS)})")
                else:
                    parts.append(c)
            regex = re.compile(rf"^{{}}{{}}{tone}$".format(''.join(parts), ''))
            if not regex.match(pinyin_parts[idx]):
                return False
            # stroke constraint if any
            if s_low:
                low = int(s_low)
                high = int(s_high) if s_high else low
                if strokes[idx] < low or strokes[idx] > high:
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

class IncludeNode(ASTNode):
    def __init__(self, items: List[str]):
        self.items = items

    def match(self, idiom: Dict[str, Any]) -> bool:
        return all(
            any(item in part for part in idiom['pinyin_numeric_parts'])
            for item in self.items
        )


class ExcludeNode(ASTNode):
    def __init__(self, items: List[str]):
        self.items = items

    def match(self, idiom: Dict[str, Any]) -> bool:
        return all(
            all(item not in part for part in idiom['pinyin_numeric_parts'])
            for item in self.items
        )

class IdiomSearcher:
    def __init__(self, json_path: str):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.idioms = json.load(f)
        # convert accented pinyin to numeric parts
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
            if dsl.startswith('INCLUDE(', i):
                tokens.append('INCLUDE')
                tokens.append('(')
                i += len('INCLUDE(')
                continue
            if dsl.startswith('EXCLUDE(', i):
                tokens.append('EXCLUDE')
                tokens.append('(')
                i += len('EXCLUDE(')
                continue
            if dsl[i].isspace():
                i += 1
                continue
            if dsl.startswith('AND', i) and (i + 3 == L or not dsl[i+3].isalpha()):
                tokens.append('AND')
                i += 3
                continue
            if dsl.startswith('OR', i) and (i + 2 == L or not dsl[i+2].isalpha()):
                tokens.append('OR')
                i += 2
                continue
            if dsl.startswith('NOT', i) and (i + 3 == L or not dsl[i+3].isalpha()):
                tokens.append('NOT')
                i += 3
                continue
            if dsl[i] in '()':
                tokens.append(dsl[i])
                i += 1
                continue
            if dsl[i] == '/':
                j = i + 1
                while j < L and not (dsl[j] == '/' and dsl[j-1] != '\\'):
                    j += 1
                if j >= L:
                    raise ValueError('Unterminated regex')
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
        if tok in ('INCLUDE', 'EXCLUDE'):
            kind = tok
            pos += 1
            if tokens[pos] != '(':
                raise ValueError(f"Expected '(' after {kind}")
            pos += 1
            items: List[str] = []
            while pos < len(tokens) and tokens[pos] != ')':
                for part in tokens[pos].split(','):  # split comma-separated items
                    part = part.strip()
                    if part:
                        items.append(part)
                pos += 1
            if pos >= len(tokens) or tokens[pos] != ')':
                raise ValueError(f"Unterminated {kind}(")
            pos += 1
            node = IncludeNode(items) if kind == 'INCLUDE' else ExcludeNode(items)
            return node, pos
        if tok == 'NOT':
            child, newpos = self._parse_factor(tokens, pos + 1)
            return NotNode(child), newpos
        if tok.startswith('/') and tok.endswith('/'):
            return RegexNode(tok[1:-1]), pos + 1
        if tok == '(':
            nxt = tokens[pos + 1]
            # sequence
            if re.match(r'^[#\[a-z@%?*]', nxt):
                end = pos + 1
                depth = 0
                while end < len(tokens):
                    if tokens[end] == '(': depth += 1
                    elif tokens[end] == ')':
                        if depth == 0:
                            break
                        depth -= 1
                    end += 1
                slots = tokens[pos+1:end]
                return SeqNode(slots), end+1
            # grouped expression
            child, newpos = self._parse(tokens, pos + 1)
            return child, newpos + 1
        raise ValueError(f"Unexpected token: {tok}")

    def search(self, dsl: str) -> List[Dict[str, Any]]:
        ast, pos = self._parse(self._tokenize(dsl))
        return [idiom for idiom in self.idioms if ast.match(idiom)]
