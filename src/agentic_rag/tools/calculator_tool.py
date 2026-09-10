"""Safe arithmetic evaluator; never evaluates arbitrary Python."""
import ast
import operator
from .base_tool import ToolResult, failure, success

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}

def calculate(expression: str) -> ToolResult:
    try:
        tree = ast.parse(expression, mode="eval")
        value = _eval(tree.body)
        if not isinstance(value, (int, float)):
            return failure("Expression did not produce a number")
        return success(value)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        return failure(f"Invalid arithmetic expression: {exc}")

def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool): return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY: return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN: return _BIN[type(node.op)](_eval(node.left), _eval(node.right))
    raise ValueError("Only numeric arithmetic is allowed")

class CalculatorTool:
    def run(self, expression: str) -> ToolResult: return calculate(expression)

