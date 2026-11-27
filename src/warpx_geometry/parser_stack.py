"""Stack size that the WarpX/AMReX parser needs to evaluate an expression.

AMReX compiles a parser expression to a stack machine with a fixed stack of
AMREX_PARSER_STACK_SIZE (16) entries and aborts at startup if an expression
needs more: "amrex::Parser: AMREX_PARSER_STACK_SIZE, 16, is too small for ...".

parser_stack_size() computes that number without AMReX. It follows what AMReX
does in Src/Base/Parser: the optimizer's constant folding and its rules that
move numbers in sums and products (parser_ast_optimize, parser_ast_sort), and
the compiler's fused instructions for numbers and variables and its choice to
evaluate the deeper operand first (parser_compile_exe_size). It reproduces the
stack size of AMReX 26.08 to 26.11 exactly for the expressions this package
generates (tested on several hundred geometries); for other expressions it is
an estimate.
"""

import ast
import functools
import operator
import re

AMREX_PARSER_STACK_SIZE = 16

# enum order of parser_f1_t and parser_f2_t in AMReX_Parser_Y.H, which sets
# the order of operands of the same kind
_F1 = [
    "sqrt", "exp", "log", "log10", "sin", "cos", "tan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "abs", "floor", "ceil",
    "comp_ellint_1", "comp_ellint_2", "erf",
]  # fmt: skip
_F2 = [
    "pow", "atan2", "gt", "lt", "geq", "leq", "eq", "neq", "cmpchain", "and",
    "or", "heaviside", "jn", "yn", "min", "max", "fmod",
]  # fmt: skip
_CMP = {ast.Gt: "gt", ast.Lt: "lt", ast.GtE: "geq", ast.LtE: "leq", ast.Eq: "eq",
        ast.NotEq: "neq"}  # fmt: skip
_FOLD = {"min": min, "max": max, "gt": operator.gt, "lt": operator.lt,
         "geq": operator.ge, "leq": operator.le}  # fmt: skip
# order of the node types (parser_node_t)
_RANK = {"n": 0, "s": 1, "+": 2, "*": 4, "/": 5, "f1": 6, "f2": 7, "f3": 8}

# Nodes are tuples: ("n", value), ("s", name), ("+", l, r), ("*", l, r),
# ("/", l, r), ("f1", name, arg), ("f2", name, l, r), ("f3", cond, a, b).
# A difference a - b is a + (-1)*b, as in AMReX.


def _num(t):
    return t[0] == "n"


def _sym(t):
    return t[0] == "s"


def _leaf(t):
    return t[0] in ("n", "s")


def _is_neg(t):
    return t[0] == "*" and _num(t[1]) and t[1][1] == -1.0


def _less(a, b):
    """parser_node_compare: the order of the operands of + and *."""
    if a[0] != b[0]:
        return _RANK[a[0]] < _RANK[b[0]]
    kind = a[0]
    if kind in ("n", "s"):
        return a[1] < b[1]
    if kind in ("+", "*", "/"):
        return _less(a[2], b[2]) or (a[2] == b[2] and _less(a[1], b[1]))
    if kind == "f1":
        fa, fb = _F1.index(a[1]), _F1.index(b[1])
        return fa < fb or (fa == fb and _less(a[2], b[2]))
    if kind == "f2":
        fa, fb = _F2.index(a[1]), _F2.index(b[1])
        if fa != fb:
            return fa < fb
        return _less(a[3], b[3]) or (a[3] == b[3] and _less(a[2], b[2]))
    return False


