import json


def get_tool_call_id(tool_call: dict) -> str:
    """Return the provider tool-call id used to attach the matching ToolMessage."""

    return tool_call.get("id") or tool_call.get("tool_call_id") or ""


def get_tool_call_name(tool_call: dict) -> str:
    """Return the bound tool/function name requested by the model."""

    return tool_call.get("name") or ""


def get_tool_call_args(tool_call: dict) -> dict:
    """Return parsed tool arguments, accepting dict args or JSON-string args."""

    args = tool_call.get("args") or {}

    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {"query": args}

    return args if isinstance(args, dict) else {}


def merge_tool_call_chunk(current: dict, chunk: dict) -> dict:
    """Merge one streamed tool-call chunk into the accumulated tool-call state."""

    current["id"] += chunk.get("id") or ""
    current["name"] += chunk.get("name") or ""

    chunk_args = chunk.get("args")
    if isinstance(chunk_args, str):
        current["args"] += chunk_args
    elif isinstance(chunk_args, dict):
        current["parsed_args"] = chunk_args

    return current


def parse_tool_call_args(raw_args) -> dict:
    """Parse raw streamed tool args into a dict once the stream is complete."""

    if isinstance(raw_args, dict):
        return raw_args

    if isinstance(raw_args, str) and raw_args:
        try:
            parsed = json.loads(raw_args)
        except json.JSONDecodeError:
            return {"query": raw_args}

        return parsed if isinstance(parsed, dict) else {}

    return {}


def normalize_streamed_tool_calls(
    tool_calls_by_index: dict[int, dict],
) -> list[dict]:
    """Convert accumulated streamed tool-call chunks into normal tool-call dicts."""

    tool_calls = []

    for index in sorted(tool_calls_by_index):
        tool_call = tool_calls_by_index[index]
        name = tool_call.get("name") or ""

        if not name:
            continue

        args = tool_call.get("parsed_args") or parse_tool_call_args(
            tool_call.get("args")
        )
        tool_calls.append({
            "id": tool_call.get("id") or f"tool_call_{index}",
            "name": name,
            "args": args,
        })

    return tool_calls
