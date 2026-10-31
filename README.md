# size_codebase.py

Sizes up a codebase: how much code there is, in which languages, how much of it is the
studio's own versus third-party, and how much work went into it (commits, contributors,
pull requests). [Patina Source](https://patinasource.com) asks studios to run it before
licensing the source code of a game.

It only **reads** files. It prints a summary and saves it next to the script as
`size_report_<folder>.txt`. The report holds counts and folder names only: no source code,
no file names, no author names. Nothing is uploaded anywhere.

## Usage

Needs Python 3.8+ and nothing else ([python.org/downloads](https://www.python.org/downloads/)).
Works on Windows, macOS and Linux.

```sh
python3 size_codebase.py "/path/to/project"  ["/path/to/other" ...]
python3 size_codebase.py                       # asks for the folder; drag it into the window
python3 size_codebase.py "/path/to/Program.mdb"  # a single file, e.g. an Access database
```

On Windows, `py` instead of `python3` also works, and so does double-clicking the script.

If it gets a folder wrong, say so (paths relative to the project folder, or absolute; repeatable):

```sh
python3 size_codebase.py "/path/to/project" --third-party Source/Game/SomeLib --own Plugins/MyPlugin
```

The comment at the top of the script covers the rest:
languages it doesn't know (`--code-ext`), Visual SourceSafe databases (`--sourcesafe`),
SQL Server (`--sql-server`), and saving scc's and jscpd's own reports (`--reports`).

## What it understands

- **Engines:** Unity, Unreal (every version from Unreal Engine 1 to 5: C++, Blueprints,
  UnrealScript, Kismet, AngelScript, Verse ...), Godot, GameMaker, Ren'Py, Defold and more;
  Python and JavaScript/TypeScript projects; most other languages too.
- **Version control:** Git, Perforce, SVN, Mercurial, Plastic SCM (Unity Version Control),
  Team Foundation (TFVC), Bazaar, Fossil, Darcs, CVS and Visual SourceSafe. Without version
  control, it counts the people named as authors in the code. To count pull requests and
  changelists it may ask your own version-control server, read-only, with the access you
  already have.
- **Databases:** Microsoft Access and SQL Server (forms, reports, queries, VBA, stored
  procedures, SSIS and SSRS). It reads only code and the list of objects, never the rows in a
  table.

## Standard measures

The report ends with the measures buyers' codebase forms ask for: logical lines of code and
generated lines ([scc](https://github.com/boyter/scc)), duplication
([jscpd](https://github.com/kucherenko/jscpd)), commits on the main branch without merges or
reverts, and the primary language. scc and jscpd are fetched once from their official
releases and checked against fixed checksums. Offline, or with `--no-download`, the script
estimates their figures itself.
