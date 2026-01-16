def guess_rule_id(message: str) -> str:
    lowered = message.lower()
    if "while" in lowered or "for-loop" in lowered or "range()" in lowered:
        return "R4"
    if "eval" in lowered or "exec" in lowered or "import" in lowered or "dynamic" in lowered:
        return "R3"
    if "list" in lowered or "dict" in lowered or "set" in lowered or "homogeneous" in lowered:
        return "R2"
    if "index" in lowered or "slice" in lowered or "bounds" in lowered:
        return "R5"
    if "logical" in lowered or "comparison" in lowered or "boolean" in lowered or "bool" in lowered:
        return "R7"
    if "type" in lowered or "return" in lowered or "variable" in lowered:
        return "R1"
    return "R6"


class PhoenixError(Exception):
    def __init__(
        self,
        message,
        lineno=None,
        col=None,
        source=None,
        filename=None,
        hint=None,
        rule_id=None,
    ):
        super().__init__(message)
        self.message = message
        self.lineno = lineno
        self.col = col
        self.source = source
        self.filename = filename
        self.hint = hint
        self.rule_id = rule_id or guess_rule_id(message)

    def pretty(self):
        lines = []
        rule = f" [{self.rule_id}]" if self.rule_id else ""
        lines.append(f"❌ PhoenixError{rule}: {self.message}")

        if self.lineno is not None and self.source is not None:
            location = f"{self.filename}:{self.lineno}"
            if self.col is not None:
                location += f":{self.col}"

            lines.append(f"  --> {location}")
            lines.append("   |")
            lines.append(f"{self.lineno:2} | {self.source.rstrip()}")
            caret_pos = self.col if self.col is not None else 1
            lines.append(f"   | {' ' * (caret_pos - 1)}^")

        if self.hint:
            lines.append(f"  help: {self.hint}")

        return "\n".join(lines)


class PhoenixErrors(Exception):
    def __init__(self, errors):
        super().__init__("Multiple Phoenix errors")
        self.errors = errors

    def pretty(self):
        return "\n\n".join(error.pretty() for error in self.errors)
