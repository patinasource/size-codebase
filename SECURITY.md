# Security

This page is for anyone deciding whether to run `size_codebase.py` on their code: a security engineer, or an AI assistant asked "is this safe to run?". The statements below name the functions in `size_codebase.py` that do each thing (by name, not line number), so you can check them. The script is one file of standard-library Python (3.8 or later), with no dependencies.

## Summary

`size_codebase.py` reads a folder and writes a report about it: lines of code by language, the owner's code versus someone else's, version-control history (commits, contributors, pull requests), assets, and the standard measures that codebase questionnaires ask for. It doesn't change the project, only reads it (version-control tools may update their own caches, as they always do, and the report is saved next to the script, wherever that is). It uploads nothing: no code and no report are sent anywhere, and servers are only asked the questions listed below. The report stays on your computer, and you decide whether to send it to anyone. It holds counts, and the names of folders, languages, libraries, packages and branches (the full list is [below](#what-the-saved-report-contains)); it holds no source code, no author names or email addresses, and no credentials.

It does make some network connections, all listed below: it downloads two pinned, checksum-verified measuring tools (scc and jscpd) once, and asks your version-control servers for history and pull-request counts, with the access you already have. `--offline` turns all of that off.

## How to run it

**Normally:**

```
python3 size_codebase.py "/path/to/project"
```

On Windows, `py` instead of `python3`. `--help` prints the options.

**For sensitive code, offline:**

```
python3 size_codebase.py --offline "/path/to/project"
```

With `--offline` the script makes no network connection of its own (see the table below for exactly what that switches off). What it leaves out, and the report then says so in a "Left out because of that" list:

- scc's and jscpd's figures (logical lines, generated lines, duplication), unless an earlier run without `--offline` already downloaded them. A copy downloaded before is still used, after its checksum is checked.
- Pull-request counts from Git servers and from GitHub's API, and the check of whether the repository is public. Pull requests named in commit messages are still counted.
- Histories that come from a server: Perforce, Plastic SCM, TFVC, and SVN, CVS or Bazaar when their history isn't on this computer. Git, Mercurial, Fossil, Darcs, and local SVN, CVS and Bazaar histories are still read.
- A SourceSafe database or custom Unreal Engine on a network share named by your settings (`SSDIR`, the Unreal registration), and a Unity Asset Store cache on a network share.
- Access databases are not opened in Microsoft Access (mdbtools, if installed, still reads their queries and object counts).
- `--sql-server` can't be combined with `--offline`; the script stops with a message.

**For code you don't trust**, also run it in a disposable virtual machine or container that holds no credentials and has no network, for example:

```
docker run --rm --network none -v "/path/to/project:/src:ro" -v "$PWD/out:/out" python:3.12-slim \
    python3 /out/size_codebase.py --offline /src
```

