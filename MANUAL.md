# size_codebase.py manual

## Name

`size_codebase.py`: take an inventory of a codebase (its code by language, its version-control
history, its contributors) and produce the standard measures buyers' codebase forms ask for.

## Synopsis

```
python3 size_codebase.py [PATH ...] [OPTION ...]
py size_codebase.py [PATH ...] [OPTION ...]          (Windows)
python3 size_codebase.py                             (asks for the folders)
```

Options and paths may come in any order. Every option applies to every `PATH`.

## Description

Scans each `PATH` and reports on it separately. A `PATH` is usually a project folder; it may
also be a single file, such as a Microsoft Access database, which holds a whole program in one
file. Only that file is examined, and its folder supplies the version-control history.

It only reads: it doesn't change the project or its history, uploads nothing and downloads
nothing. It asks servers only what the history needs (see [Connections](#connections)). What it
does and where it can go wrong is in [HOW_IT_WORKS.md](HOW_IT_WORKS.md); every connection it
makes and program it runs is in [SECURITY.md](SECURITY.md).

Needs Python 3.8 or newer, and nothing else.

## Options

### Which code is whose

**`--third-party PATH`**
: Count this folder or file as someone else's code (a library, an SDK, a bought plugin),
  whatever the automatic rules say. Relative to each scanned folder, or absolute. Repeatable.

**`--own PATH`**
: Count this folder or file as the owner's own code, even inside a folder that would otherwise
  be someone else's (an `external` folder, a Unity `Plugins` folder, a file with an open-source
  licence header the owner wrote). Relative to each scanned folder, or absolute. Repeatable.

  Neither option can bring back a folder that is always skipped (caches, dependencies, build
  output: HOW_IT_WORKS.md section 3). Run the script on such a folder directly to count it.

  ```
  python3 size_codebase.py ~/Game --third-party Source/Game/SomeLib --own Plugins/MyPlugin
  ```

**`--code-ext .EXT=NAME[:LIKE]`**
: Count files with extension `.EXT` as code in a language called `NAME` (one the script doesn't
  know, such as a studio's own). Every non-blank line counts. `LIKE` is a known language whose
  comments it shares, so the standard measures can tell comments from code: `text` (the
  default: no comments), `C`, `C++`, `Ada`, `SQL`, `Lisp`, `Python`, `Pascal`, `Lua` or
  `Visual Basic`. The leading dot is optional. Repeatable.

  ```
  python3 size_codebase.py ~/Game --code-ext .par=PARLANSE --code-ext ".atg=DMS grammar:Ada"
  ```

### Version-control history

The history in the scanned folder (Git, Perforce, SVN, Mercurial, Plastic SCM, TFVC, Bazaar,
Fossil, Darcs, CVS) is found and read without any option. Perforce, Plastic SCM, TFVC, and SVN
or CVS checkouts of a server need their command-line tool installed and logged in. These options
add history kept elsewhere.

**`--history PATH`**
: Older history of this code, kept somewhere other than the scanned folder: a folder or a single
  file. Repeatable, once per place; or put every old history in one folder and name that. In
  each folder named, and every folder inside it, the script finds:

  - working copies and repositories of any system above (old SVN and CVS working copies are
    counted once, at their top folder);
  - bare Git repositories (`git clone --mirror`, a server's copy);
  - Git bundles (`git bundle create`; GitLab's project export holds one, `project.bundle`);
  - SVN repositories' own folders (`svnadmin create`, the old server's folder or a copy of it),
    read without `svn` unless their revisions are packed or kept in Berkeley DB;
  - SVN dumps (`svnadmin dump`, `svnrdump dump`: full, incremental or with deltas), also
    compressed with gzip, bzip2 or xz. Only files with `dump`, `dmp`, `bundle` or `svn` in
    their names, or ending `.gz`, `.bz2` or `.xz`, are checked;
  - Visual SourceSafe databases.

  Only what is inside the paths named is read: no folder above them, no symbolic link in them,
  and no server they name for pull requests. Up to 100 repositories are read from each path. A
  system it can't read (Diversion, Lore ...) is named in the report, which asks for an export.

  Every history found, here and in the scanned folder, is put together, through any number of
  moves between systems, each change counted once (HOW_IT_WORKS.md section 9). The `PATH` must
  exist, or the script stops before scanning.

  ```
  python3 size_codebase.py ~/Game \
    --history ~/old/game-svn.dump.gz \
    --history ~/old/bitbucket-mirror.git \
    --history ~/old/gitlab-export \
    --history ~/old/p4-workspace
  ```

**`--sourcesafe PATH`**
: A Visual SourceSafe database holding this code's history: the folder with `srcsafe.ini`, a
  copy of it without that file, or its `data` folder alone. SourceSafe has no server program, so
  a copy from a backup works as well as the original. May be on a network share. Repeatable.
  Without it, databases inside the project, the one `SSDIR` names, and those the project files
  name on this computer are read anyway; `--history` naming a folder that holds one reads it too.

  ```
  py size_codebase.py "C:\Projects\Game" --sourcesafe "D:\OldVSS"
  ```

**`--network-sourcesafe`**
: Also open SourceSafe databases on network shares (`\\server\share`) that the project's own
  files name, and a `Data_Path` on a network share in a database's `srcsafe.ini`. Without it
  they're named on screen but not opened, since the project's files could name any computer, and
  on Windows opening a share can send your sign-in to it. Use it only for a project you trust.

### Databases

**`--sql-server SERVER`**
: Read the code that lives only inside this running SQL Server (stored procedures, functions,
  views, triggers) through `sqlcmd`, with your Windows sign-in, or the one in `SQLCMDUSER` and
  `SQLCMDPASSWORD`. Never reads a table's rows. Repeatable.

**`--sql-database NAME`**
: With `--sql-server`: read only this database rather than every user database. Repeatable;
  applies to every server named.

**`--trust-server-certificate`**
: With `--sql-server`: trust the server's certificate without checking it (`sqlcmd -C`), for a
  server you trust that has its own self-signed certificate.

  ```
  py size_codebase.py "C:\Projects\Billing" --sql-server MYSERVER\SQLEXPRESS --sql-database Sales
  ```

Access databases (`.accdb`, `.mdb` ...) need no option: they're read in full on Windows with
Microsoft Access installed, and without their VBA through mdbtools elsewhere.

### Connections and output

**`--offline`**
: Connect to no other computer at all: no version-control servers, no network shares besides the
  folders you name, and no Access database opened in Microsoft Access. The report lists what that
  left out. Histories kept in the working copy (Git, Mercurial, Fossil, Darcs) and everything
  `--history` names on this computer are still read. Can't be combined with `--sql-server`, with
  `--network-sourcesafe`, or with a `--sourcesafe` or `--history` path on a network share.

**`--reports`**
: Also save the lines by language and the duplication totals beside the report, laid out as
  scc's report and jscpd's totals are, for attaching to a form (see [Files](#files)). Both hold
  counts only: no code and no file names.

**`-h`, `--help`**
: Print the script's version and how to use it, and stop.

## Interactive mode

Started without arguments (for example by double-clicking it on Windows), the script asks for a
folder: drag it into the window or paste its path, and press Enter. It then asks for another; an
empty line ends it, and it waits for Enter before closing the window. No options can be given
this way.

Dragged and pasted paths are cleaned up, here and on the command line: Windows `"quotes"`, macOS
Terminal's backslash escapes (`My\ Game`), Linux `'quotes'` and `file://` addresses all work.

## Files

For each `PATH`, saved in the folder that holds the script (if it can't write there, the current
folder, then the home folder), `<name>` being the scanned folder's or file's name with
everything but letters and digits replaced by `_`:

`size_report_<name>.txt`
: The report, as printed on screen.

`size_report_<name>.json`
: The same numbers, for reading by machine.

`size_report_<name>_lines.json`, `size_report_<name>_duplication.json`
: With `--reports` only: the lines by language and the duplication totals.

A file of the same name is overwritten. The reports hold counts, and names of folders, branches,
languages, libraries and packages: no source code, no author names. Read them before sending
them.

## Connections

Without `--offline`, it asks servers only for what the history needs, read-only, with the access
you already have, and never stops to ask for a password:

- Git: each remote, for the pull requests it keeps (`git ls-remote`); GitHub, through `gh` if
  it's installed and signed in, for merged pull requests; and GitHub, GitLab or Bitbucket,
  without signing in, whether anyone can read the repository. Not for repositories named with
  `--history`.
- Perforce, Plastic SCM and TFVC, and SVN, CVS or Bazaar where the history is on a server: their
  own commands ask that server for the history.
- `--sql-server`: that server. `--sourcesafe`, `SSDIR` and `--history`: the folders named, even
  on a network share. `--network-sourcesafe`: the shares the project files name.

## Environment

`SSDIR`
: A SourceSafe database to read, as if named with `--sourcesafe`.

`SQLCMDUSER`, `SQLCMDPASSWORD`
: A SQL Server sign-in for `--sql-server`, used by `sqlcmd`.

`ASSETSTORE_CACHE_PATH`
: A Unity Asset Store download folder moved from its usual place.

`P4CONFIG`
: The name of Perforce's settings file.

The programs it runs (git, p4, svn ...) get your whole environment and their own settings and
logins. SECURITY.md lists every variable and setting read.

## Exit status

`0`
: Done, including when a `PATH` isn't there (it says so and goes on to the next) and when part
  of a scan fails (the report lists the problem and the scan carries on).

`2`
: Stopped before scanning: an unknown option, an option missing its value, a `--code-ext` it
  can't read, a `--history` path that doesn't exist, or `--offline` with an option that needs
  another computer.

## Examples

A project, with its history and nothing else:

```
python3 size_codebase.py ~/Projects/Game
```

A project that moved from SVN to Bitbucket to GitLab to Perforce, with each old history kept in
one folder:

```
python3 size_codebase.py ~/Projects/Game --history ~/OldHistory
```

Two projects, the same corrections applied to each, with the extra files for a form:

```
python3 size_codebase.py ~/Projects/Game ~/Projects/Tools --third-party ThirdParty/Physics --reports
```

An Access program and the SQL Server it talks to, on Windows:

```
py size_codebase.py "C:\Apps\Orders.accdb" --sql-server DBHOST\SQLEXPRESS --sql-database Orders
```

Nothing sent anywhere:

```
python3 size_codebase.py ~/Projects/Game --offline
```

## See also

[README.md](README.md), [HOW_IT_WORKS.md](HOW_IT_WORKS.md) (section 14 has a one-table summary
of these options), [SECURITY.md](SECURITY.md).
