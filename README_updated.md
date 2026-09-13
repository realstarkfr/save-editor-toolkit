# Papa's Save Toolkit

A fan-made, multi-game save inspector and editor for select **Flipline Studios** PC releases.

> **Current toolkit version:** 3.0.0  
> Built for local, single-player save inspection and editing with automatic backups and recovery.

## Supported Games

- 🔨 **JackSmith**
- 🍨 **Papa's Freezeria Deluxe**
- 🍕 **Papa's Pizzeria Deluxe**
- ☕ **Papa's Mocharia Deluxe**

The toolkit is designed around reusable game profiles, so additional compatible games can be added later without rewriting the entire editor.

## Major Features

- 💾 Automatic timestamped backups before save writes
- ↩️ Backup restore menu
- 🛡️ Automatic rollback attempt if a write fails
- 🔬 Nested save-data browser
- 🔎 Search keys and values across the save
- 🧠 Smart field inspector for common save categories
- 📝 Pending-change preview before writing
- 📤 Export decoded save data to JSON for inspection
- 📂 File or folder input with automatic save discovery
- 🧬 Type-aware editing for integers, floats, booleans, strings, lists, and dictionaries
- ✅ Save reopen/validation pass after writing
- 🧩 Modular game-profile architecture
- 🖥️ Console-based interface with no GUI dependency

## Smart Inspector Categories

The Smart Field Inspector can search for likely fields related to:

- 💰 Money / currency
- ⭐ Rank / level / XP
- 🎟️ Tickets
- 🏆 Stickers / achievements
- 👥 Customers
- 🍕 Ingredients / toppings / flavors
- 📜 Recipes / Specials
- 🎮 Minigames
- 🎄 Holidays / seasons
- 🛋️ Furniture / lobby decorations
- 👕 Clothing / outfits
- 📅 Day / progression

These searches are intentionally schema-aware but **not destructive**. The editor does not blindly replace complex save structures with fake values such as `"ALL_UNLOCKED"`.

## Papa's Mocharia Deluxe

Papa's Mocharia Deluxe is included as a supported toolkit profile.

The Deluxe release includes features such as:

- 154 customers
- 124 ingredients
- 40 Special Recipes
- 90 stickers
- 12 holidays
- 7 minigames
- Food Truck free-play content
- Clothing, furniture, and seasonal unlocks

Because internal save-field names may differ between game versions, the toolkit first exposes the real save structure through the browser, search engine, and JSON exporter before game-specific one-click unlock logic is added.

## Requirements

### Python

**Python 3.11 or newer is recommended.**

Py3AMF currently tests CPython 3.11, 3.12, 3.13, and 3.14.

### Python Package

Install dependencies with:

```bash
python -m pip install -r requirements.txt
```

Recommended `requirements.txt`:

```text
Py3AMF==0.9.1
```

Py3AMF is the maintained Python 3 fork of PyAMF and provides the `pyamf` package namespace used by the toolkit:

```python
from pyamf.sol import SolReader, SolWriter
```

Do **not** install the old Python-2-era `PyAMF` package for this project.

## Installation

Clone or download the project, then open a terminal in the project directory.

Optional but recommended: create a virtual environment.

### Windows

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux / Steam Deck / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Running the Toolkit

Run:

```bash
python papas_save_toolkit.py
```

Example menu:

```text
╔════════════════════════════════════════════╗
║          PAPA'S SAVE TOOLKIT v3.0         ║
╚════════════════════════════════════════════╝

 1. 🔨 JackSmith
 2. 🍨 Papa's Freezeria Deluxe
 3. 🍕 Papa's Pizzeria Deluxe
 4. ☕ Papa's Mocharia Deluxe

 8. 🔧 Diagnostics
 9. ℹ️  About
 0. 🚪 Exit
```

Choose a game, then provide either:

- the full path to a compatible save file, or
- a directory containing save files

The toolkit can search compatible files inside the selected directory and let you choose which save to open.

## Save Formats

The toolkit currently supports:

| Format | Use |
|---|---|
| `.sol` | AMF/Flash Local Shared Object saves used by supported Papa's Deluxe titles |
| `.json` | JSON-formatted saves, including supported JackSmith configurations |

The toolkit determines the loader from the file extension.

## Safety System

Before writing a modified save, the toolkit:

