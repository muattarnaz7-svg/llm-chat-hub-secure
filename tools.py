"""Tools jo LLM istemal kar sakta hai: calculator aur web search."""

import ast
import json
import math
import operator

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "abs": abs,
    "round": round,
}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        return node.value
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent bohat bara hai")
        return _BIN_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCS
        and not node.keywords
    ):
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise ValueError("ye expression supported nahi hai")


def calculate(expression: str) -> str:
    """Evaluate a math expression exactly, e.g. '2 * (3 + 4)', '15% of 200' written
    as '0.15 * 200', or 'sqrt(144) + 2**5'. Supports + - * / // % ** and the functions
    sqrt, sin, cos, tan, log, log10, abs, round, plus the constants pi and e.

    Args:
        expression: The math expression to evaluate.

    Returns:
        The numeric result as text, or an error message.
    """
    try:
        tree = ast.parse(expression.replace("^", "**").strip(), mode="eval")
        result = _eval(tree)
    except ZeroDivisionError:
        return "Error: zero se divide nahi kar sakte"
    except Exception as exc:  # noqa: BLE001 - tool ko kabhi crash nahi karna
        return f"Error: {exc}"
    if isinstance(result, float):
        return f"{result:.10g}"
    return str(result)


def web_search(query: str) -> str:
    """Search the web (DuckDuckGo) for current information, news or facts the model
    may not know. Use it for recent events, prices, or anything time-sensitive.

    Args:
        query: What to search for.

    Returns:
        A list of results with title, link and a short snippet, or an error message.
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS  # purana package name

        results = DDGS().text(query, max_results=4)
    except Exception as exc:  # noqa: BLE001
        return f"Error: web search nahi ho saka ({exc})"

    if not results:
        return "Koi result nahi mila."
    lines = []
    for i, item in enumerate(results, 1):
        title = item.get("title", "")
        link = item.get("href", "")
        body = (item.get("body", "") or "")[:300]
        lines.append(f"{i}. {title}\n   {link}\n   {body}")
    return "\n".join(lines)


# Gemini seedhe in Python functions ko tools ki tarah leta hai
TOOLS = [calculate, web_search]

# Groq / OpenRouter / Mistral (OpenAI-style) ke liye tool descriptions
TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Evaluate a math expression exactly (supports + - * / // % **, "
                "sqrt, sin, cos, tan, log, log10, abs, round, pi, e). "
                "Use this for any arithmetic instead of calculating in your head."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The math expression, e.g. '2 * (3 + 4)'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current information, news or facts you may "
                "not know. Use it for recent or time-sensitive questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
]

_DISPATCH = {"calculate": calculate, "web_search": web_search}


def run_tool(name: str, arguments_json: str) -> str:
    """Model ke bheje hue tool call ko chalata hai (OpenAI-style providers ke liye)."""
    func = _DISPATCH.get(name)
    if func is None:
        return f"Error: unknown tool '{name}'"
    try:
        args = json.loads(arguments_json or "{}")
        return func(**args)
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"