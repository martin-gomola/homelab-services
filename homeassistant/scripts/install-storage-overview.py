#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install a tracked view into Home Assistant's default dashboard."
    )
    parser.add_argument("template", type=Path)
    parser.add_argument("storage", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    args = parse_args()
    template = load_json(args.template)
    storage = load_json(args.storage)

    views = storage["data"]["config"]["views"]
    overview_index = next(
        (index for index, view in enumerate(views) if view.get("path") == "overview"),
        None,
    )
    if overview_index is None:
        raise ValueError("The default dashboard has no 'overview' view")

    if views[overview_index] == template:
        print("Overview view is already up to date")
        return

    views[overview_index] = template

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = args.storage.with_name(f"{args.storage.name}.bak-{timestamp}-overview")
    shutil.copy2(args.storage, backup)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=args.storage.parent,
        prefix=f".{args.storage.name}.",
        delete=False,
    ) as handle:
        json.dump(storage, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
        temporary_path = Path(handle.name)

    os.chmod(temporary_path, args.storage.stat().st_mode)
    os.replace(temporary_path, args.storage)
    print(f"Installed Overview view and created {backup.name}")


if __name__ == "__main__":
    main()
