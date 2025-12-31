class PhoenixError(Exception):
    def __init__(self, message, lineno=None, col=None, source=None, filename=None):
        super().__init__(message)
        self.message = message
        self.lineno = lineno
        self.col = col
        self.source = source
        self.filename = filename

    def pretty(self):
        lines = []
        lines.append(f"❌ PhoenixError: {self.message}")

        if self.lineno is not None and self.source is not None:
            location = f"{self.filename}:{self.lineno}"
            if self.col is not None:
                location += f":{self.col}"

            lines.append(f"  --> {location}")
            lines.append("   |")
            lines.append(f"{self.lineno:2} | {self.source.rstrip()}")
            caret_pos = self.col if self.col is not None else 1
            lines.append(f"   | {' ' * (caret_pos - 1)}^")

        return "\n".join(lines)