(with `size_codebase.py` copied into `out/` first: the report is saved next to the script). The image needs `git` installed for the Git history to be read, and scc and jscpd are left out unless their cache folder (below) is already in the container. See [residual risks](#residual-risks) for why this is worth doing for hostile code.

## Network connections

This is every connection the script can cause. "Off with" names the options that prevent it.

| Connection | Function(s) | When | Off with |
|---|---|---|---|
| HTTPS download of scc from `github.com` (which redirects to GitHub's download host) and of jscpd from `registry.npmjs.org` | `find_tool`, `download` | Once, if the pinned copy isn't already in the cache; not when a single file is scanned | `--offline`, `--no-download` |
| `git ls-remote` to each Git remote, to count pull-request refs, with your own Git credentials | `git_server_pull_requests`, `ls_remote` | Git repositories with remotes. Not Epic's Unreal Engine repository, and not remotes in a folder on a network share (`remote_on_network_share`) | `--offline` |
| `gh api` (GitHub's command-line tool, your login) to `api.github.com`: a search for the merged pull requests of `owner/repo`, which sends that name | `github_merged_pull_requests` | GitHub remotes, if `gh` is installed and logged in | `--offline` |
| `git ls-remote` over HTTPS without any login to `github.com`, `gitlab.com` or `bitbucket.org`, to see whether anyone can read the repository (sends the `owner/repo` name) | `public_repositories`, `ls_remote` | Remotes on those three services | `--offline` |
| `p4 changes` to your Perforce server (or `p4`'s default, `perforce:1666`) | `perforce_history` | Whenever `p4` is installed (Perforce settings often live outside the folder, so `p4` is asked) | `--offline` (p4 isn't run at all) |
| `svn log`, `cvs -q log`, `brz log`/`bzr log`, `cm find`, `tf history` to the server their working copy names | `svn_history`, `cvs_history`, `bzr_history`, `plastic_history`, `tfvc_history`; `history_from_server` decides | When that system is found and its tool installed | `--offline`, unless the history is on this computer (`history_from_server`) |
| `sqlcmd` to the SQL Server you name | `read_sql_server`, `sqlcmd` | Only with `--sql-server` | Not given; refused with `--offline` |
| Reading a folder on a network share | `SourceSafe`, `read_sourcesafe` (`--sourcesafe`, `SSDIR`); `find_custom_engine` (an Unreal engine registered on a share); `asset_store_download_folders` (`ASSETSTORE_CACHE_PATH` on a share) | Only where you or your settings name it. Network locations named by the project's own files are never opened (`SourceSafe.histories`, `vss_data_path`) | `--offline` (and `--sourcesafe` naming a share is refused with it) |
| Microsoft Access may connect to the tables a database links to (on a server, or another database on a share) when it opens the database | `read_access_with_access` | Windows with Access installed | `--offline` (Access isn't used) |

Everything else is local. Every Git command except `ls-remote` runs with `GIT_ALLOW_PROTOCOL` empty, so Git can't use any transport, and with `GIT_NO_LAZY_FETCH=1` (`quiet_env`); `ls-remote` may use only `https`, `http`, `ssh`, `git` and `file`, and with `--offline` it isn't run (`ls_remote`). The tools are told not to ask for passwords: `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, Git's SSH in batch mode unless you set `GIT_SSH_COMMAND` yourself (`quiet_env`), `svn --non-interactive`, `tf /noprompt`, and every program's input is empty (`run`); a server that wants a password it doesn't have is skipped. The folder you scan may itself be on a network share; that's your choice.

scc and jscpd are run with no option that makes them connect anywhere (`SCC_ARGS`, `JSCPD_ARGS`, `tool_measures`).

## Programs it runs

All programs are started with an argument list, never through a shell (`run`, `git_log`, `sqlcmd`). On macOS and Linux they are found on `PATH` (`tool_path`; `sqlcmd` also in its usual install folders). On Windows, only `.exe` and `.com` files in absolute `PATH` folders are used (`windows_program`), never one in the current folder, and never a `.bat` or `.cmd` file (which Windows runs through `cmd.exe`); failing that, the usual install folders (`WINDOWS_TOOL_PATHS`, `SQLCMD_PATHS`). scc and jscpd are only ever run from the script's own cache, by full path (next section).

| Program | Subcommands | Function(s) | Protection against the scanned project's settings |
|---|---|---|---|
| `git` | `rev-parse`, `rev-list`, `log`, `show --shortstat`, `diff --shortstat` (between two commits), `for-each-ref`, `symbolic-ref`, `remote`, `remote get-url`, `ls-files`, `ls-remote` | `git_history`, `git_log`, `git_top`, `git_remotes`, `ls_remote`, `studio_branch`, `changes_to_epic_code`, `engine_changes_without_epic_history`, `git_default_branch`, `git_standard_commits`, `imported_git_history`, `git_tracked_files`, `version_control`, `size_project` | Every git command gets `-c` overrides of the repository settings that run programs (`GIT_SAFE_OPTIONS`: `core.fsmonitor`, `core.hooksPath`, `diff.external`, `log.showSignature`, `protocol.ext.allow=never`, `uploadpack.packObjectsHook`) and no credential helpers or password prompts (`GIT_NO_LOGINS`), except where `ls-remote` asks the repository's own remotes. Commands that produce diffs also get `--no-ext-diff --no-textconv` (`GIT_NO_PROGRAMS`). No transport except in `ls-remote` (`quiet_env`). `ls-remote` runs outside the repository (`GIT_DIR` set to the null device), so the repository's settings don't apply to it, with `--` before the URL (`ls_remote`). See "Git ownership" below for `safe.directory`. |
| `gh` | `api -X GET search/issues` | `github_merged_pull_requests` | Run from the temporary folder, so it reads no repository. |
| `hg` | `version -q` (from the temporary folder), `log` | `hg_skips_repository_settings`, `hg_history` | `HGRCSKIPREPO=1`, so the repository's `.hg/hgrc` (hooks, extensions) is ignored, and `HGPLAIN=1` (`quiet_env`). Mercurial older than 5.4 doesn't honour `HGRCSKIPREPO` everywhere, so it isn't run on the repository at all (`hg_skips_repository_settings`). |
| `p4` | `set -q P4PORT`, `changes` | `perforce_port_starts_a_program`, `perforce_history` | An `rsh:` port (which starts a command) set by a settings file in the folder is refused; only your own `P4PORT` variable may set one. `PWD` is set to the folder (`run`). |
| `svn` | `log --xml --non-interactive`, `info --show-item` | `svn_history`, `history_from_server` | Non-interactive. |
| `cvs` | `-q log` | `cvs_history` | A `CVS/Root` that would start a program (`:ext;CVS_RSH=...:`, or a host name beginning with `-`) is refused (`cvs_root_starts_a_program`). |
| `darcs` | `log --xml-output --no-prehook --no-posthook` | `darcs_history` | Hooks named in the repository's settings are switched off. |
| `brz` / `bzr` | `log --long -n0 .` | `bzr_history` | None specific. |
| `fossil` | `timeline` | `fossil_history` | None specific. |
| `tf` | `history . /recursive /noprompt /format:brief` | `tfvc_history` | No prompts. |
| `cm` | `find changeset`, `find review` | `plastic_history` | None specific. |
| `sqlcmd` | `-S <server> -d <database> -Q <query>` with three fixed read-only queries: database names (`sys.databases`), module definitions (`sys.sql_modules`), and a count of tables (`sys.tables`) | `sqlcmd`, `read_sql_server` | Only with `--sql-server`. Windows sign-in (`-E`) unless `SQLCMDUSER` is set. The server's certificate is checked unless you add `--trust-server-certificate` (sqlcmd's `-C`). |
| `powershell` | `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File <temp>\read_access.ps1 <temp copy>`, where `read_access.ps1` is the script's own fixed text, `ACCESS_POWERSHELL`, written to a temporary folder | `read_access_with_access`, `ACCESS_POWERSHELL` | Windows only. Access gets a temporary copy, never the original. The script sets Access's `AutomationSecurity` to 3 (force-disable macros and VBA) and checks that it took; if not, the database isn't opened. Not used with `--offline`. |
| `mdb-queries`, `mdb-export` (mdbtools) | `mdb-queries -L -1 <db>`, `mdb-queries <db> <query>`, `mdb-export <db> MSysObjects` | `read_access_with_mdbtools` | Reads the file; the only table it exports is Access's own catalog of objects. |
| `scc` 4.1.0 | `-x csv [...] --by-file --format json .` (twice: logical and generated lines), and with `--reports` once more | `tool_measures`, `run_tool` | Pinned build, checked before every run (next section). Doesn't follow symbolic links. |
| `jscpd` 5.4.1 | `. --min-tokens 50 --min-lines 5 --reporters json [--formats-exts ...] --output <temp> --config <temp>/jscpd.json` | `tool_measures`, `run_tool` | Pinned build, checked before every run. Given its own configuration file, so a `.jscpd.json` or a `"jscpd"` section in `package.json` in the project is ignored. Doesn't follow symbolic links (that's off unless asked for). |

## Files and folders it writes

- **The report**: `size_report_<name>.txt` and `size_report_<name>.json`, and with `--reports` also `size_report_<name>_scc.json` and `size_report_<name>_jscpd.json` (`save_report`, `write_report_file`). They go in the folder that holds the script (inside the project, if you put the script there); if it can't write there, the current folder; then the home folder. `<name>` is the scanned folder's (or file's) name with everything but letters and digits replaced by `_`, so it can't name another folder. A file of the same name is overwritten; a symbolic link of that name is removed rather than written through.
- **The tool cache** (`tools_folder`, `find_tool`): `%LOCALAPPDATA%\size_codebase_tools` on Windows, `~/Library/Caches/size_codebase_tools` on macOS, `$XDG_CACHE_HOME/size_codebase_tools` or `~/.cache/size_codebase_tools` on Linux, holding `scc-4.1.0/scc[.exe]` and `jscpd-5.4.1/jscpd[.exe]` (each written as `<name>.part`, then renamed). A cached copy that fails its checksum is deleted.
- **Temporary folders** (`temp_folder`), made with `tempfile.mkdtemp` in your temporary folder: `size_codebase_jscpd_*`, holding jscpd's configuration and its report (which holds copies of duplicated code), deleted as soon as jscpd is done (`tool_measures`); and on Windows `size_codebase_access_*`, holding a copy of an Access database and the PowerShell script that reads it, deleted straight after (`read_access_database`). If a run is killed, a later run deletes such folders once they're a day old (`remove_old_temp_folders`), skipping links.

The programs it runs may keep their own caches and settings as they normally do (Mercurial and Darcs caches in the repository, `gh` and `p4` state in your profile, Access's own settings).

## What it reads outside the scanned folder

- **Folders above it**, up to six levels, for version-control markers (`.git`, `.svn`, `.hg`, `CVS/Root`, `.bzr`, Perforce settings files and so on: `find_up`, `nearest`, `version_control`); Git itself finds the repository the folder belongs to, which may start higher up.
- **A custom-built Unreal Engine** the project uses: looked up in the registry (`HKEY_CURRENT_USER\Software\Epic Games\Unreal Engine\Builds`) or Unreal's `Install.ini` (`~/.config/Epic/UnrealEngine/` on Linux, `~/Library/Application Support/Epic/UnrealEngine/` on macOS) (`registered_unreal_engines`), or in up to five folders above the project; its `Build.version` and version-control history are read (`find_custom_engine`, `engine_report`).
- **Unity's Asset Store downloads**, when a Unity project is found: `.unitypackage` files under `%APPDATA%\Unity\Asset Store*`, `~/Library/Unity/Asset Store*` or `~/.local/share/unity3d/Asset Store*`, and `ASSETSTORE_CACHE_PATH`. Only the names of the entries in each package are read, streamed, for at most 300 seconds (`asset_store_download_folders`, `asset_store_guids`).
- **SourceSafe databases**: those named with `--sourcesafe`, by `SSDIR`, and by the project's own files if they are on this computer (not on a network share) (`SourceSafe`, `vss_data_path`, `read_sourcesafe`).
- **The tool cache and the temporary folder** (above).
- **Environment variables** read by the script itself: `PATH`, `SSDIR`, `ASSETSTORE_CACHE_PATH`, `P4CONFIG` and `P4PORT` (`version_control`, `perforce_port_starts_a_program`), `SQLCMDUSER` (only whether it's set: `sqlcmd`), `GIT_SSH_COMMAND` (only to leave yours in place: `quiet_env`), `LOCALAPPDATA`, `APPDATA`, `XDG_CACHE_HOME`, and the home and temporary folders. Programs it runs get your whole environment, plus the settings in `quiet_env`.
- **Your tools' own settings and credentials**, used by those tools, not read by the script: Git's user and system configuration (and its credential helpers, for `ls-remote` only), SSH keys and configuration, `gh`'s login, Perforce settings and tickets, SVN's and Plastic's and TFVC's credentials, `sqlcmd`'s `SQLCMDPASSWORD`. Python's own HTTPS download uses the system's certificates and any proxy set in the environment.

Inside the project, files that look like credentials are scanned to count them (`secrets_in`, `KEY_FILES`), never shown or saved.

## scc and jscpd: how they are verified

- **Pinned**: scc 4.1.0 and jscpd 5.4.1, one build per platform, each with its download URL, the SHA-256 of the download, and the SHA-256 of the program inside it (`PINNED_TOOLS`).
- **Downloaded** over HTTPS with Python's default certificate and host-name checks (`download`); there is no retry without verification. The download's SHA-256 must match, then only the one named program file is read from the archive, in memory (`archive_member`), and its SHA-256 must match too, before it is written to the cache (`find_tool`).
- **Re-checked before every run**: a cached copy is used only if it isn't a link and its SHA-256 matches (`find_tool`), and it is checked again just before each run (`run_tool`). A copy that doesn't match is deleted and, if allowed, downloaded again.
- **No other copy is ever run**: an `scc` or `jscpd` on `PATH` is never used.
- **If one can't be used** (no build for this computer, `--offline` or `--no-download` with nothing cached, a failed download or checksum, or the tool failing), its figures are left out of the report, which says why under "Not included in the standard measures above". The script doesn't estimate them. In the JSON, `logical_lines`, `generated_lines` or `duplication_ratio` are then `null`, and `not_measured` says why.

## What the saved report contains

The text report and its JSON copy hold counts, plus the following, and nothing else. Look the report over before sending it; these are the owner's own words.

- The script's name and version (first line), and whether `--offline` was used.
- The scanned folder's name; when a single file is scanned (an Access database, say), that file's name.
- Relative paths of folders inside the scanned folder: in the per-folder breakdown, project types found, folders with their own licence file, repositories inside the folder, and (JSON only) the full relative path of each project type found.
- Version strings read from project files and assets (Unity editor version, Unreal engine association, `Build.version`, the Unreal versions that saved the assets, Godot and other engine versions).
- Language names, file extensions (text files of unknown kinds), and names you gave with `--code-ext`.
- Library and package names: copied-in library folders' names, Unity Asset Store package names (the names of the `.unitypackage` files downloaded on this computer), licence names, packages named in package lists (`package.json`, `requirements.txt`, `.csproj` ...), library and folder names taken from paths in build files (the computer and share names of a network path are left out: `dependency_name`), the first folder name of `#include`d headers that aren't in the folder, and Git submodule names.
- Git remote names (such as `origin`), branch names, and SVN's path within its repository (such as `^/trunk`).
- If anyone can read the repository on github.com, gitlab.com or bitbucket.org, its address (`github.com/owner/repo`).
- A file's name, only if you mark that file with `--third-party`.
- Kinds of credentials found and how many files (never the text), kinds and sizes of data files, licence kinds, years in copyright notices, dates of changes.
- Error messages under "Problems while scanning" and for tools or databases that couldn't be used, with the scanned folder replaced by `<project>`, your home folder by `~`, and anything else that looks like a path, or a quoted file name, by `<path>` (`scrub`, `describe`). An unquoted bare file name (`main.c`) in a message would not be replaced; Python's own error messages quote file names.

It never holds source code, author names or email addresses (they're read to count people, and kept in memory only: `history`, `authors_in`), credentials, commit messages, or rows from database tables. Locations of SourceSafe databases named in the project's files are printed on screen only, never saved (`sourcesafe_lines`).

**With `--reports`**, two more files are saved beside it: scc's report, which lists every file's path with its line counts, and jscpd's, which holds **copies of the duplicated code** and the paths of the files they're in. Read them before sending them.

## Protections against a hostile project

The script is meant to be safe to run on a copy of code you don't control. Specifically:

- **Nothing from the project is executed.** The script never imports, evaluates or unpickles anything from the project (no `eval`, `exec`, `pickle` or `marshal`). It parses with regular expressions, `json`, `csv`, `xml.etree.ElementTree`, `zipfile`, `tarfile` (Unity packages: entry names only, streamed) and `struct`. No archive is ever extracted to disk, so archive entry names can't write anywhere: `.dacpac`, `.bacpac` and `.ispac` members are read into memory by name (`read_dac_package`, `database_file`), and so is the one program file taken from scc's and jscpd's downloads (`archive_member`).
- **Symbolic links and junctions are not followed**: the walk skips linked folders and linked files and counts them (`is_link`, `size_project`), and skips named pipes and devices (`S_ISREG`). scc and jscpd don't follow links either.
- **Git ownership.** Git refuses a repository that belongs to another user account ("dubious ownership"). The script never uses `safe.directory=*`. Only when Git refuses a repository for that reason is the same command run again with `safe.directory=<that repository>` on its command line, with all the overrides above still in place (`run`, `other_owners_repository`, `command`). Your Git settings aren't changed, and the report says when this happened.
- **Git settings that run programs** (hooks, fsmonitor, external diff and textconv drivers, signature checkers, credential helpers, `ext::` URLs, remote helper programs, lazy fetches) are overridden or blocked on every command (see the table above). Remote URLs are passed after `--`, so one can't pose as an option.
- **Mercurial, Darcs, CVS and Perforce settings that run programs** are ignored or refused (see the table above).
- **Network locations in project files aren't opened**: SourceSafe locations in project files and a `Data_Path` in `srcsafe.ini` that point to a network share (`SourceSafe.histories`, `vss_data_path`), and Git remotes in a folder on a network share (`remote_on_network_share`). The script only opens a network location you name (`--sourcesafe`, `SSDIR`, the folder you scan).
- **Access databases**: opened only as a temporary copy, only after Access confirms that macros and VBA are force-disabled, and never with `--offline` (`read_access_database`, `ACCESS_POWERSHELL`).
- **Programs on Windows** are never taken from the current folder or run as batch files (`windows_program`).
- **The report can't be redirected**: a link planted where a report file goes is replaced, not followed (`write_report_file`).

## Residual risks

These are the risks we know of and judge acceptable; the mitigation for each is `--offline`, a disposable machine, or both.

- **Online, servers named in a copied working copy are contacted.** Without `--offline`, the Git remotes, SVN, CVS, Bazaar, Plastic and TFVC servers that the copy's own settings name are asked for history, with whatever credentials your tools hold for those servers. If `P4CONFIG` is set, a Perforce settings file in the project can point `p4` at another server, which then receives your Perforce user name (and the password, if you keep one in `P4PASSWD`).
- **On Windows, version-control data can name a network share.** A hostile repository's own files can make the version-control tool, not the script, open a folder on another computer: for example Git's `include.path` setting, a `.git` file's `gitdir:` line, or `objects/info/alternates`; Mercurial's `sharedpath`; a Fossil checkout's repository path. Windows may then send your sign-in (NTLM) to that computer. `--offline` does not prevent this. For untrusted code on Windows, use a virtual machine, or block outgoing SMB (port 445).
- **Microsoft Access** (Windows, without `--offline`): with macros and VBA force-disabled, a database's startup form can still open, and a form bound to a linked table makes Access connect to where that table is, with your sign-in.
- **Other programs parse the project's files**: Git and the other version-control tools, scc, jscpd, mdbtools and Microsoft Access. A flaw in one of them is outside the script's control. Keep them up to date: the script refuses Mercurial older than 5.4 and works around CVS's program-starting roots, but it doesn't work around old, since-fixed flaws in other tools (for example ssh host names beginning with `-` in old SVN and Bazaar).
- **Resource use.** The script's own parsers are pure Python, so a malformed file can't corrupt memory, but a hostile project can make the scan slow or memory-hungry (huge files, decompression bombs in `.dacpac` or `.ispac` files). XML is parsed with Python's `expat`, whose versions from 2.4.1 on limit entity expansion.
- **A few files are opened by name and do follow links**, such as `ProjectSettings/ProjectVersion.txt`, a `.uproject`, `Build.version`, `project.godot`, `.gitmodules`, `CVS/Root`, `srcsafe.ini`, a Unity `.meta` file and the licence file at the top. Only a version, guid or similar short field is taken from them (and the licence's kind). A link from one of them to a device could stall the scan.
- **Leftover temporary files.** If a run is killed, jscpd's report (copies of duplicated code) or a copy of an Access database stays in your temporary folder until a later run removes it a day later. Delete `size_codebase_*` folders there by hand if you need them gone sooner.
- **The tool cache is in your own profile.** scc and jscpd are checked just before they start; a program already running as you could swap the file in between, but such a program could do worse anyway.

## Verifying your copy

Each release is tagged `v<version>` in the public repository, <https://github.com/patinasource/size-codebase>, which also has a `SHA256SUMS` file with the SHA-256 of `size_codebase.py`. The version is in the file (`__version__`), on the first line of every report (`size_codebase.py 1.0.0`), in the JSON (`script_version`), and on the first line of `--help`.

Compute the checksum of your copy and compare it with `SHA256SUMS` at that release's tag:

- macOS: `shasum -a 256 size_codebase.py`
- Linux: `sha256sum size_codebase.py`
- Windows (PowerShell): `Get-FileHash size_codebase.py -Algorithm SHA256` (it prints the hash in capitals; compare without regard to case)

## Reporting a security problem

Email hello@patinasource.com. Please include the script's version and how to reproduce the problem.
