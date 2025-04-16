class Node:
    """表达式树的基类"""
    pass


class OperatorNode(Node):
    """运算符节点（AND/OR）"""

    def __init__(self, op_type, left=None, right=None):
        self.type = op_type  # 'AND' 或 'OR'
        self.left = left
        self.right = right

    def __repr__(self):
        return f"({self.left} {self.type} {self.right})"


class LeafNode(Node):
    """叶子节点（具体的查询项）"""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return self.value


# MODIFIED: GroupNode representation
class GroupNode(Node):
    """节点表示由 () 包裹的项序列"""
    def __init__(self, items):
        self.items = items

    def __repr__(self):
        # Format as "item1 item2 ..." WITHOUT parentheses
        return ' '.join(self.items)


def parse_query(query: str) -> Node:
    """解析查询表达式，支持AND(&&)、OR(||)和括号优先级"""
    tokens = tokenize(query)
    if not tokens:
        return None
    return parse_expression(tokens)[0]


def tokenize(query: str) -> list:
    """将查询字符串分解为标记"""
    i, tokens = 0, []
    query = query.strip()

    while i < len(query):
        char = query[i]
        if query[i:i + 2] == "&&":
            tokens.append("&&")
            i += 2
        elif query[i:i + 2] == "||":
            tokens.append("||")
            i += 2
        elif char in "()":
            tokens.append(char)
            i += 1
        elif char.isspace():
            i += 1
        else:
            start = i
            while (
                i < len(query)
                and not query[i].isspace()
                and query[i] not in "()"
                and query[i : i + 2] not in ["&&", "||"]
            ):
                i += 1
            tokens.append(query[start:i])

    return tokens


def parse_expression(tokens, pos=0):
    """解析表达式"""
    if pos >= len(tokens) or tokens[pos] == ')':
        return None, pos

    left, pos = parse_term(tokens, pos)
    if left is None:
        return None, pos

    while pos < len(tokens):
        if tokens[pos] == ")":
            break

        op_type = None
        operator_token = None

        if tokens[pos] in ["&&", "||"]:
            operator_token = tokens[pos]
            op_type = "AND" if operator_token == "&&" else "OR"
            pos += 1
        elif tokens[pos] != ")":
            if tokens[pos] not in ["&&", "||"]:
                op_type = "AND"  # 默认使用 AND
            else:
                raise ValueError(f"无效的查询结构：在位置 {pos} 处遇到意外的标记 '{tokens[pos]}'")

        else:
            break

        if op_type:
            # 下一个应当是右操作数
            if pos >= len(tokens) or tokens[pos] == ')':
                raise ValueError(
                    f"无效的查询结构：在位置 {pos-1} 的运算符 '{operator_token or '隐式AND'}' 后缺少操作数"
                )

            right, pos = parse_term(tokens, pos)
            if right is None:
                raise ValueError(f"无效的查询结构：在位置 {pos} 处期望一个查询项或组")

            left = OperatorNode(op_type, left, right)
        else:
            break

    return left, pos


def parse_term(tokens, pos):
    """解析项（可能是括号内的表达式、组或单个项）"""
    if pos >= len(tokens):
        return None, pos

    if tokens[pos] == "(":
        pos += 1  # 跳过 '('
        items = []
        start_group_pos = pos
        # 收集所有在括号内的标记直到匹配 ')'
        while pos < len(tokens) and tokens[pos] != ")":
            if tokens[pos] in ["&&", "||"]:
                raise ValueError(f"无效的查询结构：不允许在 () 组内使用运算符 '{tokens[pos]}'")
            items.append(tokens[pos])
            pos += 1

        if pos < len(tokens) and tokens[pos] == ")":
            pos += 1  # 跳过 ')'
            if not items:
                raise ValueError("空的 () 组是不允许的")
            return GroupNode(items), pos
        else:
            raise ValueError("缺少右括号 ')'")

    elif tokens[pos] in ["&&", "||", ")"]:
        raise ValueError(f"无效的查询结构：在位置 {pos} 处遇到意外的标记 '{tokens[pos]}'")
    else:
        # 普通叶子
        return LeafNode(tokens[pos]), pos + 1