from __future__ import annotations

import json

from bookmarks_mcp.models import Library


def parse(text: str) -> Library:
    # If the source payload omits ``position``, derive sibling-local positions
    # from the order items appear in the ``folders`` / ``bookmarks`` arrays so
    # the imported library preserves source order instead of collapsing to id.
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return Library.model_validate_json(text)

    if isinstance(raw, dict):
        counters: dict[object, int] = {}
        for key in ("folders", "bookmarks"):
            items = raw.get(key)
            if not isinstance(items, list):
                continue
            parent_field = "parent_id" if key == "folders" else "folder_id"
            for item in items:
                if not isinstance(item, dict) or "position" in item:
                    continue
                parent = item.get(parent_field)
                # dict keys must be hashable — None is hashable, so this works.
                item["position"] = counters.get(parent, 0)
                counters[parent] = counters.get(parent, 0) + 1
    return Library.model_validate(raw)


def serialize(library: Library) -> str:
    return library.model_dump_json(indent=2) + "\n"
