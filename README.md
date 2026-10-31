# size_codebase.py

This is an all-in-one inventory taker meant to deal with a large number of cases. It handles
codebases that are actually all in one file, such as those built with the Unity game engine or
with Microsoft Access, projects that have switched between multiple version control systems, and
codebases where libraries copied in from elsewhere sit among the owner's own code.

Point it at a folder and it reports how much code there is and in which languages, how much of it
is the owner's own versus someone else's, how much work went into it (commits, contributors, pull
requests), and the standard measures that codebase questionnaires ask for.
[Patina Source](https://patinasource.com) asks companies to run it before licensing their source
code.

It only **reads** files. It prints a summary and saves it next to the script as
`size_report_<folder>.txt`. The report holds counts and folder names only: no source code, no file
names, no author names. Nothing is uploaded anywhere.

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
python3 size_codebase.py "/path/to/project" --third-party src/vendor/somelib --own plugins/ours
```

Other options cover languages it doesn't know (`--code-ext`), Visual SourceSafe databases
(`--sourcesafe`), code inside a running SQL Server (`--sql-server`), and saving scc's and jscpd's
own reports (`--reports`). See the [command-line reference](HOW_IT_WORKS.md#14-command-line-reference).

## What it understands

- **Languages:** mainstream ones (C, C++, C#, Java, Python, JavaScript/TypeScript, Go, Rust ...),
  enterprise and legacy ones (COBOL, Fortran, Ada, ABAP, PL/I, RPG, VB6, Delphi ...), shaders and
  scripting languages, and any other you name with `--code-ext`.
- **Code inside files and databases:** Microsoft Access (queries, VBA, forms and reports), SQL
  Server (stored procedures, views, functions and triggers from scripts, `.dacpac` packages or a
  running server), SSIS and SSRS. It reads only code and the list of objects, never the rows in a
  table.
- **Someone else's code:** vendored and copied-in libraries, licence headers and licence files,
  package-manager dependencies, Git submodules, bought plugins, generated and minified code, and
  data pasted into source files, all kept apart from the owner's own code.
- **Version control:** Git, Perforce, SVN, Mercurial, Plastic SCM, Team Foundation (TFVC), Bazaar,
  Fossil, Darcs, CVS and Visual SourceSafe (read straight from its database). When a project moved
  from one system to another, it combines the histories without counting the same work twice.
  Without version control, it counts the people named as authors in the code.
- **Game engines:** Unity, Unreal (every version from 1 to 5, including Blueprints counted in
  nodes), Godot, GameMaker, Ren'Py and others.

For everything it does, the cases it handles and where it can be wrong, see
[HOW_IT_WORKS.md](HOW_IT_WORKS.md).

## Standard measures

The report ends with the measures buyers' codebase forms ask for: logical lines of code and
generated lines ([scc](https://github.com/boyter/scc)), duplication
([jscpd](https://github.com/kucherenko/jscpd)), commits on the main branch without merges or
reverts, and the primary language. scc and jscpd are fetched once from their official releases and
checked against fixed checksums. Offline, or with `--no-download`, the script uses a copy it already
has, or else estimates their figures itself.
