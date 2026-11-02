# How size_codebase.py works

`size_codebase.py` takes an inventory of a codebase. It counts lines of code by language, separates the owner's own code from code someone else wrote, reads the version-control history, counts contributors and pull requests, lists assets, flags credentials and licences, and produces the standard measures that codebase questionnaires ask for (logical lines and generated lines as `scc` counts them, duplication as `jscpd` measures it, commits on the main branch).

It is a single Python file that needs Python 3.8 or later and nothing else. It runs on Windows, macOS and Linux.

This document explains what it does in detail: what it reads, how it decides what is code and whose code it is, how it reads each version-control system, and where it can be wrong. The README has the short version and basic usage.

Contents:

1. [Privacy: what it reads, what it reports, what it never does](#1-privacy-what-it-reads-what-it-reports-what-it-never-does)
2. [What you can point it at](#2-what-you-can-point-it-at)
3. [Walking the folder: project types and what is skipped](#3-walking-the-folder-project-types-and-what-is-skipped)
4. [What counts as code](#4-what-counts-as-code)
5. [Game engines](#5-game-engines)
6. [Codebases inside a file or a database](#6-codebases-inside-a-file-or-a-database)
7. [Own code versus someone else's](#7-own-code-versus-someone-elses)
8. [Generated code, data, duplicates and other things that are not counted as own code](#8-generated-code-data-duplicates-and-other-things-that-are-not-counted-as-own-code)
9. [Version control](#9-version-control)
10. [Contributors](#10-contributors)
11. [Other findings](#11-other-findings)
12. [Standard measures (scc, jscpd)](#12-standard-measures-scc-jscpd)
13. [Output](#13-output)
14. [Command-line reference](#14-command-line-reference)
15. [Limitations, and how to correct them](#15-limitations-and-how-to-correct-them)

---

## 1. Privacy: what it reads, what it reports, what it never does

[SECURITY.md](SECURITY.md) has the full details, each tied to the function that does it: every network connection, every program it runs, every file it writes, everything it reads outside the scanned folder, and the protections against a hostile project. In short:

- **It only reads the project.** It writes its report, a cache holding scc and jscpd, and temporary folders that it deletes when done.
- **Nothing is uploaded.** It connects to other computers only to download scc and jscpd once (checked against fixed SHA-256 checksums), and to ask your own version-control servers for history and pull-request counts, with the access you already have; the tools are told not to prompt for passwords. `--offline` turns all of that off (see [section 14](#14-command-line-reference)).
- **The report holds counts**, and the names of folders, languages, libraries, packages and branches. It never holds source code, author names or email addresses (names are read to *count* people and stay in memory), credentials (only their kind and number of files), or database rows. It names a file only if you give that file on its own or mark it with `--third-party`. Error messages in it have paths replaced by `<project>`, `~` or `<path>`. With `--reports`, scc's report and jscpd's totals are saved too; both hold counts only (see [section 12](#12-standard-measures-scc-jscpd)).

Look the report over before sending it: folder, library, package and branch names are the owner's own words. SECURITY.md lists exactly what can appear in it.

### Databases: code only, never rows

From Access databases, SQL Server and SQL Server packages, it reads only code (queries, VBA, stored procedures, views, functions, triggers, SSIS statements and scripts, SSRS queries and code) and the list of objects. It never reads a table's rows. The one table-like thing it reads is Access's own catalog of objects (`MSysObjects`), through mdbtools, to count forms, reports, queries, macros and modules. For a `.bacpac` export, which holds every table's rows, only the schema (`model.xml`) and the pre- and post-deployment scripts are opened.

Microsoft Access is only ever given a temporary *copy* of a database, and only once Access confirms that the database's macros and code are switched off (`AutomationSecurity` set to "force disable"); if it can't, the database isn't opened, and the report says so. mdbtools only reads, so it works on the original.

---

## 2. What you can point it at

- **A folder.** The usual case. Everything under it is scanned.
- **Several folders.** Each is scanned and reported separately, with the same options.
- **A single file.** Typically an Access database, which holds a whole program in one file. Only that file is examined (its folder supplies the version-control context). scc and jscpd are not run on a single file.
- **Nothing.** Started without arguments (for example by double-clicking it on Windows), it asks for a folder: drag it into the window or paste the path, press Enter, and repeat for more folders. An empty line ends it. Options can't be given in this mode.

Dragged and pasted paths are cleaned up: Windows-style `"quotes"`, macOS Terminal's backslash escapes (`My\ Game`), Linux `'quotes'` and `file://` URLs all work.

On Windows it handles paths longer than 260 characters and network shares. Folder names are matched case-insensitively where it matters (Linux tells `Classes` from `classes`; Windows, where most projects are made, does not).

---

## 3. Walking the folder: project types and what is skipped

### Project types

In every folder it looks for the marks of a project and lists what it finds under "Project types found". A type is not listed again inside a project of the same type (so `docs/requirements.txt` inside a Python project is not a second project).

| Type | Recognised by |
|---|---|
| Unity | `ProjectSettings/ProjectVersion.txt` (gives the editor version), or `Assets` and `ProjectSettings` side by side |
| Unreal Engine 4/5 project | a `.uproject` (its `EngineAssociation` gives the engine version, or says it is a custom-built engine) |
| Unreal Editor for Fortnite | a `.uefnproject` |
| Unreal Engine source | `Build/Build.version` (the `Engine` folder of a source build; gives major.minor.patch) |
| Unreal Engine 3 | `Development/Src` |
| Unreal Engine 1/2 | a `System` folder holding `.u` or `.int` files, beside `Maps`, `Textures`, `Sounds` or `Music` |
| UnrealScript package | a `Classes` folder holding `.uc` files |
| Godot | `project.godot` (version from `config/features`, else 3.x or 4.x from `config_version`) |
| GameMaker | `.yyp` (Studio 2) or `.project.gmx` (Studio 1) |
| Ren'Py | a `game` folder holding `.rpy`, `.rpyc` or `.rpa` files |
| Defold | `game.project` |
| Construct | `.c3proj`, `.capx`, `.c3p`, `.caproj` (its event sheets are not counted) |
| RPG Maker MV / MZ | `.rpgproject` / `.rmmzproject`, or `js/rpg_core.js` / `js/rmmz_core.js` beside `data` |
| LÖVE | `main.lua` and `conf.lua` |
| Source engine (Valve) | `gameinfo.txt`, or `game`, `public` and `tier1` folders |
| CRYENGINE, Stride, Flax, MonoGame, XNA | `.cryproject`; `.sdpkg`/`.sdsln`; `.flaxproj`; `.mgcb`; `.contentproj` |
| Haxe (OpenFL / HaxeFlixel / Kha) | `.hxml`, or a `project.xml` that mentions haxelib |
| Ogre3D | `plugins.cfg`, `resources.cfg` or `ogre.cfg` |
| JavaScript (+ TypeScript) | `package.json` (TypeScript if `tsconfig.json` is beside it) |
| Python | `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt` or `Pipfile` |
| .NET | `.csproj`, `.fsproj` or `.vbproj` (not inside Unity) |
| Visual Studio solution | `.sln` (with its number of projects) |
| C/C++ (Visual Studio, CMake, premake), Meson, SCons, Xcode | `.vcxproj`/`.vcproj`, `CMakeLists.txt`, `premake*.lua`, `meson.build`, `SConstruct`, `*.xcodeproj` |
| Java/Kotlin (Gradle), Java (Maven), Rust, Go | `build.gradle(.kts)`/`settings.gradle(.kts)`, `pom.xml`, `Cargo.toml`, `go.mod` |
| Visual Basic 6 | `.vbp` or `.vbg` |
| Microsoft Access | Access database files in the folder (with their number) |
| Access exported as text | a folder named like `X.accdb.src` (the msaccess-vcs add-in's layout) |
| SQL Server: SSDT, SSIS, SSRS | `.sqlproj`, `.dtproj`, `.rptproj` |

The type matters because it changes how the folder is read: which folders are build output, what an ambiguous extension means, and which folders are someone else's.

### Skipped everywhere

These folders are never entered, wherever they appear: version-control folders (`.git`, `.svn`, `.hg`, `.bzr`, `.plastic`), editor settings (`.vs`, `.idea`, `.vscode`, `.history`), package caches and dependencies (`node_modules`, `bower_components`, `jspm_packages`, `.yarn`, `.pnpm-store`, `site-packages`, `Pods`, `Carthage`, `.swiftpm`, `.build`, `.dart_tool`, `.pub-cache`), framework build caches (`.next`, `.nuxt`, `.output`, `.svelte-kit`, `.turbo`, `.parcel-cache`, `.vercel`, `.cache`, `.sass-cache`, `.gradle`), Python caches and environments (`__pycache__`, `.venv`, `venv`, `.tox`, `.nox`, `.eggs`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.ipynb_checkpoints`), and operating-system clutter (`__MACOSX`, `.Spotlight-V100`, `.Trashes`, `.fseventsd`, `.TemporaryItems`, `$RECYCLE.BIN`, `System Volume Information`, `lost+found`).

Also skipped: any `*.egg-info` folder; any folder holding `pyvenv.cfg` (a Python virtual environment, whatever it is called); `cmake-build-*` folders and any folder holding `CMakeCache.txt` (CMake build folders); a `packages` folder whose subfolders hold `.nupkg` files (NuGet's downloads); symbolic links and Windows junctions, to folders or to files (they can loop, lead to code counted twice, or lead outside the folder; the report says how many were skipped); named pipes and devices, which can't be read like files; and macOS `._*` metadata files.

### Skipped only at the root of a project of a given kind

Build output is skipped only directly inside the project's root folder, so that a folder like `Assets/Scripts/Library` is still counted.

| Project | Folders skipped at its root |
|---|---|
| Unity | `Library`, `Temp`, `Obj`, `Logs`, `UserSettings`, `Build`, `Builds`, `MemoryCaptures` |
| Unreal | `Intermediate`, `Saved`, `DerivedDataCache`, `Binaries`, `Build`, and packaged builds made into the project folder (`Windows`, `WindowsNoEditor`, `WindowsClient`, `WindowsServer`, `Linux`, `LinuxNoEditor`, `LinuxServer`, `Mac`, `MacNoEditor`, `Android`, `IOS`, `StagedBuilds`, `ArchivedBuilds`) |
| Unreal Engine source | `Intermediate`, `Saved`, `DerivedDataCache`, `Binaries` |
| Unreal Engine 3 | `Intermediate`, `Binaries` |
| Any folder with a `.uplugin` | `Intermediate`, `Binaries` |
| JavaScript | `dist`, `build`, `out`, `coverage`, `storybook-static` |
| Python | `build`, `dist`, `htmlcov` |
| .NET, SSDT, SSIS, SSRS | `bin`, `obj` |
| C/C++ (Visual Studio) | `Debug`, `Release`, `x64`, `Win32`, `x86`, `ARM64`, `ipch` |
| Gradle | `build`, `.gradle`, `.cxx` |
| Maven, Rust | `target` |
| Godot | `.godot`, `.import` |
| GameMaker | `options`, `tmp` |

The "Total size" line in the report counts the files that remain, so it excludes dependencies, caches and build output.

---

## 4. What counts as code

### Languages by extension

A file is code if its extension is a known language. The list covers, among others:

- Mainstream: C, C++ (including modules and CUDA), C#, Objective-C, Java, Kotlin, Swift, Go, Rust, Python, Cython, JavaScript, TypeScript, Vue, Svelte, HTML, CSS/SCSS/Sass/Less, Ruby, PHP, Lua, Dart, Scala, Groovy, Elixir, Erlang, Haskell, OCaml, Clojure, F#, Zig, Nim, Perl, Tcl, CoffeeScript, shell, PowerShell, batch files.
- Shaders: HLSL, GLSL, Cg, Unity `.shader`/`.cginc`/`.compute`, Unreal `.usf`/`.ush`, Metal, WGSL, Slang, Godot shaders, and the usual stage extensions (`.vert`, `.frag` ...).
- Game and narrative scripting: UnrealScript, Verse, SkookumScript, GDScript, Ren'Py, GML, Haxe, ActionScript, Squirrel, Luau, MoonScript, Monkey, BlitzBasic, BlitzMax, AppGameKit, Boo, Ink, Yarn Spinner, Twine, Naninovel.
- Microsoft and database: Visual Basic (`.vb`), VB6/VBA (`.bas`, `.cls`, `.frm`, `.ctl`, `.dsr`, `.pag`, `.dob`), VBScript, SQL and T-SQL, PL/SQL.
- Enterprise and legacy: COBOL, Fortran (fixed and free form), Ada, ABAP, JCL, PL/I, RPG, VHDL, Verilog/SystemVerilog, Pascal/Delphi, assembly.
- Build scripts: CMake, Gradle, and build files recognised by name (`premake*.lua`, `CMakeLists.txt`, `Makefile`, `*.mk`, `SConstruct`, `SConscript`, `meson.build`, `build.ninja`, `Jamfile`, `*.jam`, `wscript`). These are listed under their own labels, such as "Lua (build scripts)" and "Make (build scripts)", so they can be told apart from the product's code.

Some extensions mean code only in a certain kind of project:

- `.script`, `.gui_script`, `.render_script` are Lua only inside a Defold project.
- `.fs` is F# only inside a .NET project (elsewhere it is usually a fragment shader).
- `.js` inside a Unity project's `Assets` is labelled UnityScript.
- `.as` inside an Unreal project is labelled AngelScript (elsewhere, ActionScript).
- `*.Build.cs` and `*.Target.cs` are labelled "C# (build rules)" (Unreal's build scripts).
- VB6/VBA files are labelled "Visual Basic 6" in a VB6 project and "VBA (Access)" in an Access project.

Not counted as code: documentation and configuration text (`.txt`, `.md`, `.json`, `.xml`, `.yaml`, `.toml`, `.ini`, `.csv`, project files such as `.sln` and `.csproj`, Unity `.meta` and `.asset`, and so on), and Jupyter notebooks, which are listed with the assets.

### How lines are counted

The main table counts **non-blank lines**, comments included. Files saved as UTF-16 (common for Windows C++, C# and UnrealScript, and for scripts saved by SQL Server Management Studio) are converted first, so their blank lines count as blank.

The standard measures (section 12) count **logical lines**: lines that are neither blank nor only a comment. Those come from scc itself; the script doesn't count them.

Some file types have lines removed before counting:

- **VB6 forms and controls** (`.frm`, `.ctl`, `.dsr`, `.pag`, `.dob`, `.cls`): the layout section before the first `Attribute VB_` line, and the `Attribute VB_` lines themselves, are not code. A `.cls` or `.bas` file that doesn't look like Visual Basic (for example a LaTeX class file) is not counted.
- **SQL scripts**: `INSERT` statements (with their continuation lines, `SET IDENTITY_INSERT` around them, and `GO` separators between them) are the data in a database, not its code. They are moved to the "Data, not code" section.
- **Access objects exported as text**: see [section 6](#6-codebases-inside-a-file-or-a-database).

### Languages it doesn't know: `--code-ext`

Files in a language the script doesn't know (a company's own language, say) are not counted as code. Instead, text files of unknown kinds among the owner's own code are listed, by extension, with their number and size, when there are at least five of them. (An extension is judged to be text by its first file: no NUL bytes in its first 4 KB.)

If some of them are code, run again with `--code-ext`:

```
--code-ext .par=PARLANSE
--code-ext ".atg=DMS grammar:Ada"
```

The part after `=` is the language's name in the report. In the main table every non-blank line of it counts, as for every language. The optional part after `:` is a known language whose comment syntax it shares: `text` (the default), `C`, `C++`, `Ada`, `SQL`, `Lisp`, `Python`, `Pascal`, `Lua` or `Visual Basic`. It is passed on to scc (as `--count-as-pattern`, so scc counts its comments as comments; with `text`, every non-blank line is a logical line) and to jscpd (as `--formats-exts`), so the standard measures include these files too. The option can be repeated. A specification it can't read stops the script with an explanation.

---

## 5. Game engines

The script is a general codebase inventory, but it understands game engines in depth, because a game's code is often spread across engine files, bought packages and visual scripts.

### Unity

- The editor version is read from `ProjectSettings/ProjectVersion.txt`.
- Build output folders at the project root are skipped (see section 3).
- Someone else's code inside `Assets` is separated out by several means (all described in [section 7](#7-own-code-versus-someone-elses)): `Plugins` folders, Unity's own add-ons (TextMesh Pro, Standard Assets, Samples, AssetStoreTools), the folder names of about 150 widely used Asset Store packages, folders laid out like an Asset Store package, and, most reliably, the guids of the Asset Store packages downloaded on the computer running the script.
- In `Packages/`, Unity's own `com.unity.*` packages are third-party; other embedded packages are the owner's. `Packages/manifest.json` is read for the list of package dependencies.
- `.js` files in `Assets` are labelled UnityScript.
- If the folder holds a *built* Unity game rather than the project (`UnityPlayer.dll`, `globalgamemanagers`, `GameAssembly.dll`, `Assembly-CSharp.dll` and their macOS/Linux equivalents, with no Unity project), the report says so, and says whether it is a Mono build (from which C# can be recovered) or an IL2CPP build (compiled to machine code).

### Unreal Engine 4 and 5

- The engine version comes from the `.uproject`. A custom-built engine is recognised (see "Custom-built and forked engines" below). UEFN projects are recognised and their Verse code counted.
- C++ is counted as code; `*.Build.cs`/`*.Target.cs` as build rules.
- **Blueprints and other visual scripting are counted in nodes.** The script reads the header tables of each `.uasset` and `.umap` (never the asset data itself) and counts the nodes in its graphs. Rows in the report: Blueprints, Widget Blueprints (UI), Animation Blueprints, Level Blueprints, Materials, Behavior trees (AI), and other node graphs (Niagara, sound cues, MetaSounds, Control Rig, PCG and similar). Comments, reroute knots and the editor's duplicate material graph nodes are not counted, just as blank lines aren't counted in code. Data-only Blueprints (that set values without logic) are counted as files with no nodes.
- The package reader handles every UE4 and UE5 file-summary layout from the earliest UE4 to UE 5.6, little- and big-endian (console builds), and the alternative tag used by some licensee games. The sizes of the import and export table entries vary with the version and in modified engines; the script works them out from where the tables start and end, and if that doesn't add up, tries each plausible size and keeps one only if every entry in the table makes sense. Packages larger than 256 MB have only their header read.
- **Cooked** assets (from a packaged game) have had their graphs stripped. They are counted as assets but contribute no nodes, and the report says how many there were.
- The report says how much could be measured: how many packages were read in full, how many were cooked, how many couldn't be read (and how many of those appear to hold Blueprint graphs, judged by tell-tale class names in their first 64 KB), how many are Git LFS placeholders that were never downloaded, and how many Blueprints have no nodes.
- Assets are classified by the class of the package's main object: levels, textures, 3D models, materials, animations, audio, visual effects, data tables, AI, cinematics, fonts, Blueprints. World Partition's per-actor files are grouped as "Level actors (World Partition)". The engine versions that saved the assets are listed.
- Plugins bought from the Marketplace or Fab, or Epic's own (their `.uplugin` has a `MarketplaceURL` or `FabURL`, says `Installed`, or was created by Epic), are third-party. Other plugins are the owner's. Epic's sample content directly under `Content/` (StarterContent, AnimStarterPack, Mannequin, LevelPrototyping, Megascans, Marketplace, Fab) is third-party.
- Files with Epic's copyright notice stay the owner's code (Unreal's templates put the notice on a project's first files, and developers keep it on files they start by copying those) but are counted and pointed out, so you can check none were copied from the engine.
- `#include`s of Unreal's own headers are expected and not reported as missing code.
- If the folder holds a packaged Unreal game (`.pak`/`.utoc` files without a project), the report says so.

### Unreal Engine 3

- Recognised by `Development/Src`. Epic's own UnrealScript and C++ packages (Core, Engine, Editor, UnrealEd, GameFramework, UTGame, UDKBase, the online subsystems and many more) are reported as "Unreal Engine's own code", separately from the licensee's packages beside them.
- Kismet and material nodes are counted from UE3 packages saved by package version 491 or later. Because the export table layout varies between UE3 versions and licensees, the count is only trusted if the table ends exactly where the next one starts. Compressed packages are treated as cooked.
- The per-folder breakdown shows `Development/Src/<package>` for UE3 trees.

### Unreal Engine 1 and 2

- Recognised by a `System` folder with `.u`/`.int` files beside the content folders, or by `Classes/*.uc` package folders.
- `.u` files are compiled UnrealScript packages, and they usually carry each class's source text. The script counts the classes and the source lines inside them. If the `.uc` source files are also present, the report says the `.u` holds the same classes; if not, it says the `.u` is the only copy of the source (which is then not added to the code count).
- Epic's packages (Core, Engine, Botpack, UnrealShare, XGame and so on) are counted as the engine's.
- Level, texture, sound, music, mesh and animation packages (`.unr`, `.ut2`, `.utx`, `.uax`, `.umx`, `.usx`, `.ukx` ...) are identified and counted as assets.

### Custom-built and forked engines

- A project whose `EngineAssociation` is not a version number is built with a custom engine. The script looks the engine up where Unreal registers source builds (the Windows registry, or `Install.ini` on macOS and Linux), or, if the association is empty, in up to five folders above the project. If found outside the scanned folder (or in a different repository), the engine gets its own section with its version and version-control history. If not found, the report says to run the script on the engine's folder too.
- A source copy of the engine inside the scanned folder is reported as "Unreal Engine's own code (Epic's, possibly with the studio's changes)", separately from the game's code.
- For an engine fork in Git, see "Unreal Engine forks" in [section 9](#9-version-control).

### Godot

Version from `project.godot`. GDScript and Godot shaders are counted. `addons/` at the project root is third-party, each addon named by its folder. `.godot` and `.import` are skipped. `.tres` resources and `.tscn` scenes are counted as assets. C++ `#include`s in a Godot project are attributed to godot-cpp rather than reported as missing.

### GameMaker

Studio 1 and 2 projects are recognised, GML is counted, and `options` and `tmp` at the root are skipped.

### Ren'Py

- `.rpy` and `.rpym` are counted as Ren'Py code.
- `game/tl/` holds the game's text translated into other languages, often most of a Ren'Py game's lines. It is reported as "Translations", not code. (A `tl` folder outside a Ren'Py game is ordinary code.)
- A released game ships the engine (`renpy/`) and a copy of Python (`lib/`) beside `game/`; both are third-party. `python-packages` folders (where Ren'Py games bundle pip libraries) are third-party.
- If there are compiled scripts (`.rpyc`) or archives (`.rpa`) but no `.rpy` source, the report says the source is missing or packed into archives.

### Others

- **Defold**: `.script`, `.gui_script` and `.render_script` are counted as Lua.
- **RPG Maker MV/MZ**: the engine's own `rpg_*.js`/`rmmz_*.js` files and the libraries it ships (PIXI, Effekseer, lz-string, localforage ...) are third-party; plugins are the owner's.
- **Construct**: recognised, but its event sheets (its logic) are not counted, and the project type says so.
- **LÖVE, Source engine, CRYENGINE, Stride, Flax, MonoGame, XNA, Haxe, Ogre3D**: recognised and listed; their code is counted by language. Files carrying Valve's, Crytek's, Unity Technologies' or Amazon's (Lumberyard/O3DE) copyright notice are pointed out, as with Epic's.

### Console code

Code in console-platform folders (`PS4`, `PS5`, `Orbis`, `Prospero`, `XboxOne`, `XboxSeries`, `Scarlett`, `GDK`, `NX`, `WiiU`, `3DS` and similar; `Switch`, `Xbox`, `PlayStation`, `Nintendo` and `Sony` only when they sit beside other platform folders) or in files whose names mark a console (`_ps5.`, `.xsx.`, `-nx64.` ...) is counted as the owner's but pointed out: it is usually under the platform holder's NDA, which may keep it out of a sale or licence.

---

## 6. Codebases inside a file or a database

Much of a business system's code can live inside database files rather than source files. The script reads these and adds their code to the language table, under labels that say where it came from (for example "SQL (in Access queries)" or "T-SQL (in the SQL Server database)"). A "Databases" section summarises what was found.

### Microsoft Access (`.accdb`, `.mdb`, `.accda`, `.accde`, `.mde`, `.mda`, `.adp`, `.ade`)

The format is identified from the file's first bytes: Access 97 or earlier (Jet 3), Access 2000-2003 (Jet 4), Access 2007 or later (ACE), or an Access Data Project (a front end for SQL Server). A database is **compiled** if its extension says so (`.mde`, `.accde`, `.ade`), or if its properties say MDE (which catches an `.accde` renamed to `.accdb`). A compiled database has had its VBA source removed, and the report says so.

How much can be read depends on the computer:

- **Windows with Microsoft Access installed**: everything. The script copies the database to a temporary folder and drives Access through PowerShell, with macros and code disabled; if Access can't confirm they are disabled, the database isn't opened. With `--offline`, Access isn't used at all, because opening a database can make Access connect to the tables it links to on other computers (a server, or a back-end database on a network share); mdbtools is used instead, if installed. It reads the number of forms, reports, macros and modules, every query's SQL, the tables (and how many are linked over ODBC, for example to SQL Server, meaning the data lives there), and the source of every VBA module, including the code behind forms and reports. The copy is deleted afterwards.
- **Elsewhere, or without Access, with mdbtools installed**: everything except VBA. Query SQL comes from `mdb-queries`; the numbers of forms, reports, macros, modules and tables come from Access's object catalog. mdbtools gives each query's SQL on one line, so it is counted as Access shows it: one line per clause (`FROM`, `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, `UNION` ...).
- **Neither**: the database is listed and counted as a data file, and the report says to run the script on Windows with Access installed (or, with `--offline`, that Access wasn't used because of it).

Queries whose names begin with `~` are the record sources of forms and reports, and are labelled "SQL (in Access forms and reports)". VBA from the database is also searched for authors named in comments (see [section 10](#10-contributors)).

Databases inside third-party folders are listed but not opened.

Because an Access database holds its tables in the same file as its code, each one is also listed under "Files holding data" (see [section 8](#8-generated-code-data-duplicates-and-other-things-that-are-not-counted-as-own-code)).

### Access objects exported as text

Many teams keep Access code in version control by exporting each object as text (with `SaveAsText` or the msaccess-vcs add-in). The script recognises these exports by their first lines, whatever their extension (`.bas`, `.txt`, `.form`, `.report`, `.macro`, `.qry`, `.mac`, `.frm`, `.rpt`):

- **Forms and reports**: only the VBA after `CodeBehindForm`/`CodeBehindReport` is counted, without `Attribute VB_` lines. The layout (which holds hex blobs such as printer settings) is not code and is not mistaken for embedded data.
- **Queries**: the SQL is decoded from `dbMemo "SQL"` and counted. A query saved in Access's design grid instead is counted one line per table, column, join and condition, and the report says so. If the add-in saved the SQL in a `.sql` file beside the query, only the `.sql` file is counted.
- **Macros**: counted as objects, not lines.

If the folder holds both a database and its text export, the code is counted once: when the exported forms and reports number at least half of the database's, the database's own code is left out, and the report says it was counted from the export.

### SQL scripts (`.sql`, `.tsql`)

- Each object a script creates or alters (procedures, functions, views, triggers, tables, types, synonyms, sequences, schemas) is counted once by its schema-qualified name (schema `dbo` when none is given), however many scripts alter it. Temporary tables and table variables are ignored.
- `INSERT` statements are data, not code (see section 4). A script with them is also listed under "Files holding data".
- UTF-16 and UTF-8-with-BOM scripts (as SQL Server Management Studio saves them) are read correctly.

### `.dacpac` and `.bacpac` packages

These are zip files describing a SQL Server database. The script reads `model.xml` to count objects by kind, and counts the bodies of procedures, functions, views and triggers as "T-SQL (in .dacpac / .bacpac packages)", **unless the same object is already defined in a `.sql` script** in the folder, so that a database project and its built package are not counted twice. Pre- and post-deployment scripts are counted as SQL, with their `INSERT`s as data. A `.bacpac` also holds every table's rows; only its schema is read, and it is listed as a data file.

### SQL Server databases (`--sql-server`)

Code that exists only inside a running SQL Server is read with `--sql-server SERVER` (repeatable). The script uses `sqlcmd` (found on `PATH` or in its usual install folders on Windows and Linux) and signs in with Windows authentication, unless `SQLCMDUSER` and `SQLCMDPASSWORD` are set in the environment, in which case `sqlcmd` uses those. `sqlcmd` checks the server's certificate (newer versions encrypt, and check the certificate, by default). If that fails, as it does for a server with its own self-signed certificate, the report says so; for a server you trust, add `--trust-server-certificate`, which passes `sqlcmd` its `-C` option. `--sql-server` can't be combined with `--offline`.

It reads every user database that is online, or only those named with `--sql-database`. From each it reads the definitions of user-created modules (stored procedures, functions, views, triggers, rules) from `sys.sql_modules`, and the number of user tables. Nothing else is queried. Each definition is counted as "T-SQL (in the SQL Server database)", unless the same object (by schema and name) was already counted from a `.sql` script.

### SQL Server data files and backups

`.mdf`, `.ndf`, `.ldf`, `.bak` and `.trn` files are counted, but the code inside them can't be read from the files. A `.bak` or `.trn` file counts only if it is in Microsoft Tape Format (it begins with `TAPE`), as SQL Server's backups are; other programs' backup copies (an editor's, a game engine's) are skipped. The report says so, suggests `--sql-server` or exporting the code, and lists them as data files.

### SSIS and SSRS

- **SSIS packages** (`.dtsx`, or a whole project in an `.ispac`): SQL statements from Execute SQL tasks and data-flow commands are counted as "SQL (in SSIS packages)", and the code of script tasks (their `ScriptMain` C# or VB.NET, not designer files) as "C# (in SSIS script tasks)" or "VB.NET (in SSIS script tasks)".
- **SSRS reports** (`.rdl`, `.rdlc`): dataset queries (`CommandText`) are counted as "SQL (in SSRS reports)", and custom code blocks as "VB.NET (in SSRS reports)".

### Code embedded in binary assets

The same idea applies to Unreal: visual-scripting graphs inside `.uasset`/`.umap` packages are counted in nodes, and UnrealScript source carried inside UE1/UE2 `.u` packages is counted in lines (section 5).

---

## 7. Own code versus someone else's

The main code table is headed "Apparently original source code". This is code that *looks* like the owner's own. It is not a finding on legal ownership or licensing rights, and the report says so.

Every folder inherits a category from its parent: own, test, third-party, or engine (Epic's). Files can then be placed in a different category. The mechanisms below are applied in roughly this order; a hand mark (`--own` or `--third-party`) overrides all of them.

### By folder name

Child folders of the owner's code are third-party if they are named:

- `vendor`, `vendors`, `_vendor`, `vendored`, `third_party`, `thirdparty`, `third-party`, `external`, `externals`, `extern`, `python-packages`, or `fonts` (font vendors' demo pages and CSS). The libraries inside are named by their subfolders (so `ThirdParty/boost` is listed as "boost").
- The name of a library often copied straight into source folders: about 130 names, such as `boost`, `sqlite`, `zlib`, `libpng`, `eigen`, `glm`, `rapidjson`, `nlohmann`, `fmt`, `spdlog`, `imgui`, `freetype`, `bullet`, `physx`, `openssl`, `curl`, `protobuf`, `googletest`, `catch2`, `stb`, `tinyxml2`, `pugixml`, `asio`, `box2d`, `luajit`, `sol2`, `enet`, `libuv`, `recastnavigation`, `abseil`, `tbb`, `openal-soft`, `bgfx`, `mimalloc`, `tracy`, `harfbuzz`, `icu`, `libsodium`, `mbedtls`, `grpc`, `poco`, `unlua`, `discord_game_sdk`.
- In a Unity project's `Assets`: `Plugins` anywhere; `TextMesh Pro`, `Samples`, `Standard Assets*`, `Sample Assets`, `AssetStoreTools` directly in `Assets`; and the folder names of widely used Asset Store packages anywhere under `Assets` (DOTween, Odin/Sirenix, PlayMaker, Rewired, Photon, UniRx, Final IK, Amplify, Gaia, Easy Save, Behavior Designer, Dialogue System, Feel/MoreMountains, Animancer, A* Pathfinding, NGUI, LeanTween, Zenject, FMOD, Wwise, Spine, Steamworks.NET, ad and analytics SDKs, and about a hundred more).
- In a Unity project's `Packages`: `com.unity.*`.
- In a Godot project: `addons` at the root.
- In a Ren'Py game: `renpy` and `lib` at the root.
- In an Unreal project's `Content`: Epic's sample content and asset packs (listed in section 5).

Folders named `test`, `tests`, `__tests__`, `spec`, `specs`, `e2e`, `EditMode` or `PlayMode`, and files named like tests (`test_*.py`, `*_test.py`, `conftest.py`, `*.test.js`, `*.spec.ts` ...), are the owner's code but counted as tests, shown in the table's "of which tests" line.

### Unity Asset Store packages

Asset Store packages unpack into folders with any name under `Assets`, so folder names are not enough. Three further checks:

1. **Packages downloaded on this computer.** When a Unity project is found, the script reads the `.unitypackage` files in Unity's Asset Store download folder (`%APPDATA%\Unity\Asset Store*` on Windows, `~/Library/Unity/Asset Store*` on macOS, `~/.local/share/unity3d/Asset Store*` on Linux, plus `ASSETSTORE_CACHE_PATH` if set). It reads only the names of the entries in each package, which are the guids of its assets. Unity keeps an asset's guid in its `.meta` file when importing it, so a folder or file in the project whose `.meta` guid matches is recognised as that package's, **even if it was moved or renamed**. Packages are read smallest first (code packages before large art packs), for at most 300 seconds in total. The report says how many of the downloaded packages were read. Unreadable packages are skipped.
2. **Package layout.** A folder under `Assets` with both documentation (`Documentation`, `Docs`, `Manual`, `Help`) and demo (`Demo`, `Demos`, `Example`, `Examples`, `Demo Scenes` ...) subfolders, or with a readme, manual, changelog or licence file that mentions the Asset Store (`assetstore.unity.com`, `u3d.as/`, "Asset Store"), is treated as a package.
3. **Known folder names**, above.

### Unreal plugins and engine code

See section 5: bought and Epic plugins by their `.uplugin`, Epic's sample content by folder, Epic's UE1-3 packages by name (only when they hold `Classes`, `Inc` or `Src`), a source copy of the engine by `Build/Build.version`, and Epic's `.u` packages by name.

### Licence files in folders

A folder (other than the scanned folder itself) holding its own `LICENSE`, `LICENCE`, `COPYING` or `COPYRIGHT` file is judged by where it sits:

- If it is not itself a project root and its parent folder holds code files, it is a library copied in among the owner's code, and is third-party.
- Otherwise (for example `Plugins/X` or `Mods/X`, a package among other packages), it may well be the owner's own open-sourced code. It stays the owner's, but is listed under "Folders with their own licence file, counted as original code" with its line count, so you can check it.

### Licence headers in files

The first 6 KB of every code file is checked for a licence notice: the Boost licence, SQLite's public-domain dedication, MIT ("Permission is hereby granted, free of charge"), Apache, GPL/LGPL/AGPL, BSD ("Redistribution and use in source and binary forms"), zlib, MPL, Unlicense/CC0, or the matching `SPDX-License-Identifier`. A file with one, among the owner's code, is moved to third-party and listed under that licence.

Engine makers' notices (Epic's, Valve's, Crytek's, Unity Technologies', Amazon's) are different: they are **not** taken as a sign of someone else's code, because files started from an engine's templates keep them. Those files stay the owner's, but the number of lines carrying each notice is shown so you can check.

### Known library files

Single files from well-known libraries are recognised by name wherever they are: the SQLite amalgamation (`sqlite3*.c/h`), `stb_*.h`, Dear ImGui's files, `json.hpp`, miniz/lz4/xxhash/zstd, TinyXML/pugixml, common single-header libraries (`httplib.h`, `cgltf.h`, `miniaudio.h`, `dr_*.h`, `picojson.h`, `rapidxml*.hpp`, `cxxopts.hpp`, `doctest.h`), FastNoise, moodycamel's queues, and RPG Maker's engine and library files.

### Git submodules

Submodules listed in a `.gitmodules` file are third-party if their URL's owner (the account or organisation on the hosting service) differs from the owner of the repository containing them. Submodules from the same owner stay the owner's. The report lists how many submodules there are and which were counted as someone else's.

### Package managers and manifests

Dependencies installed by package managers (`node_modules`, `site-packages`, virtual environments, `Pods`, NuGet's `packages`, and so on) are skipped entirely. Their manifests are read to list what the project depends on (see [section 11](#11-other-findings)).

### The per-folder breakdown

The report shows the owner's code by folder (top 15), so a library that slipped through is easy to spot. It starts from the top-level folders, showing two levels for common source roots (`Assets/`, `src/`, `Source/`, `packages/`, `apps/`, `lib/`, `libs/`, `game/`, `Plugins/`, `Content/`, `script/`, `scripts/`). If one folder holds more than half of all the code, it is opened up into its subfolders, so that, for example, a `boost` folder copied into `Source/MyGame` shows up on its own line.

### Correcting it by hand: `--own` and `--third-party`

If a folder or file is in the wrong category, name it:

```
--third-party Source/Game/SomeLib --own Plugins/MyPlugin
```

Paths are relative to the scanned folder, or absolute. Both options can be repeated and apply to folders or single files. A hand mark overrides every rule above, including for folders inside a third-party folder (so you can mark one plugin inside `Plugins` as your own). The report notes how many paths were marked. A folder marked third-party is listed under its folder name; a file under its file name.

---

## 8. Generated code, data, duplicates and other things that are not counted as own code

### Generated and minified code

A file is generated, and reported separately from the owner's code, if:

- its name says so: `*.min.js`, `*.min.css`, `*.bundle.js`, `*.Designer.cs`, `*.g.cs`, `*.generated.*`, `*_pb2.py`, `*_pb2_grpc.py`, `*.pb.cc`, `*.pb.h`, `*_generated.h`, Qt's `moc_*.cpp`, `ui_*.h` and `qrc_*.cpp`, SWIG's `*_wrap.c`/`*_wrap.cxx`, `lex.yy.c`, Bison's `*.tab.c`/`*.tab.h`;
- its first 1,500 bytes contain "auto-generated", "autogenerated", "@generated" or "do not edit"; or
- it is a JavaScript or CSS file over 20 KB whose lines average more than 300 bytes (minified).

### Data embedded in code

Images, fonts, sounds and lookup tables are often pasted into source files as arrays of numbers. A file of at least 40 non-blank lines is treated as data if at least 80% of a sample of its lines are nothing but comma-separated numbers, hex values, character literals or byte strings. Such files go to "Data, not code". (Each value is checked separately, so a single enormous line of digits can't stall the scan.)

### Files holding data

What is being inventoried is the code, and data files may hold customers' data. The report lists, with their sizes, files that should stay out of whatever is shared:

- Access databases (their tables are in the same file as the code);
- SQL Server database files and backups;
- `.bacpac` exports;
- SQL scripts with `INSERT` statements;
- data files of at least 100 KB outside third-party folders: `.csv`, `.tsv`, `.xls`, `.xlsx`, `.xlsm`, `.ods`, `.parquet`, `.avro`, `.orc`, `.feather`, `.jsonl`, `.ndjson`, `.sqlite`, `.sqlite3`, `.db`, `.db3`, `.sdf`, `.dbf`, `.fdb`, `.gdb`, `.dmp`, `.dump`, `.bcp` (not `Thumbs.db`).

It then explains how to share the code without the data: SQL Server Management Studio's "Generate Scripts" with "Schema only", or a `.dacpac`; for Access, exporting objects as text, emptying the tables, or sharing only the front end of a split database; for data files, leaving them out or substituting sample data.

### Exact duplicates

Among the owner's code, a file whose contents are byte-for-byte identical to another file already counted (compared by SHA-1) is a duplicate: a backup, or the same code kept in two places. The report gives the lines in duplicate files and the total without them. (Near-duplicates and copy-pasted fragments are measured separately, by the duplication ratio in section 12.)

### Precompiled libraries

`.dll`, `.lib`, `.a`, `.so`, `.dylib`, `.jar`, `.aar`, `.bpl`, `.ocx` and `.pyd` files are counted, split between the owner's folders and third-party folders. They have no source in the folder, so they can't be licensed as source.

### Build output

Build output is skipped by the folder rules in section 3. In addition, scc and jscpd leave out files that `.gitignore` files ignore, so those are in the main table but not in the standard measures.

### Files not committed

In a Git repository, the owner's code files that Git doesn't track are counted and pointed out: they exist only in this copy.

---

## 9. Version control

### Which systems, and how each is read

The script looks for each system's marker in the scanned folder or any of the six folders above it, so a subfolder of a working copy is recognised. It then reads the history with that system's own command-line tool. On Windows it also looks for the tools where GitHub Desktop, SourceTree, TortoiseSVN, TortoiseHg, P4V, Plastic/Unity Version Control, Visual Studio, Breezy, Fossil and CVSNT install them, since those are often not on `PATH`.

| System | Marker | How the history is read | Unit |
|---|---|---|---|
| Git | `git rev-parse` succeeds, or `.git` | `git log --all` (every branch), names and emails through the repository's `.mailmap` | commits |
| Perforce | `p4` reports submitted changes for the folder; or `.p4config`, `.p4ignore`, `p4config.txt` (or the file `P4CONFIG` names) | `p4 changes -l -s submitted <folder>/...` | submitted changelists |
| SVN | `.svn` | `svn log --xml -r HEAD:1` (up to the newest revision on the server, not just the checkout's), falling back to the checkout's own history | revisions |
| Mercurial | `.hg` | `hg log`, ignoring the repository's own settings (Mercurial 5.4 or later; an older one isn't run, and the report says so) | commits (merges from the second parent) |
| Plastic SCM / Unity Version Control | `.plastic` | `cm find changeset` (all branches, with dates in ISO form, `--dateformat=o`; fields split by control characters, as comments can hold anything), without changeset 0, the empty one every repository starts with; merges from `cm find merge` (not cherry-picks); code reviews from `cm find review` | changesets (on `/main`, for the forms) |
| Team Foundation (TFVC) | `$tf`, `.$tf`, `.tfignore` | `tf history . /recursive` | changesets |
| Bazaar | `.bzr` | `brz log`, or `bzr log` | revisions |
| Fossil | `.fslckout`, `_FOSSIL_` | `fossil timeline` (check-ins only, without the initial empty check-in) | check-ins |
| Darcs | `_darcs` | `darcs log --xml-output` | patches |
| CVS | `CVS/Root` | `cvs log`: file revisions grouped into commits by commit id, or, from before CVS had them, by the same author, minute and message | commits |
| Visual SourceSafe | its database (see below) | read directly from the database files | check-ins |
| Jujutsu | `.jj` | beside Git (colocated, the default), through Git; otherwise not readable here | |
| Unity Collaborate, SourceGear Vault | `.collabignore`, `_sgvault` | not readable here; the report asks for an export | |
| Lore (Epic's, 2026), Diversion, Sapling, Pijul, BitKeeper, Monotone, GNU Arch, ClearCase, Rational Team Concert, Rational Synergy, PTC Integrity (MKS), StarTeam, Surround SCM, CA Harvest, Veracity, RCS, SCCS | `.lore`/`.loreignore`, `.diversion`/`.dvignore`, `.sl`, `.pijul`, `BitKeeper/etc`, `_MTN`, `{arch}`, `.view.dat`/`view.dat` (one naming its view), `.jazz5`, `_ccmwaid.inf`, `project.pj`, `.sbas`, `.MySCMServerInfo`, `harvest.sig`, `.sgdrawer`, `RCS/` (holding `,v` files), `SCCS/` (holding `s.` files) | not readable here (their tools need their server and a login, are rarely installed, or would obey the working copy's own settings); the report asks for an export | |

If a system is found but its tool isn't installed, or reads no history, the report says so (for example "Bazaar (but the brz command isn't installed, so no history)", or "Perforce (no history: is p4 installed and logged in?)"). Perforce is detected by asking `p4` itself, because its settings often live in the registry or environment rather than in a file.

All commands are told not to prompt for passwords (`GIT_TERMINAL_PROMPT=0`, Git Credential Manager non-interactive, Git's SSH in batch mode, `svn --non-interactive`), and run with UTF-8 output and with time limits. `p4` is run with `PWD` set to the folder, because it finds its `P4CONFIG` settings from `PWD`.

A copied repository's own settings could make these tools start programs, so the script switches those off: for Git, hooks, fsmonitor, external diff and textconv programs, signature checks, credential helpers and every network transport (except when it asks a server, from outside the repository); for Mercurial, the repository's whole `.hg/hgrc`; for Darcs, hooks. A CVS root or a Perforce settings file that would start a program to reach the server isn't used. [SECURITY.md](SECURITY.md) lists each of these.

**Git ownership.** Git refuses to read a repository that belongs to another user account (common on external drives and in folders copied from another computer), because its settings could run programs as whoever reads it. When Git refuses one for that reason, the script runs the same command again naming that one repository as safe (`safe.directory=<that repository>`, on the command line only), with the settings above still switched off. It never trusts every repository (`safe.directory=*`), and doesn't change Git's own settings. The report says when this happened.

**With `--offline`**, histories that come from a server aren't read: Perforce, Plastic, TFVC, and SVN, CVS or Bazaar when the history isn't on this computer (an SVN repository at a `file://` address, a local CVS root, a Bazaar branch that isn't a lightweight checkout of one elsewhere). The report lists what was left out. Git, Mercurial, Fossil and Darcs keep the whole history in the working copy, so they are read as usual.

Dates: TFVC prints dates in the computer's local format, so only the year is used from them; so does Plastic, from a `cm` too old to take `--dateformat`. Plastic leaves out changesets on hidden branches unless asked for them; the script doesn't ask, so a repository with hidden branches has those changesets left out.

### What each history reports

For each history: the number of changes; for Git, how many are on the branch that is checked out, and how many are merge commits; the number of contributors (see section 10); first and last change; the busiest person's share of the changes; changes per year; pull requests and code reviews found; and notes.

For Git, it also notes:

- a **shallow clone** (older history is missing; run `git fetch --unshallow`);
- commits **dated before Git existed** (7 April 2005), which must have been converted from an earlier system;
- history **imported from other systems** (see "Projects that moved between systems" below).

Every history notes changes **dated before its system existed** (SVN before October 2000, Git and Mercurial before April 2005, Plastic before 2006 and so on), which must have been converted from an earlier one, and the markers of conversion tools in its messages, one per original change:

| Marker in the message | Tool | Converted from |
|---|---|---|
| `git-svn-id: <url>@<revision> <uuid>` | git-svn (and svn2git with `--metadata`, Atlassian's scripts) | SVN |
| `svn path=...; revision=N` | KDE's svn2git (svn-all-fast-export) with `--add-metadata` | SVN |
| `[git-p4: depot-paths = ...: change = N]` | git-p4 | Perforce |
| `[p4-fusion: depot-paths = ...: change = N]` | p4-fusion | Perforce |
| `Copied from Perforce` / ` Change: N` | Perforce Git Fusion, cloning from Perforce | Perforce |
| `Imported from Git` ... ` sha1: <hash>` | Perforce Git Fusion, in changelists pushed from Git | Git |
| `git-tfs-id: [...]$/path;CN` | git-tfs | TFVC |
| `{06/03/2002 12.30 PM}` at the start | Microsoft's VSSConverter (SourceSafe to TFS) | SourceSafe |
| `(vss N)` at the end | VSSMigrate | SourceSafe |
| `This commit was manufactured by cvs2svn ...` | cvs2svn / cvs2git (commits they make up for branches and tags) | CVS |
| `--HG--` | hg-git | Mercurial |
| `--BZR--` | Breezy's Git support (round-tripping) | Bazaar |
| `Legacy-ID: ...` | reposurgeon (`write --legacy`) | any |

And what tools leave elsewhere: in Git, SubGit's `refs/svn/map`, git-tf's `TFS_C<N>` tags, p4-fusion's `refs/cl/`, `refs/notes/hg` (git-remote-hg, hg-fast-export), git-cinnabar's refs, and the `.git/svn`, `.git/git-tf`, `.git/hg2git-mapping` and `.git/cvs-revisions` files of git-svn, git-tf, hg-fast-export and git cvsimport; in Mercurial, the `convert_revision` that `hg convert` records in each changeset (an SVN revision, a Git commit, a Perforce changelist) and hg-git's `.hg/git-mapfile`; in Bazaar, revision ids that name an SVN revision (bzr-svn) or a Git commit; in Fossil, the `svn-rev-N` tags of `fossil import --svn`.

When a subfolder of a Git repository is scanned, only the commits that touched that subfolder are counted (with `--full-history`, so merge commits that brought changes into it are kept).

### Pull requests and code reviews

Pull requests are found three ways, and each is reported separately:

1. **In commit messages.** "Merge pull request #N" (GitHub, Bitbucket Server), "Merged in branch (pull request #N)" (Bitbucket Cloud), "See merge request group/project!N" (GitLab), "Merged PR N:" (Azure DevOps), and GitHub squash merges ending in "(#N)". Each numbering scheme is kept separate, and each number is counted once however many commits mention it. Code reviews are found the same way: Gerrit `Change-Id`s, Phabricator `Differential Revision`s, and Perforce Swarm `#review-N`. These are read from the change messages of every system the script reads messages from: all of them except TFVC (whose history is read without messages) and SourceSafe.
2. **On the Git server.** GitHub, GitLab and Bitbucket Server keep a ref for every pull request ever opened (`refs/pull/N/...`, `refs/merge-requests/N/...`, `refs/pull-requests/N/...`). `git ls-remote` on each remote counts them: open, closed and merged. A remote that can't be reached is reported as "couldn't connect", not as zero pull requests. A remote that is a folder on a network share isn't asked (it keeps no pull requests, and the repository's settings could name any computer). Not with `--offline`.
3. **Through GitHub's API**, if `gh` is installed and logged in: the number of merged pull requests for each GitHub remote. Not with `--offline`.

Plastic code reviews are counted with `cm find review`.

If none are found in a Git repository, the report says "none found in commit messages or on the server (which doesn't mean there were none)", or, with `--offline`, that the server wasn't asked. The summary uses the largest pull-request count found.

### Unreal Engine forks

Studios that modify Unreal Engine often keep a fork of Epic's repository, which carries hundreds of thousands of Epic's commits. The script tells them apart:

- Commits whose message ends like `[CL 16428889 by ... in ue5-main branch]` (as every commit in Epic's repository does), or whose author email is at `epicgames.com` or `epicgames.net`, are Epic's. They are counted on a separate line and left out of everything else: commit counts, contributors, pull requests and the standard measures.
- **How much the studio changed Epic's code**: the studio's branch is the local branch with the most non-Epic commits (checking `HEAD` and up to 30 branches), even if Epic's release branch happens to be checked out. The report shows the newest Epic changelist on that branch, and the files changed and lines added and removed between it and the branch.
- **An engine repository that starts from a copy of Epic's source** rather than Epic's history: the script adds up the files changed and lines added and removed in the studio's non-merge commits, leaving out bulk imports (commits touching at least 3,000 files or adding at least 300,000 lines, which bring in new versions of Epic's code). The report says how many bulk imports were left out.
- Pull requests on Epic's own GitHub repository are never counted.

### Visual SourceSafe

Microsoft stopped selling SourceSafe in 2005 and its command line (`ss.exe`) is rarely installed, so the script reads the database files directly, using the same record layout that vss2git, vss2svn and py-vss read.

**Finding the database.** A SourceSafe database is a folder with `srcsafe.ini` and a `data` folder. The script finds it:

- inside the scanned folder (the database's own files are then not counted as code);
- through the `SSDIR` environment variable (with `--offline`, not if it names a network share);
- where the project files say it is: `SccAuxPath` entries in `.sln`, `.vcproj`, `.vcxproj`, `.csproj`, `.vbproj` and `.scc` files. These locations are shown on screen only, never saved in the report (a server's name isn't for the report). One on this computer is read if it's there. One on a network share is opened only with `--network-sourcesafe`, since project files could name any computer: without it, the report says to add `--network-sourcesafe`, or to name it with `--sourcesafe`;
- with `--sourcesafe <folder>`, which may be on a network share (but not with `--offline`).

SourceSafe has no server program, so a copy of the database from a backup or an old disk works as well as the original, as does a copy without `srcsafe.ini`, or the `data` folder on its own. The `Data_Path` setting in `srcsafe.ini` is honoured, unless it points to a network share; then the database's own `data` folder is read instead, unless `--network-sourcesafe` is given. Up to five databases are read.

**Reading it.** Every revision of every file is a record. Records with a wrong check value (a CRC-32 folded to 16 bits) are left out and counted as damaged in a note. Labels are counted separately. Actions that are not a change of their own (labels, "added" in a project, which duplicates "created" in the file's own record, and archive/restore) are left out.

**Check-ins.** SourceSafe has no commits, so revisions are grouped into check-ins the way vss2git groups them: by the same person, either within 30 seconds of each other, or with the same comment within 10 minutes. The report shows check-ins, the file revisions in them, contributors, dates, labels, and the number of files and projects in the database.

**When the database isn't there.** If the code was evidently kept in SourceSafe (folders still hold `vssver.scc`/`vssver2.scc` binding files, project files name a database, or Git commit messages mention SourceSafe or vss2git) but no database was found, the report explains how to add it with `--sourcesafe`, and mentions any Git commits dated before 2005 that suggest part of it was already converted. SourceSafe archive files (`.ssa`) are pointed out; the script can't read them, and the report explains how to restore one with SourceSafe Administrator.

### Projects that moved between systems

A project that moved from one system to another (SourceSafe to SVN to Git, CVS to Mercurial, Perforce to Plastic ...), maybe more than once, often still has the older systems' histories, and the newer ones often hold them too, whole or in part. When a folder has histories in more than one system (including SourceSafe databases, and a mirror such as Plastic's GitSync), the report puts them together under "<systems> together", with each change counted once, in the newest system that has it.

**Finding the same change in two histories**, in this order:

1. **A conversion marker** in one names the change in the other: git-svn's revision number in an SVN history's revisions, git-p4's changelist in Perforce's, git-tfs's changeset in TFVC's, Git Fusion's commit hash in Git's, `hg convert`'s recorded revision, bzr-svn's revision id, hg-git's map.
2. **The same message within two days** (time zones; a conversion run overnight). The message is its first line, without what conversion tools add (the marker lines above, VSSConverter's date, p4-fusion's changelist number, VSSMigrate's file version), ignoring case and spacing; empty messages and CVS's `*** empty log message ***` match nothing. Where one system only gives the year (TFVC), the same message in the same year.
3. **The same message of at least 24 characters, found once in each history**, on any date: some conversions date every change the day they ran.

**How two histories fit together**, the one that starts first being the older (on the same day, the older system; and Git as the newest, so a mirror of a Git repository is counted in Git):

- **Converted**: at least half of the older history's changes are in the newer one, or (for histories with too few messages to go by, such as SourceSafe's) the newer starts within 31 days of the older and has changes on at least half of the days the older has them. The older history's changes during the newer one's are counted in the newer; those from before it starts (a partial conversion) or after it ends are added. If the newer dates the converted changes when the conversion ran (half of them more than two days off), all of the older's are taken to be in it.
- **One after the other**: the older ends on or before the day the newer starts. Both are added (any changes found in both, once).
- **Overlapping**: both were in use for a while, for the same work: at least a tenth of the older history's changes in that time are in the newer, or one of them has too few messages to tell. That time is counted once, from the newer.
- **Side by side**: both were in use at the same time with messages that don't match (say, Perforce for the art and Git for the code). Both are counted in full.

With three or more systems, each pair is worked out, and each older history is described with the first newer one that holds its work. A change counted in any newer history isn't counted again, so a chain such as SourceSafe, converted into SVN, converted into Git, counts each change once.

The report gives each history's size and dates, a sentence on how each older one fits with a newer one, and the total ("Together, without counting it twice: N changes from ... to ..."). The summary gives the total and the chain ("SourceSafe, converted into SVN, converted into Git"). In the standard measures, a history wholly held in another isn't counted as another repository, nor are its commits; commits found in two histories are counted once; and the history to deliver is that of the systems still holding something of their own.

**A Git history that starts with a bulk import.** If one of Git's root commits (dated after Git existed) adds at least 300 files, the report notes that the code was copied in from somewhere else and its earlier history isn't in Git.

**Repositories inside the scanned folder** with histories in more than one system are fitted together the same way, in their own section.

### Repositories inside the scanned folder, and engines outside it

- Repositories found inside the scanned folder (say, `Game/` and `Tools/` side by side, or a submodule) get their own history sections, up to ten. Systems that put a marker folder in every folder (old SVN, CVS) are counted once, at their top folder. A repository is not reported twice if it is the same Git repository as the scanned folder.
- A custom-built Unreal Engine found elsewhere on the computer gets its own section (section 5).

### Caveats printed with every history

The report reminds the reader that the numbers count what this copy of the history holds: commits on all branches include unmerged work; squash merges turn many commits into one; deleted branches, and history from before an import or migration, are missing; and pull requests are found only where the hosting service leaves traces in the repository, so the count from the hosting service itself is the authoritative one.

### When there is no version control

The report says so, and shows the range of years in which the source files were last modified (noting that copying can reset file dates). If all the owner's files were modified within one day, it says that's when the files were copied or unzipped, not when the code was written. If the folder looks like a downloaded archive rather than a repository (its name ends in `-main`, `-master`, `-develop`, `-trunk`, `-release`, `-default` or a commit hash, or all its files were modified within an hour), it suggests running the script on a clone instead.

---

## 10. Contributors

### Merging identities

People commit under several names and addresses. The script groups identities that belong to one person (with a union-find over every author seen):

- An author's identities are their name and email (or just a user name, for systems like Perforce and SVN). Comparisons ignore case.
- Two authors are the same person if they share an **email address**, a **full name** (one with a space in it), or a **distinctive handle** (at least five characters and not a common first name).
- GitHub's privacy addresses (`12345+jane@users.noreply.github.com`) are reduced to the user name (`jane`), which ties them to the same person's other identities.
- A lone first name ("alex") never ties identities together, nor do shared defaults: `root`, `admin`, `administrator`, `user`, `build`, `buildbot`, `jenkins`, `teamcity`, `ci`, `github`, `gitlab`, `dev`, `developer`, `default`, `unknown`, `none`, `anonymous`, `system`, `unity`, `unreal`, `(no author)` and the like.
- Chains are followed: if A shares an email with B and B shares a name with C, all three are one person.
- Git's `.mailmap` is applied before any of this.

The same grouping is applied **across all histories** (several repositories, nested repositories, SourceSafe and Git): the summary gives the number of people across all of them, each counted once.

### Authors named in code comments

Without version control, the only trace of who wrote the code is often a comment. The script finds authors named in the comments of the owner's code (and in VBA read from Access databases):

- `@author Jane Doe`, `Author: Jane Doe <jane@example.com>`, `Authors: Jane Doe and Kenji Mori`, `Written by`, `Created by` (including Xcode's `Created by Jane Doe on 3/4/15.`), `Coded by`, `Programmed by`, `Programmer:`, and Python's `__author__ = "..."`.
- Only in comment lines (`//`, `/*`, `*`, `#`, `'`, `--`, `;`, `REM`, `<!--`, `{`, `(*`), so a string in code that contains "Author:" isn't counted.
- Several names on one line are split on commas, "&", "/" and "and". Text after an email, a date, a year or a word like "on", "at", "for", "in" is dropped.
- Not counted as people: things that aren't names (prose such as "the factory", tools such as "Unity" or "Visual Studio", months, "various contributors", "see AUTHORS"), placeholders ("John Doe", "Your Name", "Firstname Lastname"), and template variables such as `$Author$` or `${USER}`.

These people are grouped with the same rules as above and **only counted, never named**. The count always appears in the report; without version control it is also given in the summary as the number of contributors, with the warning that there were probably more.

---

## 11. Other findings

### Assets

Files are counted by kind across the whole folder (including third-party packages): scenes and levels, prefabs, 3D models, textures and images, audio, animations, materials, visual effects, UI layouts, fonts, video, Godot resources, documents (design documents and specifications: PDF, Word, Excel, PowerPoint, OpenDocument, Pages, Keynote, Numbers), Jupyter notebooks, Ren'Py compiled scripts and archives, Unreal packages by type (section 5), and Access databases.

If there are at least 1,000 lines of the owner's code but fewer than 20 content assets (not counting scenes and notebooks) and no visual scripting, the report notes that this looks like the source code only, and suggests asking whether the full project still exists.

### Credentials

The script looks for credentials that would have to be removed before code changes hands. It reports only their kind and the number of files:

- **Key and credential files, by name**, in any folder: `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`, `.env` and `.env.*`, and `.pem`, `.p12`, `.pfx`, `.keystore`, `.jks`, `.ppk`, `.mobileprovision` files.
- **Secrets in file contents**: private keys (`-----BEGIN ... PRIVATE KEY`), AWS access keys, Google API keys, GitHub tokens, Slack tokens, Stripe live secret keys, and passwords in connection strings (`password=...;` or `pwd=...;`). Searched in every code file, and in configuration-type files under 1 MB (`.env`, `.ini`, `.cfg`, `.conf`, `.config`, `.json`, `.yml`, `.yaml`, `.xml`, `.properties`, `.plist`, `.toml`, `.txt`, `.asset`) outside third-party folders.

### Licences

- **At the top of the folder**: a `LICENSE`, `LICENCE`, `COPYING`, `COPYRIGHT` or `EULA` file is classified as a non-commercial licence, AGPL, LGPL, GPL, MPL, Apache 2.0, MIT, BSD, zlib, Creative Commons, Unlicense/public domain, proprietary (all rights reserved), or "a licence of its own". Anything other than proprietary or its own raises a "licensed to others already" alert.
- **In folders and file headers**: see section 7.
- **Copyright years**: the range of years in copyright notices in the owner's code (1980-2049, including ranges like "2012-2016" and the © sign).
- **Public repository**: if a GitHub, GitLab or Bitbucket remote can be read without logging in, the report says the code is already public. (Not checked with `--offline`.)

### Code the project needs that isn't in the folder

A project built on a company's own engine or shared library kept elsewhere (or lost) shows up here. The script collects:

- **`#include` and `#import`s** in the owner's C-family code that don't resolve to any file in the scanned folder. Compiler and operating-system headers (the C and C++ standard libraries, POSIX, Windows, DirectX, Apple frameworks, OpenGL) are ignored. In an Unreal, Godot, Source or CRYENGINE project, the engine's own headers are expected and attributed to the engine. The rest are grouped by known library (Boost, Ogre, Bullet, PhysX, SDL, Qt, FMOD, Wwise, Steamworks, Havok, Scaleform, Bink and about 70 others) or by their first folder.
- **Build files**: include and library folders outside the project named in premake (`includedirs`, `libdirs`), CMake (`include_directories`, `target_include_directories`, `link_directories`, `find_package`, `FetchContent_Declare`, `ExternalProject_Add`), Visual Studio project and property files (`AdditionalIncludeDirectories`, `AdditionalLibraryDirectories`, `IncludePath`, `LibraryPath`), Xcode (`HEADER_SEARCH_PATHS`, `LIBRARY_SEARCH_PATHS`, `FRAMEWORK_SEARCH_PATHS`), Meson (`dependency()`), and Makefiles and SCons (`-I`, `-L`, `pkg-config`). Each path is reduced to a library name: path noise (`include`, `lib`, `x64`, `Program Files` ...) and personal folders (and the user name after `Users/` or `home/`) are skipped, versions are read from names like `boost_1_55_0` ("boost 1.55.0"), and a path that is only a variable is named by the variable (`$(DXSDK_DIR)` gives "DXSDK"). A network path's computer and share names are left out (`\\buildsrv\libs\boost_1_55_0` gives "boost 1.55.0"). Paths inside the project are ignored.

Names the script recognises as well-known libraries are listed as "Known libraries". Names it doesn't recognise are listed first, as possibly the owner's own code (an engine, shared code) to ask for, and raise an alert.

- **Package lists**: dependencies named in `package.json` (including dev dependencies), Unity's `Packages/manifest.json`, Marketplace/Fab plugins enabled in a `.uproject`, `vcpkg.json`, `requirements*.txt`, `pyproject.toml`, `Cargo.toml`, `.csproj`/`.fsproj`/`.vbproj` package references, `packages.config`, `conanfile.txt`, `go.mod`, `build.gradle(.kts)` and `pom.xml`, grouped by ecosystem (up to 12 names each, then a count).

### The summary's "Check" line

The summary at the top ends with a list of things a reader should check, when present: exact copies of files, console code, text files of unknown kinds, a compiled Access database, Access databases not opened, SQL Server files whose code isn't counted, data files to keep out, code needed from elsewhere, credentials, no assets, a downloaded copy without history, an open licence, a public repository, and SourceSafe history not included or archives not read.

---

## 12. Standard measures (scc, jscpd)

Codebase questionnaires commonly ask for the same handful of figures, defined by the tools they name. The report ends with them, measured over the owner's apparently original code:

| Measure | Definition |
|---|---|
| Logical lines of code | scc's count: lines that are not blank and not only a comment |
| of which generated | scc with `--gen` and `--generated-markers "do not edit,<auto-generated />,<auto-generated>"`, excluding `vendor`, `node_modules`, `dist`, `build`, `generated`, `migrations` |
| Duplication ratio | jscpd with `--min-tokens 50 --min-lines 5`, ignoring `**/*.csv` |
| Commits on the main branch, without merges or reverts | as `git log --oneline --no-merges` on the main branch, minus subjects containing "revert" |
| Repositories | the number of histories found (at least 1) |
| Primary language | the language with the most lines, named as forms name languages (see below) |
| History | "Git, full history", "Git, but a shallow clone", another system (with the suggestion to convert it to Git or deliver a snapshot), or "flat snapshot" |
| Changes made before 2022 | changes dated before AI coding assistants were common, out of all changes |

### Code scc and jscpd don't recognise

Some languages this script counts are unknown to the pinned scc, which skips their files, and to jscpd: Ren'Py (`.rpy`, `.rpym`), Verse, Ink, Twine, Naninovel, Squirrel, SkookumScript, MoonScript, BlitzMax, Monkey, AppGameKit, PL/I, RPG, VBScript, Delphi project files (`.dpr`), `.tsql`, `.tcc`, and shaders (`.shader`, `.hlsl`, `.cg`, `.cginc`, `.compute`, `.fx`, `.fxh`, `.psh`, `.usf`, `.ush`, `.gdshader`, `.gdshaderinc`, `.glslinc`). When the owner's code has some, both tools are told to read them as a known language whose comments they share, as with `--code-ext`: Ren'Py and Verse as Python, the C-like ones and shaders as C, and so on (the table is `UNRECOGNISED_CODE` in the script). Only extensions the project has are passed, so the tools' commands are otherwise the forms' own. The report says which extensions were added and gives scc's figure without them, which is what the forms' command gives. Visual Basic 6 form and control files (`.frm`, `.ctl` ...) are not added: read whole, their designer sections would count as code.

The report also gives jscpd's ratio for each kind of file it read (its "formats", such as `python` or `txt`) when there is more than one, because the forms' jscpd command also reads plain-text files, and duplicated text (credits, licences, notes) can dominate the ratio.

### Running scc and jscpd

The script uses pinned versions: **scc 4.1.0** (from its GitHub releases) and **jscpd 5.4.1** (from registry.npmjs.org, where it is published as a self-contained program, so Node.js isn't needed). Builds are pinned for macOS (Apple silicon and Intel), Linux (ARM64 and x64; scc also 32-bit x86; jscpd for glibc and musl) and Windows (ARM64 and x64; scc also 32-bit x86).

- Each is downloaded once, over HTTPS with the server's certificate checked (there is no retry without the check). The download is checked against a fixed SHA-256 checksum, then the one program file is taken out of it and checked against its own checksum. A file that doesn't match is never written or run.
- They are kept in a cache folder: `%LOCALAPPDATA%\size_codebase_tools` on Windows, `~/Library/Caches/size_codebase_tools` on macOS, and `$XDG_CACHE_HOME/size_codebase_tools` (or `~/.cache/size_codebase_tools`) on Linux, in subfolders named by tool and version. Deleting the folder removes them.
- The cached program's checksum is checked again before every run. A copy that doesn't match is deleted, and downloaded again if downloading is allowed.
- No other copy is ever run: an `scc` or `jscpd` installed on the computer is not used.
- jscpd is given its own configuration file, so a `.jscpd.json` in the project, or a `jscpd` section in its `package.json`, has no effect. Neither tool follows symbolic links.

Both tools are run over the whole folder. Then only the owner's code is kept: the folders where the owner's code gives way to someone else's, to the engine, or to build output, and someone else's files among the owner's, are left out (from scc's per-file results, and through a jscpd ignore list). Paths marked `--own` inside such folders are kept. The report gives the number of folders and files left out (never their names) and scc's figure for the whole folder for comparison. The tools are not run when a single file is given.

### When scc or jscpd can't be used

If a tool can't be used (there is no pinned build for this computer; it isn't in the cache and `--offline` or `--no-download` was given; the download or a checksum failed; or the tool ran but failed), **its figures are left out**: the script doesn't estimate them. The report says, under "Not included in the standard measures above", which figures are missing and why, and how to include them (for example, run again with an internet connection). In the JSON, `logical_lines`, `generated_lines` or `duplication_ratio` is then `null`, and `not_measured` gives the reason. On macOS, if the download failed because Python couldn't check the server's certificate (python.org's installer has no certificates until its "Install Certificates" step is run), the report says how to fix that.

### Primary language

- **With scc**: by scc's logical lines in the owner's code, per language. Languages scc counts that aren't code (JSON, XML, YAML, Markdown, plain text, project files and the like) are left out. Code read from databases, which scc can't see, is added as its non-blank lines, and the report says so.
- **Without scc**: by the non-blank lines in the "Apparently original source code" table, and the report says so. C and C++ are split by file there: `.c` is C, `.h` is a C header, everything else C++.
- Either way, C headers go to whichever of C and C++ is larger, and names are mapped to the ones forms use (UnityScript as JavaScript, T-SQL and PL/SQL as SQL, Pascal as Object Pascal, scc's "BASH" as Shell, and so on). A language not on the forms' list is shown as "Other", with its own name beside it.

### Commits

For Git, commits are counted on the main branch: the one `origin/HEAD` names, else `main`, `master`, `trunk` or `develop` (local or on `origin`), else the branch checked out. Merges, commits whose subject contains "revert", and Epic's commits in an Unreal fork are left out. For a subfolder scan, only commits touching the subfolder count.

For systems that don't record merges, changes whose subject starts with "merge", "merged" or "merging", and those whose subject contains "revert", are left out. For SVN, the counted path is shown, with a note if it isn't a trunk (which could include branches). For Plastic SCM, the changesets on `/main`, without merges, and without those whose subject contains "revert". Commits from all histories that could be counted are summed, each counted once (see "Projects that moved between systems"), and the report says if some couldn't be.

### `--reports`

With `--reports`, two more files are saved beside the script's report, for attaching to a form: scc's JSON report (lines by language, run with the form's command) and a summary of jscpd's report (`{"statistics": ...}`: its totals for each format and in all, as forms ask for it). Both hold counts only. jscpd's full report, which holds copies of the duplicated code and the names of their files, is never saved; it's deleted with jscpd's temporary folder.

---

## 13. Output

### On screen

Progress is shown on one line that keeps being overwritten (only when the output is a terminal). The full report is printed at the end, followed by where it was saved.

### Files

The report is saved as `size_report_<name>.txt`, where `<name>` is the scanned folder's name (or the file's name, when a single file was given) with every character other than letters and digits replaced by `_`. Beside it:

- `size_report_<name>.json`: the same numbers, for reading by machine.
- With `--reports`: `size_report_<name>_scc.json` and `size_report_<name>_jscpd-summary.json`.

They are saved next to the script. If that folder can't be written to, they go in the current folder, and failing that, the home folder. If none works, the script says to copy the report from the screen. An existing file of the same name is replaced; if it is a symbolic link, the link itself is replaced, so the report is never written into the file it points to.

### The text report, in order

1. The script's name and version (for example `size_codebase.py 1.2.0`, with a note if `--offline` was given), the project name, then a **summary**: apparently original code (with the top three languages), visual-scripting nodes, the first history in one line (changes, people, date range, pull requests), contributors across all histories, the history of all systems together, where there's more than one (see section 9), and the "Check" list.
2. Project types found; Unreal versions that saved the assets; version control found; total size.
3. **Apparently original source code** by language, with notes on tests, Epic's and other engines' notices, exact copies, files not committed to Git, and console code.
4. Original code by folder; folders with their own licence file; text files of unknown kinds.
5. Blueprints and other visual scripting; how much of the Unreal assets could be measured.
6. Databases; files holding data; code the project needs that isn't in the folder; package dependencies.
7. UnrealScript compiled into `.u` packages.
8. Someone else's code (with its breakdown by library, package or licence), Unreal Engine's own code, translations, generated code, data.
9. Precompiled libraries, and notes: built Unity game, packaged Unreal game, Git LFS placeholders, linked folders, paths marked by hand, cooked assets, Ren'Py without source, credentials, no assets.
10. Assets by kind.
11. Version-control histories, SourceSafe, file dates when there is no history, people named as authors, copyright years, the licence at the top, public repository, submodules, custom engines, nested repositories, the history caveats, and a note if Git first refused a repository that belongs to another user account (section 9).
12. **Standard measures**, with what couldn't be measured and why.
13. With `--offline`: that no other computer was contacted, and what was left out because of it.
14. Problems while scanning, if any. An unexpected error on one file, or in one section of the report, doesn't stop the scan; up to five distinct error messages are listed and the rest of the report is unaffected. Paths in them are replaced: the scanned folder by `<project>`, the home folder by `~`, and anything else that looks like a path, or a quoted file name, by `<path>`.

### The JSON file

Top-level keys: `script_version`, `offline`, `left_out_offline`, `git_repositories_of_other_users` (how many), `project`, `project_types`, `lines` (files and lines per language for each category: own, test, third-party, engine, generated, translation, data), `own_total`, `duplicate_lines`, `untracked_lines`, `console_lines`, `third_party_by_library`, `folders`, `visual_scripting`, `unreal_coverage`, `unreal_versions`, `assets`, `version_control`, `histories` (rows, reviews and notes of each), `contributors`, `dependencies_not_here`, `precompiled_libraries`, `credentials` (kinds and file counts), `copyright_years`, `licence`, `public_repositories`, `submodules`, `alerts`, `problems`, `standard_measures` (the figures, `null` where a tool couldn't be used, with `not_measured` saying why; the tools' versions; and the primary language and what it was judged from), `unknown_text_files`, `code_extensions_named` and `databases`. Like the text report, it holds no author names, no code and no credential text.

---

## 14. Command-line reference

```
python3 size_codebase.py [PATH ...] [options]
```

On Windows, `py` works in place of `python3`, and so does double-clicking the script.

| Argument | Meaning |
|---|---|
| `PATH` | A folder to scan, or a single file (such as an Access database). Several can be given; each is scanned and reported separately. With none, the script asks for folders interactively. |
| `--third-party PATH` | Count this folder or file as someone else's code. Relative to the scanned folder, or absolute. Repeatable. Overrides every automatic rule. |
| `--own PATH` | Count this folder or file as the owner's own code, even inside a folder that would otherwise be third-party. Repeatable. |
| `--code-ext .EXT=NAME[:LIKE]` | Count files with this extension as code in language NAME. LIKE is a known language whose comments it shares, for scc and jscpd: `text` (default), `C`, `C++`, `Ada`, `SQL`, `Lisp`, `Python`, `Pascal`, `Lua` or `Visual Basic`. Repeatable. |
| `--sql-server SERVER` | Read the code (procedures, functions, views, triggers) from this running SQL Server through `sqlcmd`. Windows sign-in, or `SQLCMDUSER`/`SQLCMDPASSWORD`. Repeatable. Can't be combined with `--offline`. |
| `--sql-database NAME` | With `--sql-server`: read only this database instead of every user database. Repeatable; applies to every server named. |
| `--trust-server-certificate` | With `--sql-server`: trust the server's certificate without checking it (`sqlcmd -C`), for a server you trust that has its own self-signed certificate. |
| `--sourcesafe PATH` | A Visual SourceSafe database (the folder with `srcsafe.ini`, a copy without it, or its `data` folder) holding this code's history. May be on a network share, except with `--offline`. Repeatable. |
| `--network-sourcesafe` | Also open SourceSafe databases on network shares that the project files name, and a `Data_Path` on a network share in a database's `srcsafe.ini`. Without it they're named on screen but not opened. Can't be combined with `--offline`. |
| `--offline` | Connect to no other computer: no downloads (a copy of scc or jscpd downloaded before is still used, after its checksum is checked), no version-control servers, no network shares besides the folder scanned, and Access databases aren't opened in Microsoft Access. The report lists what that left out. |
| `--no-download` | Don't download scc or jscpd. A copy already in the cache is still used; otherwise their figures are left out. |
| `--reports` | Also save scc's JSON report and jscpd's totals beside the report, for attaching to a form. Both hold counts only. |
| `-h`, `--help` | Print the script's version and how to use it, and stop. |

Environment variables: `SSDIR` names a SourceSafe database; `SQLCMDUSER` and `SQLCMDPASSWORD` are a SQL Server sign-in, used by `sqlcmd`; `ASSETSTORE_CACHE_PATH` is a moved Unity Asset Store cache; `P4CONFIG` is the name of Perforce's settings file. [SECURITY.md](SECURITY.md) lists every variable and setting the script and the tools it runs read.

Notes on parsing: the script stops with a message, before scanning anything, at an argument beginning with `--` that isn't one of the options above ("Unknown option"), at an option that needs a value given last without one, and at `--offline` combined with `--sql-server`, with `--network-sourcesafe`, or with a `--sourcesafe` folder on a network share. Any other argument is taken as a path. `--third-party` and `--own` paths given as relative paths are resolved against each scanned folder in turn.

---

## 15. Limitations, and how to correct them

**Ownership is a heuristic.** "Apparently original" means the code doesn't carry any of the signs of someone else's code described in section 7. It is not a legal finding. Specifically:

- **The owner's own open-source code** that carries an MIT, BSD, Apache or similar licence header, or sits in a folder with a licence file among other code, is counted as third-party. Fix with `--own`.
- **The owner's code in a folder with a third-party name** (`external`, `vendor`, `fonts`, a Unity `Plugins` folder, a folder that happens to be called `bullet` or `fmt`) is counted as third-party. Fix with `--own`.
- **A copied-in library without any of the signs** (no licence header, no licence file, an unrecognised folder name) is counted as the owner's. The per-folder breakdown and the duplication figures help find it. Fix with `--third-party`.
- **Files carrying an engine maker's notice** stay the owner's, with a count shown. If some were copied from the engine, mark them with `--third-party`.
- **Unity Asset Store packages** are best recognised on the computer that downloaded them. Elsewhere, recognition relies on folder names and package layout, and a renamed package without demos or docs is counted as the owner's.
- **Git submodules** are judged by their URL's owner. A library forked into the owner's own account counts as the owner's.

**Skipped folders can't be brought back.** Folders skipped as caches, dependencies or build output (section 3) are never entered, so `--own` can't include them. In particular, a folder named `build` at the root of a Unity, Unreal, JavaScript or Python project, `out` or `dist` at the root of a JavaScript project, or `bin`/`obj` at the root of a .NET project, is skipped even if it holds source. Run the script on that folder directly to count it. Symbolic links and junctions are not followed either.

**Extensions can mislead.** `.m` is counted as Objective-C (MATLAB files would be miscounted), `.pl` as Perl (not Prolog), `.inc` and `.v` are not counted, and `.fs` only inside a .NET project. Visual Basic extensions are checked for VB content, but other ambiguous extensions are not. Use `--third-party` to drop files, or `--code-ext` to add an unknown extension.

**The main table counts non-blank lines, comments included.** The standard measures count logical lines, as scc does. Both are shown; they are not expected to match. Files that `.gitignore` ignores are in the main table but not in the standard measures.

**The standard measures need scc and jscpd.** Where one can't be used (offline before it was ever downloaded, say), its figures are missing from the report, not estimated, and the report says why. Without scc, the primary language is judged from the main table.

**`--offline` leaves things out**: pull requests on the Git server, histories kept on a server, network shares named in your settings, and the VBA in Access databases (and their forms, reports and queries too, unless mdbtools is installed). The report lists what was left out.

**Visual scripting is counted only for Unreal**, in nodes rather than lines. Cooked Unreal assets have no graphs to count, and some licensee-modified package formats can't be read (the report says how many, and how many appear to hold graphs). Construct's event sheets and other engines' visual scripts (stored as data assets) are not counted.

**Histories count what this copy holds.** Unmerged branches are included in the Git commit count (the main-branch count is shown separately), squash merges hide individual commits, deleted branches are gone, and a shallow clone or an imported snapshot loses earlier history. Git LFS placeholders that were never downloaded can't be read; run `git lfs pull` first. TFVC and Plastic give only years, not full dates. Pull-request counts depend on what the hosting service leaves in the repository and on whether the server can be reached with stored credentials; the hosting service's own count is authoritative.

**Contributors are matched by identical strings.** Two identities are one person only if they share an email, a full name, or a distinctive handle. A Perforce user name and a Git email for the same person are not matched unless the same string appears in both. A `.mailmap` file fixes this for Git. People named in code comments are an undercount: most files don't name their author.

**Database code needs the right tools.** Access VBA can only be read on Windows with Microsoft Access installed; a compiled database (`.mde`, `.accde`) has no VBA source at all. mdbtools reads queries and object counts but not VBA. SQL Server code inside `.mdf` or `.bak` files can't be read from the files; use `--sql-server` against a running server. Access macros are counted as objects, not lines. When several `--sql-server` options are given, code from every server is counted, but the Databases section shows the object counts of the last server only.

**SourceSafe**: only the first five databases found are read, and `.ssa` archives must be restored with SourceSafe's own tools first.

**Histories in more than one system**: a change is found in two histories by a conversion marker or its message (section 9). A conversion that rewrote the messages and kept no marker, of a history whose messages are too few to go by, is fitted together by dates alone, which can count work done in both systems at once (side by side, for different work) only once.

**Duplicate files are exact copies only.** Files that differ by a single byte are not duplicates; near-copies show up in jscpd's duplication ratio instead.

**Check the report before sending it.** It is designed to hold counts and names only, but folder, library, package and branch names are the owner's own words. Paths in error messages are replaced, but an unquoted bare file name in one would stay.
