from praxis2.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._builtin: set[str] = set()

    def register(self, tool: Tool, *, builtin: bool = True) -> None:

        if tool.name in self._builtin and not builtin:
            return
        self._tools[tool.name] = tool
        if builtin:
            self._builtin.add(tool.name)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def anthropic_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema()}
            for t in self._tools.values()
        ]

    def openai_tools(self) -> list[dict]:

        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema(),
                },
            }
            for t in self._tools.values()
        ]
