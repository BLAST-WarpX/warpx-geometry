"""Stack size that the WarpX/AMReX parser needs to evaluate an expression.

AMReX compiles a parser expression to a stack machine with a fixed stack of
AMREX_PARSER_STACK_SIZE entries (16 by default) and aborts at startup if an
expression needs more: "amrex::Parser: AMREX_PARSER_STACK_SIZE, 16, is too
small for ...". For an AMReX built with -DAMREX_PARSER_STACK_SIZE=N, set
warpx_geometry.parser_stack.AMREX_PARSER_STACK_SIZE = N.

parser_stack_size() computes that number without AMReX. It follows what AMReX
does in Src/Base/Parser: its grammar (amrex_parser.y, amrex_parser.l), the
optimizer's constant folding and its rules that move numbers in sums and
products (parser_ast_optimize, parser_ast_sort), and the compiler's fused
instructions for numbers and variables and its choice to evaluate the deeper
operand first (parser_compile_exe_size). It counts a function of two
variables or numbers, such as max(x, 0), as AMReX up to 26.10 does; AMReX
26.11 needs one entry less there, so the result is an upper bound for it. It
reproduces the stack size of AMReX 26.08 to 26.11 exactly for the expressions
this package generates (tested on several thousand geometries), where the two
versions agree; for other expressions it is an estimate. Nesting is not
limited.
"""

import functools
import math
import operator
import re
import sys
import threading

AMREX_PARSER_STACK_SIZE = 16

# sys.setrecursionlimit is process wide
_RECURSION_LIMIT_LOCK = threading.Lock()

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
_F1_NAMES = {**{f: f for f in _F1}, "fabs": "abs"}
_F2_NAMES = {
    f: f for f in ("atan2", "pow", "heaviside", "jn", "yn", "min", "max", "fmod")
}
# values of functions of numbers, which AMReX folds; a NaN stands in where
# the value does not matter for the stack size
_FOLD1 = {"sqrt": math.sqrt, "exp": math.exp, "log": math.log, "log10": math.log10,
          "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin,
          "acos": math.acos, "atan": math.atan, "sinh": math.sinh, "cosh": math.cosh,
          "tanh": math.tanh, "asinh": math.asinh, "acosh": math.acosh,
          "atanh": math.atanh, "abs": abs, "floor": math.floor, "ceil": math.ceil,
          "erf": math.erf}  # fmt: skip
_FOLD2 = {"min": min, "max": max, "gt": operator.gt, "lt": operator.lt,
          "geq": operator.ge, "leq": operator.le, "eq": operator.eq,
          "neq": operator.ne, "and": lambda a, b: bool(a) and bool(b),
          "or": lambda a, b: bool(a) or bool(b), "pow": math.pow,
          "atan2": math.atan2, "fmod": math.fmod,
          "heaviside": lambda a, b: 0.0 if a < 0 else (b if a == 0 else 1.0),
}  # fmt: skip
# order of the node types (parser_node_t)
_RANK = {"n": 0, "s": 1, "+": 2, "*": 4, "/": 5, "f1": 6, "f2": 7, "f3": 8}

# Nodes are tuples: ("n", value), ("s", name), ("+", l, r), ("*", l, r),
# ("/", l, r), ("f1", name, arg), ("f2", name, l, r), ("f3", cond, a, b).
# A difference a - b is a + (-1)*b, as in AMReX.


class _Unsupported(ValueError):
    """Syntax that parser_stack_size does not handle (or not valid)."""


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


