"""
Papa's Save Toolkit
===================

Fan-made local save editor / inspector for:

- JackSmith
- Papa's Freezeria Deluxe
- Papa's Pizzeria Deluxe
- Papa's Mocharia Deluxe

Features:
- JSON + SOL support
- Automatic format detection
- Automatic timestamped backups
- Backup restore
- Nested save browser
- Key/value search
- Type-safe editing
- Pending-change viewer
- SOL -> JSON inspection exports
- Automatic rollback if writing fails
- Multiple save detection
- Generic Deluxe-game architecture
- Easy future game additions

IMPORTANT:
Always keep backups.

SOL support requires PyAMF-compatible libraries.
"""

from __future__ import annotations

import json
import shutil
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


# ============================================================
# OPTIONAL SOL SUPPORT
# ============================================================

SOL_AVAILABLE = False
SOL_IMPORT_ERROR: Exception | None = None

try:
    from pyamf.sol import SolReader, SolWriter

    SOL_AVAILABLE = True

except Exception as exc:
    SolReader = None
    SolWriter = None
    SOL_IMPORT_ERROR = exc


# ============================================================
# APPLICATION INFO
# ============================================================

APP_NAME = "Papa's Save Toolkit"
VERSION = "3.0.0"

BACKUP_FOLDER = "PapaSaveToolkit_Backups"
EXPORT_FOLDER = "PapaSaveToolkit_Exports"


# ============================================================
# GAME PROFILE
# ============================================================

@dataclass(frozen=True)
class GameProfile:
    identifier: str
    name: str
    extensions: tuple[str, ...]
    preferred_format: str
    description: str = ""


GAMES: dict[str, GameProfile] = {
    "1": GameProfile(
        identifier="jacksmith",
        name="JackSmith",
        extensions=(".json", ".sol"),
        preferred_format="auto",
        description="Blacksmithing adventure / crafting game",
    ),

    "2": GameProfile(
        identifier="freezeria_dx",
        name="Papa's Freezeria Deluxe",
        extensions=(".sol", ".json"),
        preferred_format="auto",
        description="Freezeria Deluxe save editor",
    ),

    "3": GameProfile(
        identifier="pizzeria_dx",
        name="Papa's Pizzeria Deluxe",
        extensions=(".sol", ".json"),
        preferred_format="auto",
        description="Pizzeria Deluxe save editor",
    ),

    "4": GameProfile(
        identifier="mocharia_dx",
        name="Papa's Mocharia Deluxe",
        extensions=(".sol", ".json"),
        preferred_format="auto",
        description="Mocharia Deluxe save editor",
    ),
}


# ============================================================
# TERMINAL UI
# ============================================================

def clear_screen() -> None:
    """Clear the terminal on Windows/Linux/macOS."""

    import os

    os.system("cls" if os.name == "nt" else "clear")


