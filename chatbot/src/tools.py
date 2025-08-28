import ast
import pytz
from datetime import datetime
from duckduckgo_search import DDGS

# ---------- calc ----------
_ALLOWED = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.FloorDiv, ast.USub, ast.UAdd,
}

def _safe_eval(node):
    if type(node) not in _ALLOWED:
        raise ValueError("Unsupported expression")
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.UnaryOp):
        val = _safe_eval(node.operand)
        if isinstance(node.op, ast.UAdd): return +val
        if isinstance(node.op, ast.USub): return -val
        raise ValueError("Bad unary op")
    if isinstance(node, ast.BinOp):
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        if isinstance(node.op, ast.Add): return left + right
        if isinstance(node.op, ast.Sub): return left - right
        if isinstance(node.op, ast.Mult): return left * right
        if isinstance(node.op, ast.Div): return left / right
        if isinstance(node.op, ast.Mod): return left % right
        if isinstance(node.op, ast.Pow): return left ** right
        if isinstance(node.op, ast.FloorDiv): return left // right
        raise ValueError("Bad binary op")
    raise ValueError("Unsupported node")

def calc(expression: str) -> str:
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_safe_eval(tree))
    except Exception as e:
        return f"error: {e}"

# ---------- time_in_timezone ----------
# helpful aliases so city names “just work”
CITY_TZ = {
    "mumbai": "Asia/Kolkata",
    "bombay": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata",
    "chennai": "Asia/Kolkata",
    "pune": "Asia/Kolkata",
    "hyderabad": "Asia/Kolkata",
    "india": "Asia/Kolkata",
}

def _normalize_tz(tz: str) -> str:
    if not tz:
        return tz
    lower = tz.strip().lower()
    if lower in CITY_TZ:
        return CITY_TZ[lower]
    return tz

def time_in_timezone(tz: str) -> str:
    try:
        tz = _normalize_tz(tz)
        if tz not in pytz.all_timezones:
            return "error: unknown timezone (use IANA tz like 'Asia/Kolkata')"
        now = datetime.now(pytz.timezone(tz))
        return now.strftime("%Y-%m-%d %H:%M:%S %Z%z")
    except Exception as e:
        return f"error: {e}"

# ---------- web_search ----------
def web_search(query: str, k: int = 3) -> str:
    try:
        k = int(k) if k is not None else 3
        if k < 1: k = 1
        if k > 10: k = 10
    except Exception:
        k = 3
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=k))
        if not results:
            return "no results"
        lines = []
        for i, r in enumerate(results, 1):
            title = (r.get("title") or "").strip()
            href = (r.get("href") or "").strip()
            snippet = (r.get("body") or "").strip()
            lines.append(f"{i}. {title}\n   {href}\n   {snippet}")
        return "\n".join(lines)
    except Exception as e:
        return f"error: {e}"

# ---------- Tool specs ----------
TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "calc",
            "description": "Safely evaluate a math expression",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "time_in_timezone",
            "description": "Get current local time in a given IANA timezone (accepts common Indian city names like 'Mumbai' too).",
            "parameters": {
                "type": "object",
                "properties": {"tz": {"type": "string"}},
                "required": ["tz"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Run a quick web search and summarize top hits",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer"}
                },
                "required": ["query"]
            }
        }
    }
]

TOOL_FUNCS = {
    "calc": lambda **kw: calc(**kw),
    "time_in_timezone": lambda **kw: time_in_timezone(**kw),
    "web_search": lambda **kw: web_search(**kw),
}