def _quotient(a: float, b: float) -> float:
    """a / b with IEEE results for b == 0, as in AMReX."""
    if b != 0.0:
        return a / b
    if a == 0.0 or math.isnan(a):
        return math.nan
    return math.copysign(math.inf, a) * math.copysign(1.0, b)


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
    if _num(l) and r[0] == "/" and _num(r[1]):  # 3 * (4/x)
        return ("/", ("n", l[1] * r[1][1]), r[2])
    if l[0] == "*" and _num(l[1]) and r[0] == "*" and _num(r[1]):  # (3*x) * (4*y)
        return _mul(("n", l[1][1] * r[1][1]), _mul(l[2], r[2]))
    if not _leaf(l) and l == r:  # f * f
        return _f2("pow", l, ("n", 2.0))
    if not _num(l) and r[0] == "*" and _num(r[1]):  # x * (3*y)
        return _mul(r[1], _mul(l, r[2]))
    if not _num(l) and r[0] == "/" and _num(r[1]):  # x * (3/y)
        return _mul(r[1], _div(l, r[2]))
    if _num(l) and r[0] == "+" and _num(r[1]):  # 3 * (4 + x)
        return _add(("n", l[1] * r[1][1]), _mul(l, r[2]))
    if _num(l) and r[0] == "+" and r[1][0] == "*" and _num(r[1][1]):  # 3*(4*x + y)
        return _add(_mul(("n", l[1] * r[1][1][1]), r[1][2]), _mul(l, r[2]))
    if _num(l) and r[0] == "+" and r[2][0] == "*" and _num(r[2][1]):  # 3*(x + 4*y)
        return _add(_mul(("n", l[1] * r[2][1][1]), r[2][2]), _mul(l, r[1]))
    if l[0] == "*" and _num(l[1]):  # (3*x) * y
        return _mul(l[1], _mul(r, l[2]))
    if l[0] == "/" and _num(l[1]):  # (3/x) * y
        return _mul(l[1], _div(r, l[2]))
    if l[0] == "/" and r[0] == "/":  # (x/y) * (a/b)
        return _div(_mul(l[1], r[1]), _mul(l[2], r[2]))
    return ("*", l, r)


def _div(l, r):
    """parser_ast_optimize for /: the rules that change the stack size."""
    if _num(l) and l[1] == 0.0:
        return ("n", 0.0)
    if _num(l) and _num(r):
        return ("n", _quotient(l[1], r[1]))
    if l == r:
        return ("n", 1.0)
    lnum = l[0] in ("*", "/") and _num(l[1])  # 4*x or 4/x
    rnum = r[0] in ("*", "/") and _num(r[1])
    if l[0] == "*" and _num(l[1]) and _num(r):  # (4*x) / 3
        return ("*", ("n", _quotient(l[1][1], r[1])), l[2])
    if l[0] == "/" and _num(l[1]) and _num(r):  # (4/x) / 3
        return _div(("n", _quotient(l[1][1], r[1])), l[2])
    if lnum and rnum:  # (4*x)/(3*y), (4/x)/(3*y), (4*x)/(3/y), (4/x)/(3/y)
        c = ("n", _quotient(l[1][1], r[1][1]))
        if l[0] == "*" and r[0] == "*":
            return _mul(c, _div(l[2], r[2]))
        if l[0] == "/" and r[0] == "*":
            return _div(c, _mul(l[2], r[2]))
        if l[0] == "*":
            return _mul(c, _mul(l[2], r[2]))
        return _mul(c, _div(r[2], l[2]))
    if _num(r):  # x / 4
        return _mul(("n", _quotient(1.0, r[1])), l)
    if r[0] == "*" and _num(r[1]):  # x / (4*y)
        return _mul(("n", _quotient(1.0, r[1][1])), _div(l, r[2]))
    if r[0] == "/" and _num(r[1]):  # x / (4/y)
        return _mul(("n", _quotient(1.0, r[1][1])), _mul(l, r[2]))
    if l[0] == "/" and r[0] == "/":  # (x/y) / (a/b)
        return _div(_mul(l[1], r[2]), _mul(r[1], l[2]))
    if r[0] == "/":  # x / (y/z)
        return _div(_mul(l, r[2]), r[1])
    if l[0] == "/":  # (x/y) / z
        return _div(l[1], _mul(r, l[2]))
    if r[0] == "f2" and r[1] == "pow" and _num(r[3]):  # f / pow(x, n)
        return _mul(l, _f2("pow", r[2], ("n", -r[3][1])))
    return ("/", l, r)


def _neg(t):
    return _mul(("n", -1.0), t)


def _fold(f, *args) -> float:
    try:
        return float(f(*args)) if f else math.nan
    except (ArithmeticError, ValueError):
        return math.nan


def _f1(name, a):
    if _num(a):
        return ("n", _fold(_FOLD1.get(name), a[1]))
    return ("f1", name, a)