def print_header(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def print_logo() -> None:
    print(
        rf"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║                   PAPA'S SAVE TOOLKIT v{VERSION:<9}                 ║
║                                                                      ║
║       💰 Saves • ⭐ Progress • 🏆 Unlocks • 🔬 Inspector             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    )


def pause() -> None:
    input("\nPress Enter to continue...")


def yes_no(
    prompt: str,
    default: bool = False,
) -> bool:

    suffix = "[Y/n]" if default else "[y/N]"

    answer = input(f"{prompt} {suffix}: ").strip().lower()

    if not answer:
        return default

    return answer in {"y", "yes"}


# ============================================================
# PATH HANDLING
# ============================================================

def normalize_path(raw: str) -> Path:
    """
    Removes surrounding quotes and expands ~.
    """

    raw = raw.strip()

    if (
        len(raw) >= 2
        and raw[0] == raw[-1]
        and raw[0] in {"'", '"'}
    ):
        raw = raw[1:-1]

    return Path(raw).expanduser()


def detect_files(
    location: Path,
    extensions: tuple[str, ...],
) -> list[Path]:

    if location.is_file():
        return [location]

    if not location.is_dir():
        return []

    matches: list[Path] = []

    for extension in extensions:

        matches.extend(
            file
            for file in location.rglob(f"*{extension}")
            if BACKUP_FOLDER not in file.parts
            and EXPORT_FOLDER not in file.parts
        )

    return sorted(
        set(matches),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def choose_file(files: list[Path]) -> Path | None:

    if not files:
        print("❌ No compatible save files found.")
        return None

    if len(files) == 1:
        print(f"\n✅ Detected save:\n{files[0]}")
        return files[0]

    print_header("SAVE FILES FOUND")

    max_files = min(len(files), 50)

    for index, file in enumerate(
        files[:max_files],
        start=1,
    ):

        modified = datetime.fromtimestamp(
            file.stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M:%S")

        print(
            f"{index:>3}. {file.name}"
            f"\n     {file.parent}"
            f"\n     Modified: {modified}"
        )

    if len(files) > max_files:
        print(
            f"\nShowing {max_files} of "
            f"{len(files)} files."
        )

    while True:

        selection = input(
            "\nSelect save number or Q to cancel: "
        ).strip()

        if selection.lower() == "q":
            return None

        try:
            index = int(selection) - 1

            if 0 <= index < max_files:
                return files[index]

        except ValueError:
            pass

        print("❌ Invalid selection.")


# ============================================================
# SAVE FORMAT DETECTION
# ============================================================

def determine_format(path: Path) -> str:

    extension = path.suffix.lower()

    if extension == ".json":
        return "json"

    if extension == ".sol":
        return "sol"

    raise ValueError(
        f"Unsupported save format: {extension}"
    )


# ============================================================
# BACKUP SYSTEM
# ============================================================

def backup_directory(save_path: Path) -> Path:

    directory = save_path.parent / BACKUP_FOLDER

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def create_backup(save_path: Path) -> Path:

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    destination = backup_directory(save_path)

    backup = destination / (
        f"{save_path.stem}"
        f"_{timestamp}"
        f"{save_path.suffix}.backup"
    )

    shutil.copy2(
        save_path,
        backup,
    )

    print(f"🛡️ Backup created:\n{backup}")

    return backup


def restore_backup(save_path: Path) -> bool:

    directory = backup_directory(save_path)

    backups = sorted(
        directory.glob(
            f"{save_path.stem}_*"
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not backups:
        print("❌ No backups exist for this save.")
        return False

    print_header("RESTORE BACKUP")

    for index, backup in enumerate(
        backups[:30],
        start=1,
    ):

        modified = datetime.fromtimestamp(
            backup.stat().st_mtime
        ).strftime("%Y-%m-%d %H:%M:%S")

        size = backup.stat().st_size

        print(
            f"{index:>2}. "
            f"{backup.name}"
            f" [{size:,} bytes]"
            f" — {modified}"
        )

    selection = input(
        "\nChoose backup or Q to cancel: "
    ).strip()

    if selection.lower() == "q":
        return False

    try:
        chosen = backups[int(selection) - 1]

    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        return False

    print()
    print(f"Backup:")
    print(chosen)
    print()
    print("Will overwrite:")
    print(save_path)

    if not yes_no(
        "\nContinue with restore?"
    ):
        return False

    # Safety backup before restoring.

    create_backup(save_path)

    shutil.copy2(
        chosen,
        save_path,
    )

    print("\n✅ Backup restored.")

    return True


# ============================================================
# JSON SUPPORT
# ============================================================

def load_json(path: Path) -> Any:

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def save_json(
    path: Path,
    data: Any,
) -> None:

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    try:

        with temporary.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )

        temporary.replace(path)

    finally:

        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


# ============================================================
# SOL SUPPORT
# ============================================================

def require_sol_support() -> None:

    if SOL_AVAILABLE:
        return

    message = (
        "\nSOL support is unavailable.\n\n"
        "Install a PyAMF-compatible package before "
        "editing .sol saves.\n"
    )

    if SOL_IMPORT_ERROR:
        message += (
            "\nPython reported:\n"
            f"{SOL_IMPORT_ERROR}\n"
        )

    raise RuntimeError(message)


def load_sol(path: Path) -> Any:

    require_sol_support()

    with path.open(
        "rb",
    ) as file:

        sol_object = SolReader(file).read()

    if hasattr(sol_object, "body"):
        return sol_object.body

    return sol_object


def save_sol(
    path: Path,
    data: Any,
) -> None:

    require_sol_support()

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    try:

        with temporary.open(
            "wb",
        ) as file:

            SolWriter(file).write(data)

        temporary.replace(path)

    finally:

        if temporary.exists():

            try:
                temporary.unlink()

            except OSError:
                pass


# ============================================================
# GENERIC SAVE LOADING
# ============================================================

def load_save(path: Path) -> tuple[str, Any]:

    save_format = determine_format(path)

    if save_format == "json":
        return save_format, load_json(path)

    if save_format == "sol":
        return save_format, load_sol(path)

    raise ValueError(
        f"Unsupported format: {save_format}"
    )


def write_save(
    path: Path,
    save_format: str,
    data: Any,
) -> None:

    if save_format == "json":
        save_json(path, data)
        return

    if save_format == "sol":
        save_sol(path, data)
        return

    raise ValueError(
        f"Unsupported save format: {save_format}"
    )


# ============================================================
# DATA DISPLAY
# ============================================================

def friendly_type(value: Any) -> str:

    if value is None:
        return "null"

    if isinstance(value, bool):
        return "bool"

    if isinstance(value, int):
        return "int"

    if isinstance(value, float):
        return "float"

    if isinstance(value, dict):
        return f"dict:{len(value)}"

    if isinstance(value, list):
        return f"list:{len(value)}"

    return type(value).__name__


def summarize(
    value: Any,
    limit: int = 65,
) -> str:

    try:
        representation = repr(value)
    except Exception:
        representation = "<unable to display>"

    representation = (
        representation
        .replace("\n", " ")
        .replace("\r", " ")
    )

    if len(representation) > limit:

        representation = (
            representation[: limit - 3]
            + "..."
        )

    return representation


# ============================================================
# TYPE-SAFE INPUT CONVERSION
# ============================================================

def parse_value(
    raw: str,
    old_value: Any,
) -> Any:

    if isinstance(old_value, bool):

        value = raw.strip().lower()

        if value in {
            "true",
            "yes",
            "y",
            "1",
            "on",
        }:
            return True

        if value in {
            "false",
            "no",
            "n",
            "0",
            "off",
        }:
            return False

        raise ValueError(
            "Expected true/false."
        )

    if (
        isinstance(old_value, int)
        and not isinstance(old_value, bool)
    ):
        return int(raw)

    if isinstance(old_value, float):
        return float(raw)

    if isinstance(old_value, dict):

        result = json.loads(raw)

        if not isinstance(result, dict):
            raise ValueError(
                "Expected a JSON object."
            )

        return result

    if isinstance(old_value, list):

        result = json.loads(raw)

        if not isinstance(result, list):
            raise ValueError(
                "Expected a JSON array."
            )

        return result

    if old_value is None:

        try:
            return json.loads(raw)

        except json.JSONDecodeError:
            return raw

    return raw


# ============================================================
# CHANGE TRACKING
# ============================================================

def compare_data(
    original: Any,
    modified: Any,
    path: str = "root",
) -> list[str]:

    changes: list[str] = []

    if (
        isinstance(original, dict)
        and isinstance(modified, dict)
    ):

        all_keys = (
            set(original.keys())
            | set(modified.keys())
        )

        for key in sorted(
            all_keys,
            key=lambda value: str(value).lower(),
        ):

            child_path = (
                f"{path}.{key}"
            )

            if key not in original:

                changes.append(
                    f"+ {child_path} = "
                    f"{modified[key]!r}"
                )

            elif key not in modified:

                changes.append(
                    f"- {child_path} = "
                    f"{original[key]!r}"
                )

            else:

                changes.extend(
                    compare_data(
                        original[key],
                        modified[key],
                        child_path,
                    )
                )

        return changes

    if (
        isinstance(original, list)
        and isinstance(modified, list)
    ):

        maximum = max(
            len(original),
            len(modified),
        )

        for index in range(maximum):

            child_path = (
                f"{path}[{index}]"
            )

            if index >= len(original):

                changes.append(
                    f"+ {child_path} = "
                    f"{modified[index]!r}"
                )

            elif index >= len(modified):

                changes.append(
                    f"- {child_path} = "
                    f"{original[index]!r}"
                )

            else:

                changes.extend(
                    compare_data(
                        original[index],
                        modified[index],
                        child_path,
                    )
                )

        return changes

    if original != modified:

        changes.append(
            f"~ {path}: "
            f"{original!r} -> "
            f"{modified!r}"
        )

    return changes


# ============================================================
# SEARCH ENGINE
# ============================================================

def search_data(
    value: Any,
    query: str,
    path: str = "root",
    results: list[
        tuple[str, Any]
    ] | None = None,
) -> list[tuple[str, Any]]:

    if results is None:
        results = []

    query_lower = query.lower()

    if isinstance(value, dict):

        for key, child in value.items():

            child_path = (
                f"{path}.{key}"
            )

            if query_lower in str(key).lower():

                results.append(
                    (child_path, child)
                )

            # Also search simple values.

            if not isinstance(
                child,
                (dict, list),
            ):

                if query_lower in str(child).lower():

                    entry = (
                        child_path,
                        child,
                    )

                    if entry not in results:
                        results.append(entry)

            search_data(
                child,
                query,
                child_path,
                results,
            )

    elif isinstance(value, list):

        for index, child in enumerate(value):

            child_path = (
                f"{path}[{index}]"
            )

            search_data(
                child,
                query,
                child_path,
                results,
            )

    return results


def search_interface(data: Any) -> None:

    print_header("SAVE SEARCH")

    query = input(
        "Search keys / values: "
    ).strip()

    if not query:
        return

    results = search_data(
        data,
        query,
    )

    print()

    if not results:

        print(
            f'❌ No results for "{query}".'
        )

        pause()
        return

    print(
        f"🔎 {len(results)} result(s):\n"
    )

    for index, (
        path,
        value,
    ) in enumerate(
        results[:150],
        start=1,
    ):

        print(
            f"{index:>3}. "
            f"{path}"
        )

        print(
            f"     "
            f"[{friendly_type(value)}] "
            f"{summarize(value, 100)}"
        )

    if len(results) > 150:

        print(
            f"\nShowing first 150 of "
            f"{len(results)} matches."
        )

    pause()


# ============================================================
# DICTIONARY / LIST BROWSER
# ============================================================

def edit_scalar(
    container: Any,
    key: Any,
) -> None:

    old_value = container[key]

    print_header(
        f"EDIT VALUE — {key}"
    )

    print(
        f"Type:  {friendly_type(old_value)}"
    )

    print(
        f"Value: {repr(old_value)}"
    )

    print()
    print(
        "Enter a new value."
    )

    print(
        "Press Enter without typing "
        "anything to cancel."
    )

    raw = input("\nNew value: ")

    if raw == "":
        return

    try:

        new_value = parse_value(
            raw,
            old_value,
        )

    except (
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ) as error:

        print(
            f"\n❌ Could not parse value:\n"
            f"{error}"
        )

        pause()
        return

    print()
    print("CHANGE PREVIEW")
    print("-" * 50)

    print(
        f"OLD [{friendly_type(old_value)}]: "
        f"{repr(old_value)}"
    )

    print(
        f"NEW [{friendly_type(new_value)}]: "
        f"{repr(new_value)}"
    )

    if yes_no(
        "\nApply this change?"
    ):

        container[key] = new_value

        print("✅ Updated.")

    pause()


def browse_container(
    root: Any,
) -> None:

    stack: list[
        tuple[Any, str]
    ] = [
        (root, "root")
    ]

    while stack:

        current, current_path = stack[-1]

        print_header(
            f"SAVE BROWSER — {current_path}"
        )

        if isinstance(current, dict):

            entries = list(
                current.items()
            )

        elif isinstance(current, list):

            entries = list(
                enumerate(current)
            )

        else:

            print(
                f"[{friendly_type(current)}]"
            )

            print(repr(current))

            pause()

            stack.pop()

            continue

        if not entries:

            print("(empty container)")

        else:

            for number, (
                key,
                value,
            ) in enumerate(
                entries,
                start=1,
            ):

                marker = (
                    "📂"
                    if isinstance(
                        value,
                        (dict, list),
                    )
                    else "✏️"
                )

                print(
                    f"{number:>4}. "
                    f"{marker} "
                    f"{str(key):<30} "
                    f"[{friendly_type(value):<12}] "
                    f"{summarize(value)}"
                )

        print()
        print("Commands:")
        print(
            "  number = open/edit entry"
        )
        print(
            "  S      = search entire save"
        )
        print(
            "  B      = go back"
        )
        print(
            "  Q      = exit browser"
        )

        command = input(
            "\nBrowser> "
        ).strip()

        if command.lower() == "q":
            return

        if command.lower() == "b":

            if len(stack) > 1:
                stack.pop()
            else:
                return

            continue

        if command.lower() == "s":

            search_interface(root)
            continue

        try:

            selected_index = (
                int(command) - 1
            )

            key, value = (
                entries[selected_index]
            )

        except (
            ValueError,
            IndexError,
        ):

            print("❌ Invalid selection.")
            pause()

            continue

        if isinstance(
            value,
            (dict, list),
        ):

            child_path = (
                f"{current_path}.{key}"
                if isinstance(current, dict)
                else f"{current_path}[{key}]"
            )

            stack.append(
                (value, child_path)
            )

        else:

            edit_scalar(
                current,
                key,
            )


# ============================================================
# EXPORT SYSTEM
# ============================================================

def json_serializable(
    value: Any,
) -> Any:

    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, dict):

        return {
            str(key): json_serializable(child)
            for key, child in value.items()
        }

    if isinstance(value, list):

        return [
            json_serializable(child)
            for child in value
        ]

    if isinstance(value, tuple):

        return [
            json_serializable(child)
            for child in value
        ]

    return str(value)


def export_snapshot(
    save_path: Path,
    data: Any,
) -> Path:

    directory = (
        save_path.parent
        / EXPORT_FOLDER
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    destination = directory / (
        f"{save_path.stem}"
        f"_export_{timestamp}.json"
    )

    with destination.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            json_serializable(data),
            file,
            indent=4,
            ensure_ascii=False,
        )

    return destination


# ============================================================
# SMART KEY CATEGORIES
# ============================================================

SEARCH_PRESETS = {
    "1": (
        "💰 Money / Currency",
        (
            "money",
            "cash",
            "coins",
            "tips",
            "currency",
        ),
    ),

    "2": (
        "⭐ Rank / Level / XP",
        (
            "rank",
            "level",
            "xp",
            "points",
            "experience",
        ),
    ),

    "3": (
        "🎟️ Tickets",
        (
            "ticket",
            "tickets",
        ),
    ),

    "4": (
        "🏆 Stickers / Achievements",
        (
            "sticker",
            "achievement",
            "award",
        ),
    ),

    "5": (
        "👥 Customers",
        (
            "customer",
            "customers",
            "closer",
        ),
    ),

    "6": (
        "🍕 Ingredients",
        (
            "ingredient",
            "ingredients",
            "topping",
            "syrup",
            "flavor",
        ),
    ),

    "7": (
        "📜 Recipes",
        (
            "recipe",
            "recipes",
            "special",
        ),
    ),

    "8": (
        "🎮 Minigames",
        (
            "minigame",
            "mini_game",
            "game_ticket",
        ),
    ),

    "9": (
        "🎄 Holidays",
        (
            "holiday",
            "season",
        ),
    ),

    "10": (
        "🛋️ Furniture / Lobby",
        (
            "furniture",
            "lobby",
            "decor",
            "decoration",
        ),
    ),

    "11": (
        "👕 Clothing",
        (
            "clothing",
            "clothes",
            "outfit",
            "shirt",
            "hat",
        ),
    ),

    "12": (
        "📅 Day / Progress",
        (
            "day",
            "currentday",
            "progress",
        ),
    ),
}


def smart_search(data: Any) -> None:

    print_header(
        "SMART SAVE INSPECTOR"
    )

    for key, (
        name,
        _,
    ) in SEARCH_PRESETS.items():

        print(
            f"{key:>2}. {name}"
        )

    print()
    print(" 0. Return")

    selection = input(
        "\nCategory: "
    ).strip()

    if selection == "0":
        return

    preset = SEARCH_PRESETS.get(
        selection
    )

    if not preset:

        print("❌ Invalid category.")
        pause()

        return

    name, search_terms = preset

    print_header(name)

    combined: list[
        tuple[str, Any]
    ] = []

    for term in search_terms:

        matches = search_data(
            data,
            term,
        )

        for result in matches:

            if result not in combined:
                combined.append(result)

    if not combined:

        print(
            "No likely fields were automatically "
            "identified."
        )

        print()
        print(
            "This does NOT mean the feature "
            "isn't stored in the save."
        )

        print(
            "The game may use different "
            "internal field names."
        )

        pause()

        return

    for index, (
        path,
        value,
    ) in enumerate(
        combined[:200],
        start=1,
    ):

        print(
            f"{index:>3}. "
            f"{path}"
        )

        print(
            f"     "
            f"[{friendly_type(value)}] "
            f"{summarize(value, 100)}"
        )

    print()
    print(
        f"Found {len(combined)} "
        "potential field(s)."
    )

    pause()


# ============================================================
# SAVE INFORMATION
# ============================================================

def count_nodes(
    value: Any,
) -> tuple[int, int, int]:

    dictionaries = 0
    lists = 0
    scalars = 0

    if isinstance(value, dict):

        dictionaries += 1

        for child in value.values():

            d, l, s = count_nodes(
                child
            )

            dictionaries += d
            lists += l
            scalars += s

    elif isinstance(value, list):

        lists += 1

        for child in value:

            d, l, s = count_nodes(
                child
            )

            dictionaries += d
            lists += l
            scalars += s

    else:

        scalars += 1

    return (
        dictionaries,
        lists,
        scalars,
    )


def show_save_info(
    profile: GameProfile,
    save_path: Path,
    save_format: str,
    data: Any,
) -> None:

    print_header("SAVE INFORMATION")

    dictionaries, lists, scalars = (
        count_nodes(data)
    )

    print(f"Game:       {profile.name}")
    print(f"File:       {save_path.name}")
    print(f"Path:       {save_path}")
    print(f"Format:     {save_format.upper()}")

    print(
        f"File Size:  "
        f"{save_path.stat().st_size:,} bytes"
    )

    print(
        f"Modified:   "
        f"{datetime.fromtimestamp(save_path.stat().st_mtime)}"
    )

    print()
    print("SAVE STRUCTURE")
    print(f"Dictionaries: {dictionaries:,}")
    print(f"Lists:        {lists:,}")
    print(f"Values:       {scalars:,}")

    if isinstance(data, dict):

        print(
            f"Root Keys:    {len(data):,}"
        )

        print()
        print("ROOT FIELDS")

        for key in list(
            data.keys()
        )[:100]:

            value = data[key]

            print(
                f" • {key} "
                f"[{friendly_type(value)}]"
            )

    pause()


# ============================================================
# PENDING CHANGE DISPLAY
# ============================================================

def show_changes(
    original: Any,
    modified: Any,
) -> list[str]:

    changes = compare_data(
        original,
        modified,
    )

    print_header("PENDING CHANGES")

    if not changes:

        print("✅ No unsaved changes.")
        return changes

    print(
        f"⚠️ {len(changes)} change(s) pending.\n"
    )

    for change in changes[:250]:
        print(change)

    if len(changes) > 250:

        print(
            f"\n... {len(changes) - 250} "
            "additional changes not displayed."
        )

    return changes


# ============================================================
# SAFE SAVE OPERATION
# ============================================================

def save_modified_data(
    save_path: Path,
    save_format: str,
    original: Any,
    modified: Any,
) -> bool:

    changes = show_changes(
        original,
        modified,
    )

    if not changes:

        pause()
        return False

    print()

    if not yes_no(
        "Write these changes to disk?"
    ):
        print("❌ Save cancelled.")
        pause()

        return False

    backup: Path | None = None

    try:

        backup = create_backup(
            save_path
        )

        write_save(
            save_path,
            save_format,
            modified,
        )

        # Validation pass:
        # immediately reopen file.

        _, verification = load_save(
            save_path
        )

        print()
        print("✅ File successfully written.")
        print("✅ Save successfully reopened.")
        print("✅ Basic validation passed.")

        return True

    except Exception as error:

        print()
        print("❌ SAVE FAILED")
        print(error)

        if (
            backup is not None
            and backup.exists()
        ):

            print()
            print(
                "Attempting automatic recovery..."
            )

            try:

                shutil.copy2(
                    backup,
                    save_path,
                )

                print(
                    "🛡️ Original save restored "
                    "from backup."
                )

            except Exception as recovery_error:

                print()
                print(
                    "⚠️ AUTOMATIC RECOVERY FAILED"
                )

                print(recovery_error)

                print()
                print(
                    "Your backup still exists here:"
                )

                print(backup)

        pause()

        return False


# ============================================================
# GAME EDITOR
# ============================================================

def game_editor(
    profile: GameProfile,
    save_path: Path,
) -> None:

    try:

        save_format, data = load_save(
            save_path
        )

    except Exception as error:

        print_header("LOAD ERROR")

        print(error)

        pause()

        return

    original = deepcopy(data)

    while True:

        clear_screen()
        print_logo()

        print(
            f"🎮 Game:   {profile.name}"
        )

        print(
            f"💾 Save:   {save_path.name}"
        )

        print(
            f"📦 Format: {save_format.upper()}"
        )

        pending = compare_data(
            original,
            data,
        )

        print(
            f"📝 Changes: {len(pending)}"
        )

        print()

        print(
            "╔════════════════════════════════════════╗"
        )

        print(
            "║             SAVE EDITOR                ║"
        )

        print(
            "╠════════════════════════════════════════╣"
        )

        print(
            "║ 1. 🔬 Advanced Save Browser            ║"
        )

        print(
            "║ 2. 🔎 Search Save Data                 ║"
        )

        print(
            "║ 3. 🧠 Smart Field Inspector            ║"
        )

        print(
            "║ 4. 📝 View Pending Changes             ║"
        )

        print(
            "║ 5. 📤 Export Save as JSON              ║"
        )

        print(
            "║ 6. ℹ️  Save Information                ║"
        )

        print(
            "║ 7. ↩️  Restore Backup                  ║"
        )

        print(
            "║ 8. 🔄 Reload Save                      ║"
        )

        print(
            "║ 9. 💾 SAVE CHANGES                     ║"
        )

        print(
            "║ 0. 🚪 Exit Editor                      ║"
        )

        print(
            "╚════════════════════════════════════════╝"
        )

        choice = input(
            "\nChoose: "
        ).strip()

        if choice == "1":

            browse_container(data)

        elif choice == "2":

            search_interface(data)

        elif choice == "3":

            smart_search(data)

        elif choice == "4":

            show_changes(
                original,
                data,
            )

            pause()

        elif choice == "5":

            try:

                destination = (
                    export_snapshot(
                        save_path,
                        data,
                    )
                )

                print(
                    "\n✅ JSON inspection "
                    "snapshot exported:"
                )

                print(destination)

            except Exception as error:

                print(
                    f"\n❌ Export failed:\n"
                    f"{error}"
                )

            pause()

        elif choice == "6":

            show_save_info(
                profile,
                save_path,
                save_format,
                data,
            )

        elif choice == "7":

            if compare_data(
                original,
                data,
            ):

                print(
                    "\n⚠️ You currently have "
                    "unsaved edits."
                )

                if not yes_no(
                    "Discard them and continue?"
                ):
                    continue

            if restore_backup(
                save_path
            ):

                try:

                    save_format, data = (
                        load_save(
                            save_path
                        )
                    )

                    original = deepcopy(
                        data
                    )

                except Exception as error:

                    print(
                        f"\n❌ Reload failed:\n"
                        f"{error}"
                    )

                    pause()

        elif choice == "8":

            if compare_data(
                original,
                data,
            ):

                if not yes_no(
                    "Discard unsaved changes?"
                ):

                    continue

            try:

                save_format, data = (
                    load_save(
                        save_path
                    )
                )

                original = deepcopy(
                    data
                )

                print(
                    "\n✅ Save reloaded."
                )

            except Exception as error:

                print(
                    f"\n❌ Reload failed:\n"
                    f"{error}"
                )

            pause()

        elif choice == "9":

            if save_modified_data(
                save_path,
                save_format,
                original,
                data,
            ):

                # Reload the exact written
                # structure.

                save_format, data = (
                    load_save(
                        save_path
                    )
                )

                original = deepcopy(
                    data
                )

                pause()

        elif choice == "0":

            unsaved = compare_data(
                original,
                data,
            )

            if unsaved:

                print()
                print(
                    f"⚠️ You have "
                    f"{len(unsaved)} "
                    "unsaved change(s)."
                )

                if not yes_no(
                    "Exit without saving?"
                ):

                    continue

            return

        else:

            print(
                "\n❌ Invalid selection."
            )

            pause()


# ============================================================
# SELECT SAVE
# ============================================================

def open_game(
    profile: GameProfile,
) -> None:

    clear_screen()
    print_logo()

    print_header(profile.name)

    print(profile.description)

    print()
    print(
        "Enter either:"
    )

    print(
        " • the full path to a save file"
    )

    print(
        " • OR a folder containing saves"
    )

    print()
    print(
        "The toolkit will recursively search "
        "folders for compatible files."
    )

    raw = input(
        "\nPath: "
    )

    if not raw.strip():
        return

    location = normalize_path(raw)

    files = detect_files(
        location,
        profile.extensions,
    )

    save_path = choose_file(
        files
    )

    if save_path is None:
        pause()
        return

    game_editor(
        profile,
        save_path,
    )


# ============================================================
# SOL DIAGNOSTICS
# ============================================================

def diagnostics() -> None:

    clear_screen()
    print_logo()

    print_header("DIAGNOSTICS")

    print(
        f"Python: {sys.version.split()[0]}"
    )

    print(
        f"Executable: {sys.executable}"
    )

    print()

    if SOL_AVAILABLE:

        print(
            "✅ SOL support available."
        )

    else:

        print(
            "❌ SOL support unavailable."
        )

        if SOL_IMPORT_ERROR:

            print()
            print(
                "Import error:"
            )

            print(
                SOL_IMPORT_ERROR
            )

    print()
    print(
        "✅ JSON support available."
    )

    pause()


# ============================================================
# MAIN MENU
# ============================================================

def main() -> None:

    while True:

        clear_screen()
        print_logo()

        print(
            "Fan-made save inspection "
            "and editing utility."
        )

        print()

        print(
            " 1. 🔨 JackSmith"
        )

        print(
            " 2. 🍨 Papa's Freezeria Deluxe"
        )

        print(
            " 3. 🍕 Papa's Pizzeria Deluxe"
        )

        print(
            " 4. ☕ Papa's Mocharia Deluxe"
        )

        print()
        print(
            " 8. 🔧 Diagnostics"
        )

        print(
            " 9. ℹ️  About"
        )

        print(
            " 0. 🚪 Exit"
        )

        choice = input(
            "\nSelect game: "
        ).strip()

        if choice in GAMES:

            open_game(
                GAMES[choice]
            )

        elif choice == "8":

            diagnostics()

        elif choice == "9":

            clear_screen()
            print_logo()

            print_header("ABOUT")

            print(
                f"{APP_NAME} v{VERSION}"
            )

            print()

            print(
                "A fan-made save inspection "
                "and editing toolkit."
            )

            print()
            print(
                "Supported profiles:"
            )

            for profile in GAMES.values():

                print(
                    f" • {profile.name}"
                )

            print()
            print(
                "The toolkit intentionally does "
                "not use fake values such as:"
            )

            print(
                '    "ALL_UNLOCKED"'
            )

            print()
            print(
                "Unlock structures differ between "
                "games and save versions."
            )

            print(
                "Use the inspector to identify "
                "the real fields first."
            )

            pause()

        elif choice == "0":

            clear_screen()

            print(
                "\n👋 Thanks for using "
                f"{APP_NAME}!\n"
            )

            break

        else:

            print(
                "\n❌ Invalid selection."
            )

            pause()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\n\n👋 Cancelled by user."
        )

    except Exception as error:

        print()
        print("=" * 72)
        print(
            "💥 UNEXPECTED ERROR"
        )
        print("=" * 72)

        print(
            f"\n{type(error).__name__}: "
            f"{error}"
        )

        print()
        print(
            "Your original save should remain "
            "untouched unless a confirmed save "
            "operation occurred."
        )