def _add(l, r):
    """parser_ast_optimize for +: the rules that change the stack size."""
    if _less(r, l):
        l, r = r, l
    if _num(l) and _num(r):
        return ("n", l[1] + r[1])
    if _num(l) and l[1] == 0.0:
        return r
    if l == r:  # x + x
        return _mul(("n", 2.0), l)
    if l[0] == "*" and _num(l[1]) and l[2] == r:  # 3*x + x
        return _mul(("n", l[1][1] + 1.0), r)
    if r[0] == "*" and _num(r[1]) and r[2] == l:  # x + 3*x
        return _mul(("n", r[1][1] + 1.0), l)
    if l[0] == "*" and r[0] == "*" and _num(l[1]) and _num(r[1]) and l[2] == r[2]:
        return _mul(("n", l[1][1] + r[1][1]), l[2])  # 3*x + 4*x
    if _num(l) and r[0] == "+" and _num(r[1]):  # 3 + (4 + x)
        return _add(("n", l[1] + r[1][1]), r[2])
    if not _num(l) and r[0] == "+" and _num(r[1]):  # x + (3 + y)
        return _add(r[1], _add(l, r[2]))
    if l[0] == "+" and not _num(r) and _num(l[1]):  # (3 + x) + y
        return _add(l[1], _add(r, l[2]))
    return ("+", l, r)


def _mul(l, r):
    """parser_ast_optimize for *: the rules that change the stack size."""
    if _less(r, l):
        l, r = r, l
    if _num(l) and l[1] == 0.0:
        return ("n", 0.0)
    if _num(l) and l[1] == 1.0:
        return r
    if _num(l) and _num(r):
        return ("n", l[1] * r[1])
    if _num(l) and r[0] == "*" and _num(r[1]):  # 3 * (4*x)
        return _mul(("n", l[1] * r[1][1]), r[2])
    if l[0] == "*" and _num(l[1]) and r[0] == "*" and _num(r[1]):  # (3*x) * (4*y)
        return _mul(("n", l[1][1] * r[1][1]), _mul(l[2], r[2]))
    if not _leaf(l) and l == r:  # f * f
        return ("f2", "pow", l, ("n", 2.0))
    if not _num(l) and r[0] == "*" and _num(r[1]):  # x * (3*y)
        return _mul(r[1], _mul(l, r[2]))
    if _num(l) and r[0] == "+" and _num(r[1]):  # 3 * (4 + x)
        return _add(("n", l[1] * r[1][1]), _mul(l, r[2]))
    if _num(l) and r[0] == "+" and r[1][0] == "*" and _num(r[1][1]):  # 3*(4*x + y)
        return _add(_mul(("n", l[1] * r[1][1][1]), r[1][2]), _mul(l, r[2]))
    if _num(l) and r[0] == "+" and r[2][0] == "*" and _num(r[2][1]):  # 3*(x + 4*y)
        return _add(_mul(("n", l[1] * r[2][1][1]), r[2][2]), _mul(l, r[1]))
    if l[0] == "*" and _num(l[1]):  # (3*x) * y
        return _mul(l[1], _mul(r, l[2]))
    return ("*", l, r)


def _div(l, r):
    """parser_ast_optimize for /: the rules that change the stack size."""
    if _num(l) and l[1] == 0.0:
        return ("n", 0.0)
    if _num(l) and _num(r):
        return ("n", l[1] / r[1])
    if l == r:
        return ("n", 1.0)
    if l[0] == "*" and _num(l[1]) and _num(r):  # (3*x) / 4
        return ("*", ("n", l[1][1] / r[1]), l[2])
    if _num(r):  # x / 4
        return _mul(("n", 1.0 / r[1]), l)
    if r[0] == "*" and _num(r[1]):  # x / (4*y)
        return _mul(("n", 1.0 / r[1][1]), _div(l, r[2]))
    return ("/", l, r)


def _f2(name, l, r):
    if _num(l) and _num(r) and name in _FOLD:
        return ("n", float(_FOLD[name](l[1], r[1])))
    return ("f2", name, l, r)


def _tree(node):
    """Return the AMReX parser tree of a Python syntax tree."""
    if isinstance(node, ast.Expression):
        return _tree(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return ("n", float(node.value))
    if isinstance(node, ast.Name):
        return ("s", node.id)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
        t = _tree(node.operand)
        return _mul(("n", -1.0), t) if isinstance(node.op, ast.USub) else t
    if isinstance(node, ast.BinOp):
        l, r = _tree(node.left), _tree(node.right)
        op = type(node.op)
        if op is ast.Add:
            return _add(l, r)
        if op is ast.Sub:
            return _add(l, _mul(("n", -1.0), r))
        if op is ast.Mult:
            return _mul(l, r)
        if op is ast.Div:
            return _div(l, r)
        if op is ast.Pow:
            return _f2("pow", l, r)
    if (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and type(node.ops[0]) in _CMP
    ):
        return _f2(
            _CMP[type(node.ops[0])], _tree(node.left), _tree(node.comparators[0])
        )
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and not node.keywords
    ):
        name, args = node.func.id, [_tree(a) for a in node.args]
        if name in _F1 and len(args) == 1:
            return ("f1", name, args[0])
        if name in _F2 and len(args) == 2:
            return _f2(name, *args)
        if name == "where" and len(args) == 3:  # if(c, a, b)
            return ("f3", *args)
    raise ValueError("unsupported expression")


