"""工具池组装(总纲 §7.3.4)。M1:名字去重 + 内建优先。
MCP 工具上权限前置审计(deny 先过滤)在 M3 接入;此处不做。"""

from praxis2.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._builtin: set[str] = set()

    def register(self, tool: Tool, *, builtin: bool = True) -> None:
        # §7.3.4 名字冲突解决:已注册为内建的名字不被后来的非内建覆盖(内建优先);
        # 其余情形(builtin↔builtin、非内建↔非内建、非内建被内建覆盖)均"后注册者生效"。
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
        """OpenAI /v1/chat/completions tools 形:
        [{type:'function', function:{name, description, parameters}}]。

        M10.5 加,跟 anthropic_tools 并存(v0.12 cleanup window 内删 anthropic_tools)。
        """
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
