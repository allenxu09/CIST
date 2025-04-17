import re
# 拼音声调映射
TONE_MARKS = {
    'a': ['a', 'ā', 'á', 'ǎ', 'à'],
    'e': ['e', 'ē', 'é', 'ě', 'è'],
    'i': ['i', 'ī', 'í', 'ǐ', 'ì'],
    'o': ['o', 'ō', 'ó', 'ǒ', 'ò'],
    'u': ['u', 'ū', 'ú', 'ǔ', 'ù'],
    'v': ['ü', 'ǖ', 'ǘ', 'ǚ', 'ǜ'],  # v用作ü
}

# 将数字声调转换为带声调拼音
def convert_number_to_tone(pinyin_with_number):
    result = []
    sylla = []
    i = 0
    while i < len(pinyin_with_number):
        # 查找拼音边界
        j = i
        while j < len(pinyin_with_number) and not pinyin_with_number[j].isdigit():
            j += 1

        syllable = pinyin_with_number[i:j]
        # 检查是否有声调数字
        if j < len(pinyin_with_number) and pinyin_with_number[j].isdigit():
            tone = int(pinyin_with_number[j])
            if 0 <= tone <= 4:  # 有效声调范围
                # 查找应该声调的元音
                for vowel in "aoeiuv":
                    if vowel in syllable:
                        vowel_pos = syllable.rfind(vowel)
                        if vowel in TONE_MARKS:
                            syllable = (syllable[:vowel_pos] +
                                        TONE_MARKS[vowel][tone] +
                                        syllable[vowel_pos + 1:])
                            sylla.append(syllable[vowel_pos - 1:])
                            break

            i = j + 1

        else:
            i = j
        result.append(syllable)

    return [''.join(result),sylla]

# 检查是否含有数字声调
def has_number_tone(text):
    # 检查是否为拼音声调标记（数字1-4紧跟在拼音字母后面）
    pattern = re.compile(r'[a-zA-Z][1-4]')
    return bool(pattern.search(text))

# 是否是拼音字符（包括数字标记）
def is_pinyin_char(char):
    return char.isalpha() or char in 'āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü' or char.isdigit()

def translate_normal_to_regex(pattern: str):
    pattern = pattern.replace('"', '\\b')
    pattern = pattern.replace('#', '\\b\\S{1,6}\\b')
    pattern = pattern.replace('@', '\\S')
    pattern = pattern.replace('%', '\\S{1,4}')
    pattern = pattern.replace(' ', '\\s+')
    return pattern

def remove_tones(pinyin):
    tone_map = str.maketrans("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü", "aaaaeeeeiiiioooouuuuvvvvv")
    return pinyin.translate(tone_map)