def _stack(t) -> int:
    """parser_compile_exe_size: the largest stack size while evaluating t."""
    depth_memo, need_memo = {}, {}

    def depth(t):  # parser_ast_depth
        key = id(t)
        if key not in depth_memo:
            if _leaf(t):
                d = 1
            elif t[0] == "f1":
                d = depth(t[2]) + 1
            elif t[0] == "f2":
                d = max(depth(t[2]), depth(t[3])) + 1
            elif t[0] == "f3":
                d = max(depth(t[1]), depth(t[2]), depth(t[3])) + 1
            else:
                d = max(depth(t[1]), depth(t[2])) + 1
            depth_memo[key] = (d, t)  # t keeps id(t) unique
        return depth_memo[key][0]

    def both(a, b):  # both operands on the stack, the deeper one first
        if depth(a) < depth(b):
            a, b = b, a
        return max(need(a), 1 + need(b))

    def need(t):
        key = id(t)
        if key in need_memo:
            return need_memo[key][0]
        kind = t[0]
        if _leaf(t):
            n = 1
        elif kind == "+":
            l, r = t[1], t[2]
            if _leaf(l):
                fused = _sym(r) or (
                    r[0] == "*"
                    and _num(r[1])
                    and _sym(r[2])
                    and (_num(l) or _is_neg(r))
                )
                n = 1 if fused else need(r[2] if _is_neg(r) else r)
            elif _is_neg(l) and _sym(l[2]):
                n = need(r)
            elif _is_neg(r) and _sym(r[2]):
                n = need(l)
            elif _is_neg(r):
                n = both(l, r[2])
            elif _is_neg(l):
                n = both(l[2], r)
            else:
                n = both(l, r)
        elif kind == "*":
            l, r = t[1], t[2]
            if _leaf(l):
                n = 1 if _sym(r) else need(r)
            elif l == r:
                n = need(l)
            else:
                n = both(l, r)
        elif kind == "/":
            l, r = t[1], t[2]
            if _leaf(l):
                n = 1 if _sym(r) else need(r)
            elif _sym(r):
                n = need(l)
            else:
                n = both(l, r)
        elif kind == "f1":
            n = 1 if _sym(t[2]) else need(t[2])
        elif kind == "f2":
            name, l, r = t[1], t[2], t[3]
            if name == "pow" and _num(r) and (r[1] == 0.5 or float(r[1]).is_integer()):
                n = 1 if _sym(l) else need(l)
            elif (_sym(l) and _leaf(r)) or (_num(l) and _sym(r)):
                n = 1
            else:
                n = both(l, r)
        else:  # if(c, a, b): c is taken off the stack before a or b runs
            n = max(need(t[1]), need(t[2]), need(t[3]))
        need_memo[key] = (n, t)
        return n

    return need(t)


@functools.lru_cache(maxsize=16)  # str(geometry) may be called repeatedly
def parser_stack_size(expr: str) -> int | None:
    """Return the stack size the WarpX/AMReX parser needs for expr.

    Returns None if expr has syntax that this function does not handle, such
    as ``^``, ``and``, user-defined functions or nesting too deep for Python's
    parser. WarpX aborts at startup if the result exceeds
    AMREX_PARSER_STACK_SIZE. It takes about 1.5 s per MB of expression.
    """
    if "^" in expr:  # pow with another precedence in Python
        return None
    try:
        source = ast.parse(re.sub(r"\bif\(", "where(", expr), mode="eval")
        return _stack(_tree(source))
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None
