class Plugin:
    """Base class for all FlowOS plugins."""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    requires: list = []  # pip packages required

    @classmethod
    def tool_definitions(cls) -> list:
        return []

    @classmethod
    def tool_handlers(cls) -> dict:
        return {}

    @classmethod
    def on_load(cls):
        """Called when plugin is activated."""
        pass