def _f2(name, l, r):
    """parser_ast_optimize for functions of two arguments (some rules)."""
    if _num(l) and _num(r):
        return ("n", _fold(_FOLD2.get(name), l[1], r[1]))
    if name == "pow" and _num(r):
        if r[1] == 0.0:
            return ("n", 1.0)
        if r[1] == 1.0:
            return l
        if r[1] == -1.0:
            return ("/", ("n", 1.0), l)
        if (
            l[0] == "f2"
            and l[1] == "pow"
            and _num(l[3])
            and float(r[1]).is_integer()
            and float(l[3][1]).is_integer()
        ):  # pow(pow(x, m), n)
            return _f2("pow", l[2], ("n", l[3][1] * r[1]))
    return ("f2", name, l, r)


# the tokens of amrex_parser.l
_TOKEN = re.compile(
    r"(?P<space>[ \t]+|\\\n|//[^\n]*)"
    r"|(?P<num>[0-9]+\.[0-9]*(?:[Ee][-+]?[0-9]+)?|\.?[0-9]+(?:[Ee][-+]?[0-9]+)?)"
    r"|(?P<name>[a-zA-Z_][a-zA-Z0-9_.]*)"
    r"|(?P<op>\*\*|\^|>=|<=|==|!=|[-+*/=,<>;()])"
)
# binary operators and their precedence (amrex_parser.y); all comparisons are
# one level, and a chain of them, such as a < b < c, is not handled here
_BINARY = {"or": 1, "and": 2, "<": 3, ">": 3, "<=": 3, ">=": 3, "==": 3, "!=": 3,
           "+": 4, "-": 4, "*": 5, "/": 5}  # fmt: skip
_COMPARISON = {"<": "lt", ">": "gt", "<=": "leq", ">=": "geq", "==": "eq", "!=": "neq"}


def _tokens(expr: str) -> list[str]:
    tokens, pos = [], 0
    text = expr.rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if m is None:
            raise _Unsupported(f"unsupported character {text[pos]!r}")
        if m.lastgroup != "space":
            tokens.append(m.group())
        pos = m.end()
    return tokens


