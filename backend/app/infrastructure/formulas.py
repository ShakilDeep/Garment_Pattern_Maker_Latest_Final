import ast
import math
import operator
import re

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError("Missing numeric value")
    n = float(str(value).strip().replace(",", "."))
    if not math.isfinite(n) or abs(n) > 10000:
        raise ValueError("Value must be finite and within 10000")
    return n


def cell_value(sheet, coordinate, trail=()):
    if coordinate in trail or len(trail) > 50:
        raise ValueError("Circular or excessive formula dependencies")
    value = sheet[coordinate].value
    if not isinstance(value, str) or not value.startswith("="):
        return number(value)
    expression = value[1:].replace("$", "")
    if len(expression) > 200:
        raise ValueError("Formula too long")
    expression = re.sub(
        r"\b[A-Z]{1,3}[1-9][0-9]{0,5}\b",
        lambda m: str(cell_value(sheet, m[0], (*trail, coordinate))),
        expression,
    )

    def calculate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return number(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return number(OPS[type(node.op)](calculate(node.left), calculate(node.right)))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return calculate(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        raise ValueError("Unsupported formula; enter a reviewed value")

    return calculate(ast.parse(expression, mode="eval").body)
