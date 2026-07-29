from __future__ import annotations


STAMP_TOOLS = ("stamp_star", "stamp_heart", "stamp_check", "stamp_x", "stamp_exclamation")


def is_stamp_tool(tool: str) -> bool:
    return tool in STAMP_TOOLS


def stamp_name_from_tool(tool: str) -> str:
    return tool.removeprefix("stamp_") if is_stamp_tool(tool) else "star"