class _Parser:
    """Precedence climbing over the grammar of amrex_parser.y.

    It recurses only into parentheses, function arguments, unary signs and
    powers, so sys.setrecursionlimit is raised for deeply nested input.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self, expected=None):
        tok = self.peek()
        if tok is None or (expected is not None and tok != expected):
            raise _Unsupported(f"expected {expected!r}, got {tok!r}")
        self.pos += 1
        return tok

    def parse(self):
        t = self.binary(1)
        if self.peek() is not None:  # e.g., ';' lists or '=' assignments
            raise _Unsupported(f"unsupported token {self.peek()!r}")
        return t

    def binary(self, min_prec):
        left = self.unary()
        left_is_comparison = False
        while True:
            op = self.peek()
            prec = _BINARY.get(op)
            if prec is None or prec < min_prec:
                return left
            self.pos += 1
            right = self.binary(prec + 1)
            if op in _COMPARISON:
                if left_is_comparison:
                    raise _Unsupported("comparison chain")
                left = _f2(_COMPARISON[op], left, right)
                left_is_comparison = True
                continue
            left_is_comparison = False
            if op == "+":
                left = _add(left, right)
            elif op == "-":
                left = _add(left, _neg(right))
            elif op == "*":
                left = _mul(left, right)
            elif op == "/":
                left = _div(left, right)
            else:  # and, or
                left = ("f2", op, left, right)

    def unary(self):
        tok = self.peek()
        if tok == "-":
            self.pos += 1
            return _neg(self.unary())
        if tok == "+":
            self.pos += 1
            return self.unary()
        base = self.primary()
        if self.peek() in ("**", "^"):  # right associative, binds before a sign
            self.pos += 1
            return _f2("pow", base, self.unary())
        return base

    def primary(self):
        tok = self.take()
        if tok == "(":
            t = self.binary(1)
            self.take(")")
            return t
        if tok[0].isdigit() or tok[0] == ".":
            return ("n", float(tok))
        if tok[0].isalpha() or tok[0] == "_":
            if self.peek() != "(":
                if tok in _F1_NAMES or tok in _F2_NAMES or tok in ("if", "and", "or"):
                    raise _Unsupported(f"{tok} without arguments")
                return ("s", tok)
            self.take("(")
            args = [self.binary(1)]
            while self.peek() == ",":
                self.pos += 1
                args.append(self.binary(1))
            self.take(")")
            if tok in _F1_NAMES and len(args) == 1:
                return _f1(_F1_NAMES[tok], args[0])
            if tok in _F2_NAMES and len(args) == 2:
                return _f2(_F2_NAMES[tok], *args)
            if tok == "if" and len(args) == 3:
                return ("f3", *args)
            raise _Unsupported(f"function {tok} with {len(args)} arguments")
        raise _Unsupported(f"unexpected token {tok!r}")


def _children(t):
    kind = t[0]
    if kind in ("n", "s"):
        return ()
    if kind == "f1":
        return (t[2],)
    if kind == "f2":
        return (t[2], t[3])
    if kind == "f3":
        return (t[1], t[2], t[3])
    return (t[1], t[2])


def _stack(root) -> int:
    """parser_compile_exe_size: the largest stack size while evaluating root.

    Bottom-up without recursion; depth is parser_ast_depth, and need is the
    stack size of a node, as in parser_compile_exe_size.
    """
    depth, need = {}, {}

    def both(a, b):  # both operands on the stack, the deeper one first
        if depth[id(a)] < depth[id(b)]:
            a, b = b, a
        return max(need[id(a)], 1 + need[id(b)])

    todo = [(root, False)]
    while todo:
        t, ready = todo.pop()
        key = id(t)
        if key in need:
            continue
        kids = _children(t)
        if not ready and kids:
            todo.append((t, True))
            todo.extend((k, False) for k in kids if id(k) not in need)
            continue
        depth[key] = 1 + max((depth[id(k)] for k in kids), default=0)
        kind = t[0]
        if not kids:
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
                n = 1 if fused else need[id(r[2] if _is_neg(r) else r)]
            elif _is_neg(l) and _sym(l[2]):
                n = need[id(r)]
            elif _is_neg(r) and _sym(r[2]):
                n = need[id(l)]
            elif _is_neg(r):
                n = both(l, r[2])
            elif _is_neg(l):
                n = both(l[2], r)
            else:
                n = both(l, r)
        elif kind == "*":
            l, r = t[1], t[2]
            if _leaf(l):
                n = 1 if _sym(r) else need[id(r)]
            elif l == r:
                n = need[id(l)]
            else:
                n = both(l, r)
        elif kind == "/":
            l, r = t[1], t[2]
            if _leaf(l):
                n = 1 if _sym(r) else need[id(r)]
            elif _sym(r):
                n = need[id(l)]
            else:
                n = both(l, r)
        elif kind == "f1":
            n = 1 if _sym(t[2]) else need[id(t[2])]
        elif kind == "f2":
            name, l, r = t[1], t[2], t[3]
            if name == "pow" and _num(r) and (r[1] == 0.5 or float(r[1]).is_integer()):
                n = 1 if _sym(l) else need[id(l)]
            else:
                # AMReX 26.11 fuses a function of two variables or numbers
                # (one entry); earlier versions push both (two), as counted
                # here, which bounds both
                n = both(l, r)
        else:  # if(c, a, b): c is taken off the stack before a or b runs
            n = max(need[id(k)] for k in kids)
        need[key] = n
    return need[id(root)]


@functools.lru_cache(maxsize=16)  # str(geometry) may be called repeatedly
def parser_stack_size(expr: str) -> int | None:
    """Return the stack size the WarpX/AMReX parser needs for expr.

    Returns None if expr has syntax that this function does not handle, such
    as user-defined functions, a comparison chain (a < b < c), several
    statements or local variables. WarpX aborts at startup if the result
    exceeds AMREX_PARSER_STACK_SIZE. It takes about 0.8 s per MB of expression.
    """
    try:
        tokens = _tokens(expr)
        if not tokens:
            return None
        # Each level of nesting costs a few Python frames in the parser, and
        # comparing deep trees (==) recurses as well.
        nesting = tokens.count("(")
        with _RECURSION_LIMIT_LOCK:
            limit = sys.getrecursionlimit()
            sys.setrecursionlimit(max(limit, 4 * nesting + 1000))
            try:
                return _stack(_Parser(tokens).parse())
            finally:
                sys.setrecursionlimit(limit)
    except (ValueError, ArithmeticError, RecursionError, MemoryError):
        return None