1. Calculates the pending differences.
2. Shows a change preview.
3. Requests confirmation.
4. Creates a timestamped backup.
5. Writes through a temporary file where supported.
6. Reopens the save as a basic validation check.
7. Attempts to restore the backup if writing fails.

Backups are stored beside the original save under:

```text
PapaSaveToolkit_Backups/
```

JSON inspection exports are stored under:

```text
PapaSaveToolkit_Exports/
```

Even with these safeguards, keep your own copies of important saves.

## Save Browser

The Advanced Save Browser can inspect nested dictionaries and lists instead of assuming every game uses the same save schema.

Example:

```text
  1. ✏️ money                      [float]       243.75
  2. ✏️ tickets                    [int]         12
  3. 📂 customers                  [dict:154]    {...}
  4. 📂 ingredients                [dict:124]    {...}
  5. 📂 stickers                   [dict:90]     {...}
```

Simple values can be edited directly. Complex structures can be opened and inspected recursively.

## JSON Export / Save Research

If a game's internal field names are unknown, export the decoded save to JSON from the toolkit.

This is especially useful when adding proper game-specific editors for:

- unlock-all ingredients
- customer unlocks
- Special Recipes
- stickers
- minigames
- holiday progression
- furniture
- clothing
- rank and XP

The project should prefer confirmed fields from real saves over guessed keys.

## Adding Another Game

Add another `GameProfile` entry to the `GAMES` dictionary:

```python
"5": GameProfile(
    identifier="example_game",
    name="Papa's Example Deluxe",
    extensions=(".sol", ".json"),
    preferred_format="auto",
    description="Example game profile",
),
```

The generic browser, search, backup, export, and editor systems can then work without duplicating the entire program.

## Diagnostics

The Diagnostics menu displays:

- Python version
- Python executable
- JSON support status
- SOL/Py3AMF support status
- import errors if SOL support cannot load

This is useful when troubleshooting installation problems.

## Building a Standalone Windows EXE

PyInstaller is optional and should not be placed in the normal runtime requirements unless you want every user to install build tooling.

Install it separately:

```bash
python -m pip install pyinstaller
```

Then build:

```bash
pyinstaller --onefile --name PapasSaveToolkit papas_save_toolkit.py
```

If the project includes an icon:

```bash
pyinstaller --onefile --name PapasSaveToolkit --icon=icon.ico papas_save_toolkit.py
```

The generated executable will normally appear under:

```text
dist/
```

Always test SOL loading and saving in the packaged build before distributing it.

## Suggested Project Layout

```text
Papas-Save-Toolkit/
├── papas_save_toolkit.py
├── requirements.txt
├── README.md
├── icon.ico
├── .gitignore
└── LICENSE
```

Runtime-generated backup and export folders should generally be excluded from Git.

Example `.gitignore` entries:

```gitignore
.venv/
__pycache__/
*.pyc
PapaSaveToolkit_Backups/
PapaSaveToolkit_Exports/
dist/
build/
*.spec
```

## Development Notes

The original editor used direct keys such as `money`, `stars`, `tickets`, and placeholder unlock values. The modern toolkit takes a safer approach:

- inspect the real save first
- preserve existing data types
- preview changes before saving
- avoid replacing dictionaries/lists with placeholder strings
- build dedicated one-click edits only after the real schema has been confirmed

This makes the toolkit much safer across different games and save revisions.

## Disclaimer

This is an unofficial fan-made project and is not affiliated with or endorsed by Flipline Studios.

Use it only with saves you are authorized to modify. Back up your files before editing. Save formats can change between game updates, so compatibility is not guaranteed forever.

Game names, characters, and trademarks belong to their respective owners.

## Project Status

The toolkit currently focuses on robust save discovery, inspection, editing, backup, export, and recovery.

Future game-specific mappings can add dedicated actions such as:

```text
💰 Set Money
⭐ Set Rank / XP
🎟️ Set Tickets
👥 Unlock Customers
🍨 Unlock Ingredients
📜 Unlock Special Recipes
🏆 Unlock Stickers
🎮 Unlock Minigames
🎄 Unlock Holidays
🛋️ Unlock Furniture
👕 Unlock Clothing
```

Those actions should be implemented only after their actual save structures are confirmed.

---

**For fans, by fans. ☕🍕🍨🔨**
