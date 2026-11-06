# Security

This page is for anyone deciding whether to run `size_codebase.py` on their code: a security engineer, or an AI assistant asked "is this safe to run?". The statements below name the functions in `size_codebase.py` that do each thing (by name, not line number), so you can check them. The script is one file of standard-library Python (3.8 or later), with no dependencies.

## Summary

`size_codebase.py` reads a folder and writes a report about it: lines of code by language, the owner's code versus someone else's, version-control history (commits, contributors, pull requests, reviews, changes marked as made with AI tools), assets and what they are (characters, items, levels), the online services the game uses, its tests and build automation, and the standard measures that codebase questionnaires ask for. It doesn't change the project, only reads it (version-control tools may update their own caches, as they always do, and the report is saved next to the script, wherever that is). It uploads nothing: no code and no report are sent anywhere, and servers are only asked the questions listed below. The report stays on your computer, and you decide whether to send it to anyone. It holds counts, the names of folders, languages, libraries, packages and branches, and the names of the online services and tools it recognises from its own lists (the full list is [below](#what-the-saved-report-contains)); it holds no source code, no author names or email addresses, no credentials, no file or class names, and no web addresses.

It downloads nothing: the standard measures (logical lines as scc counts them, duplication as jscpd measures it) are counted by the script itself, without running any other program. Its only network connections, all listed below, ask your version-control servers for history and pull-request counts, with the access you already have. `--offline` turns all of that off.

## How to run it

**Normally:**

```
python3 size_codebase.py "/path/to/project"
```

On Windows, `py` instead of `python3`. `--help` prints the options.

**Where policy forbids tools from making any network connection, offline** (none of your code is sent anywhere either way; this only stops the server queries listed below):

```
python3 size_codebase.py --offline "/path/to/project"
```

With `--offline` the script makes no network connection of its own (see the table below for exactly what that switches off). What it leaves out, and the report then says so in a "Left out because of that" list:

- Pull-request counts from Git servers and from GitHub's API, and the check of whether the repository is public. Pull requests named in commit messages are still counted.
- Histories that come from a server: Perforce, Plastic SCM, TFVC, and SVN, CVS or Bazaar when their history isn't on this computer. Git, Mercurial, Fossil, Darcs, and local SVN, CVS and Bazaar histories are still read.
- A SourceSafe database or custom Unreal Engine on a network share named by your settings (`SSDIR`, the Unreal registration), and a Unity Asset Store cache on a network share.
- Access databases are not opened in Microsoft Access (mdbtools, if installed, still reads their queries and object counts).
- `--sql-server` and `--network-sourcesafe` can't be combined with `--offline`; the script stops with a message.

**For code you don't trust**, also run it in a disposable virtual machine or container that holds no credentials and has no network, for example:

```
docker run --rm --network none -v "/path/to/project:/src:ro" -v "$PWD/out:/out" python:3.12-slim \
    python3 /out/size_codebase.py --offline /src
```

(with `size_codebase.py` copied into `out/` first: the report is saved next to the script). The image needs `git` installed for the Git history to be read. See [residual risks](#residual-risks) for why this is worth doing for hostile code.

## Network connections

This is every connection the script can cause. "Off with" names the options that prevent it.

| Connection | Function(s) | When | Off with |
|---|---|---|---|
| `git ls-remote` to each Git remote, to count pull-request refs, with your own Git credentials | `git_server_pull_requests`, `ls_remote` | Git repositories with remotes. Not Epic's Unreal Engine repository, and not remotes in a folder on a network share (`remote_on_network_share`) | `--offline` |
| `gh api` (GitHub's command-line tool, your login) to `api.github.com`: three searches of the pull requests of `owner/repo` (merged; merged and approved in a review; merged without any review), each sending that name; only the number found is read | `github_merged_pull_requests`, `github_pull_request_reviews`, `github_search_count` | GitHub remotes, if `gh` is installed and logged in | `--offline` |
| `git ls-remote` over HTTPS without any login to `github.com`, `gitlab.com` or `bitbucket.org`, to see whether anyone can read the repository (sends the `owner/repo` name) | `public_repositories`, `ls_remote` | Remotes on those three services | `--offline` |
| `p4 changes` to your Perforce server (or `p4`'s default, `perforce:1666`) | `perforce_history` | Whenever `p4` is installed (Perforce settings often live outside the folder, so `p4` is asked) | `--offline` (p4 isn't run at all) |
| `svn log`, `cvs -q log`, `brz log`/`bzr log`, `cm find`, `tf history` to the server their working copy names | `svn_history`, `cvs_history`, `bzr_history`, `plastic_history`, `tfvc_history`; `history_from_server` decides | When that system is found and its tool installed | `--offline`, unless the history is on this computer (`history_from_server`) |
| `sqlcmd` to the SQL Server you name | `read_sql_server`, `sqlcmd` | Only with `--sql-server` | Not given; refused with `--offline` |
| Reading a folder on a network share | `SourceSafe`, `read_sourcesafe` (`--sourcesafe`, `SSDIR`); `find_custom_engine` (an Unreal engine registered on a share); `asset_store_download_folders` (`ASSETSTORE_CACHE_PATH` on a share) | Only where you or your settings name it. SourceSafe locations on a network share named by the project's own files are opened only with `--network-sourcesafe` (`SourceSafe.histories`, `vss_data_path`) | `--offline` (and `--sourcesafe` naming a share, or `--network-sourcesafe`, is refused with it) |
| Microsoft Access may connect to the tables a database links to (on a server, or another database on a share) when it opens the database | `read_access_with_access` | Windows with Access installed | `--offline` (Access isn't used) |

Everything else is local. Every Git command except `ls-remote` and one `fetch` runs with `GIT_ALLOW_PROTOCOL` empty, so Git can't use any transport, and with `GIT_NO_LAZY_FETCH=1` (`quiet_env`); `ls-remote` may use only `https`, `http`, `ssh`, `git` and `file`, and with `--offline` it isn't run (`ls_remote`). The `fetch` reads a Git bundle named with `--history`, a file on this computer, into a temporary repository, and may use only `file` (`git_bundle_history`). The tools are told not to ask for passwords: `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, Git's SSH in batch mode unless you set `GIT_SSH_COMMAND` yourself (`quiet_env`), `svn --non-interactive`, `tf /noprompt`, and every program's input is empty (`run`); a server that wants a password it doesn't have is skipped. The folder you scan may itself be on a network share; that's your choice.

The standard measures are counted by the script itself, from the files it reads (`Measures`, `count_lines`, `Duplication`): no program is run and nothing is downloaded for them. (Versions before 1.7 downloaded scc and jscpd for this; a copy they left in `size_codebase_tools`, in your cache folder, is no longer used, and can be deleted.)

## Programs it runs

All programs are started with an argument list, never through a shell (`run`, `git_log`, `sqlcmd`). On macOS and Linux they are found on `PATH` (`tool_path`; `cm` and `sqlcmd` also in their usual install folders, `POSIX_TOOL_PATHS` and `SQLCMD_PATHS`). On Windows, only `.exe` and `.com` files in absolute `PATH` folders are used (`windows_program`), never one in the current folder, and never a `.bat` or `.cmd` file (which Windows runs through `cmd.exe`); failing that, the usual install folders (`WINDOWS_TOOL_PATHS`, `SQLCMD_PATHS`).

| Program | What it's run for | Subcommands | Function(s) | Protection against the scanned project's settings |
|---|---|---|---|---|
| `git` | Reading the Git history: commits, their authors and dates, and branches (`log`, `rev-list`, `for-each-ref`, `symbolic-ref`, `rev-parse`); whether a big first commit imported the code from elsewhere (`show --shortstat`), and what conversion tools left besides the commit messages (`for-each-ref` on `refs/svn/map`, `refs/notes/hg`, `refs/tags/TFS_C*` and the like, and `rev-parse --git-common-dir` to look for files such as `.git/svn` in the repository's folder); in a fork of Unreal Engine, how much the studio changed Epic's code (`diff --shortstat`); which files Git holds, to point out code that was never committed (`ls-files`); and the repository's remotes, to count pull requests on the server and check whether anyone can read the repository (`remote`, `ls-remote`); who changed code files, to count those contributors (`log` with pathspecs of code files' extensions); a Git bundle named with `--history` is fetched into a temporary bare repository, the only one git writes to (`init --bare`, `fetch`, `bundle list-heads`, `symbolic-ref HEAD`) | `rev-parse`, `rev-list`, `log`, `show --shortstat`, `diff --shortstat` (between two commits), `for-each-ref`, `symbolic-ref`, `remote`, `remote get-url`, `ls-files`, `ls-remote`, `init --bare`, `fetch`, `bundle list-heads` | `git_history`, `git_bundle_history`, `git_log`, `git_conversion_traces`, `git_top`, `git_remotes`, `ls_remote`, `studio_branch`, `changes_to_epic_code`, `engine_changes_without_epic_history`, `git_default_branch`, `git_standard_commits`, `imported_git_history`, `git_tracked_files`, `git_code_contributors`, `version_control`, `size_project` | Every git command gets `-c` overrides of the repository settings that run programs (`GIT_SAFE_OPTIONS`: `core.fsmonitor`, `core.hooksPath`, `diff.external`, `log.showSignature`, `protocol.ext.allow=never`, `uploadpack.packObjectsHook`) and no credential helpers or password prompts (`GIT_NO_LOGINS`), except where `ls-remote` asks the repository's own remotes. Commands that produce diffs also get `--no-ext-diff --no-textconv` (`GIT_NO_PROGRAMS`). No transport except in `ls-remote` (`quiet_env`). `ls-remote` runs outside the repository (`GIT_DIR` set to the null device), so the repository's settings don't apply to it, with `--` before the URL (`ls_remote`). See "Git ownership" below for `safe.directory`. |
| `gh` | Counting merged pull requests on GitHub, and those of them approved in a review or merged without one, for a GitHub remote, if GitHub's command-line tool is installed and logged in | `api -X GET search/issues` | `github_search_count` (for `github_merged_pull_requests`, `github_pull_request_reviews`) | Run from the temporary folder, so it reads no repository. |
| `hg` | Reading a Mercurial history; `version` checks that Mercurial is new enough to ignore the repository's own settings | `version -q` (from the temporary folder), `log` (the template also asks for each changeset's extras, where `hg convert` records the change it converted) | `hg_skips_repository_settings`, `hg_history` | `HGRCSKIPREPO=1`, so the repository's `.hg/hgrc` (hooks, extensions) is ignored, and `HGPLAIN=1` (`quiet_env`). Mercurial older than 5.4 doesn't honour `HGRCSKIPREPO` everywhere, so it isn't run on the repository at all (`hg_skips_repository_settings`). |
| `p4` | Reading a Perforce history (submitted changelists); `set` reads where your `P4PORT` setting comes from | `set -q P4PORT`, `changes` | `perforce_port_starts_a_program`, `perforce_history` | An `rsh:` port (which starts a command) set by a settings file in the folder is refused; only your own `P4PORT` variable may set one. `PWD` is set to the folder (`run`). |
| `svn` | Reading an SVN history; `info` finds where the repository is, and which path in it was checked out; for an SVN repository's own folder named with `--history` whose revision properties are packed or kept in Berkeley DB, its log from the `file://` address | `log --xml --non-interactive`, `info --show-item` | `svn_history`, `history_from_server`, `svn_repository_history` | Non-interactive. `svn log` runs no repository hooks. SVN dumps and unpacked FSFS repositories are read by the script itself, without `svn`. |
| `cvs` | Reading a CVS history | `-q log` | `cvs_history` | A `CVS/Root` that would start a program (`:ext;CVS_RSH=...:`, or a host name beginning with `-`) is refused (`cvs_root_starts_a_program`). |
| `darcs` | Reading a Darcs history | `log --xml-output --no-prehook --no-posthook` | `darcs_history` | Hooks named in the repository's settings are switched off. |
| `brz` / `bzr` | Reading a Bazaar history (with revision ids, which name an SVN or Git change a revision was converted from) | `log --long --show-ids -n0 .` | `bzr_history` | None specific. |
| `fossil` | Reading a Fossil history, and the tags `fossil import --svn` gives each SVN revision | `timeline`, `tag list` | `fossil_history` | None specific. |
| `tf` | Reading a Team Foundation (TFVC) history | `history . /recursive /noprompt /format:brief` | `tfvc_history` | No prompts. |
| `cm` | Reading a Plastic SCM (Unity Version Control) history: changesets, merges and code reviews | `find changeset`, `find merge`, `find review` | `plastic_history`, `cm_find` | None specific. |
| `sqlcmd` | Reading the code (procedures, functions, views, triggers) stored in the SQL Server you name with `--sql-server` | `-S <server> -d <database> -Q <query>` with three fixed read-only queries: database names (`sys.databases`), module definitions (`sys.sql_modules`), and a count of tables (`sys.tables`) | `sqlcmd`, `read_sql_server` | Only with `--sql-server`. Windows sign-in (`-E`) unless `SQLCMDUSER` is set. The server's certificate is checked unless you add `--trust-server-certificate` (sqlcmd's `-C`). |
| `powershell` | Driving Microsoft Access, to read an Access database's queries, VBA code and list of forms, reports, macros and modules | `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File <temp>\read_access.ps1 <temp copy>`, where `read_access.ps1` is the script's own fixed text, `ACCESS_POWERSHELL`, written to a temporary folder | `read_access_with_access`, `ACCESS_POWERSHELL` | Windows only. Access gets a temporary copy, never the original. The script sets Access's `AutomationSecurity` to 3 (force-disable macros and VBA) and checks that it took; if not, the database isn't opened. Not used with `--offline`. |
| `mdb-queries`, `mdb-export` (mdbtools) | Reading an Access database's queries and counting its objects, where Microsoft Access isn't available | `mdb-queries -L -1 <db>`, `mdb-queries <db> <query>`, `mdb-export <db> MSysObjects` | `read_access_with_mdbtools` | Reads the file; the only table it exports is Access's own catalog of objects. |

## Files and folders it writes

- **The report**: `size_report_<name>.txt` and `size_report_<name>.json`, and with `--reports` also `size_report_<name>_lines.json` and `size_report_<name>_duplication.json` (`save_report`, `write_report_file`). They go in the folder that holds the script (inside the project, if you put the script there); if it can't write there, the current folder; then the home folder. `<name>` is the scanned folder's (or file's) name with everything but letters and digits replaced by `_`, so it can't name another folder. A file of the same name is overwritten; a symbolic link of that name is removed rather than written through.
- **Temporary folders** (`temp_folder`), made with `tempfile.mkdtemp` in your temporary folder: on Windows `size_codebase_access_*`, holding a copy of an Access database and the PowerShell script that reads it, deleted straight after (`read_access_database`); and `size_codebase_bundle_*`, the bare repository a Git bundle named with `--history` is fetched into, deleted as soon as its history is read (`git_bundle_history`). If a run is killed, a later run deletes such folders once they're a day old (`remove_old_temp_folders`), skipping links; it deletes too the `size_codebase_jscpd_*` folders that versions before 1.7 could leave behind (they held jscpd's report, with copies of duplicated code).

The programs it runs may keep their own caches and settings as they normally do (Mercurial and Darcs caches in the repository, `gh` and `p4` state in your profile, Access's own settings).

## What it reads outside the scanned folder

- **Folders above it**, up to six levels, for version-control markers (`.git`, `.svn`, `.hg`, `.plastic`, `CVS/Root`, `.bzr`, Perforce settings files and so on: `find_up`, `nearest`, `marker_found`, `version_control`), and Mercurial's `.hg/git-mapfile` (hg-git's list of the Git commit each changeset is); Git itself finds the repository the folder belongs to, which may start higher up.
- **A custom-built Unreal Engine** the project uses: looked up in the registry (`HKEY_CURRENT_USER\Software\Epic Games\Unreal Engine\Builds`) or Unreal's `Install.ini` (`~/.config/Epic/UnrealEngine/` on Linux, `~/Library/Application Support/Epic/UnrealEngine/` on macOS) (`registered_unreal_engines`), or in up to five folders above the project; its `Build.version` and version-control history are read (`find_custom_engine`, `engine_report`).
- **Unity's Asset Store downloads**, when a Unity project is found: `.unitypackage` files under `%APPDATA%\Unity\Asset Store*`, `~/Library/Unity/Asset Store*` or `~/.local/share/unity3d/Asset Store*`, and `ASSETSTORE_CACHE_PATH`. Only the names of the entries in each package are read, streamed, for at most 300 seconds (`asset_store_download_folders`, `asset_store_guids`).
- **Old history named with `--history`**: only inside the folders and files named (`history_places`, `read_history_place`). Symbolic links in them aren't followed; files are opened only if they're named like an SVN dump or Git bundle, and only their first bytes until they prove to be one; an SVN repository's `db/revprops` files are read for each revision's author, date and message (`svn_repository_history`). No folder above them is looked at for markers (`version_control` with `inside_only`), Git is given `GIT_CEILING_DIRECTORIES` so it can't find a repository above them (`quiet_env`), and their remotes aren't asked for pull requests (`git_history` with `servers=False`).
- **SourceSafe databases**: those named with `--sourcesafe`, by `SSDIR`, and by the project's own files if they are on this computer, or on a network share with `--network-sourcesafe` (`SourceSafe`, `vss_data_path`, `read_sourcesafe`).
- **The temporary folder** (above).
- **Environment variables** read by the script itself: `PATH`, `SSDIR`, `ASSETSTORE_CACHE_PATH`, `P4CONFIG` and `P4PORT` (`version_control`, `perforce_port_starts_a_program`), `SQLCMDUSER` (only whether it's set: `sqlcmd`), `GIT_SSH_COMMAND` (only to leave yours in place: `quiet_env`), `LOCALAPPDATA`, `APPDATA`, `XDG_CACHE_HOME`, and the home and temporary folders. Programs it runs get your whole environment, plus the settings in `quiet_env`.
- **Your tools' own settings and credentials**, used by those tools, not read by the script: Git's user and system configuration (and its credential helpers, for `ls-remote` only), SSH keys and configuration, `gh`'s login, Perforce settings and tickets, SVN's and Plastic's and TFVC's credentials, `sqlcmd`'s `SQLCMDPASSWORD`.

Inside the project, files that look like credentials are scanned to count them (`secrets_in`, `KEY_FILES`), never shown or saved. Other files are read to count what they show, never to keep what they say: code (for test definitions, Unreal C++ classes, web requests, multiplayer code, web addresses and links to documents: `read_code_file`), settings files under 1 MB (web addresses and links, in the same read that looks for credentials: `size_project`), Markdown and text documents (lines, links: `Practices`), Unity test assembly definitions (`.asmdef`), licence files in someone else's folders (their kind: `folder_licence`), Unity prefabs, `.asset` files and models' `.meta` files (their components, scripts and rig: `GameContent`), and a project's `.uproject`, `Config/DefaultEngine.ini`, `Config/DefaultGame.ini`, `ProjectSettings/EditorBuildSettings.asset` and `ProjectSettings/UnityConnectSettings.asset` (plugins, levels to package, online settings: `GameContent`, `OnlineServices`). All but the code and the settings files are read by `read_settings_file`, which follows no links and reads only regular files, at most 2 MB of each (4 MB of a prefab).

## What the saved report contains

The text report and its JSON copy hold counts, plus the following, and nothing else. Look the report over before sending it; these are the owner's own words.

- The script's name and version (first line), and whether `--offline` was used.
- The scanned folder's name; when a single file is scanned (an Access database, say), that file's name.
- Relative paths of folders inside the scanned folder: in the per-folder breakdown, project types found, folders with their own licence file, the studio's own plugins, packages and submodules, repositories inside the folder, folders holding test-coverage reports or raw coverage data, and (JSON only) the full relative path of each project type found.
- Version strings read from project files and assets (Unity editor version, Unreal engine association, `Build.version`, the Unreal versions that saved the assets, Godot and other engine versions).
- Language names, file extensions (text files of unknown kinds), and names you gave with `--code-ext`.
- Library and package names: copied-in library folders' names, Unity Asset Store package names (the names of the `.unitypackage` files downloaded on this computer), licence names, packages named in package lists (`package.json`, `requirements.txt`, `.csproj` ...), library and folder names taken from paths in build files (the computer and share names of a network path are left out: `dependency_name`), the first folder name of `#include`d headers that aren't in the folder, and Git submodule names.
- Git remote names (such as `origin`), branch names, and SVN's path within its repository (such as `^/trunk`).
- Names from the script's own lists, never the project's words: online services (`ONLINE_SERVICES`, `PLATFORM_SERVICE_NAMES`, `UNITY_CONNECT_SERVICES`), AI coding tools (`AI_MARKERS`, `AI_TOOL_FILES`), build-automation systems (`CI_FILES`), document services (`DOCUMENT_SERVICES`), art and audio tools (`SOURCE_ART_EXTS`), kinds of test (`TEST_DEFINITIONS`), kinds of class, prefab and level (`UNREAL_CLASS_KINDS`, `UNITY_PREFAB_KINDS`), and where someone else's library came from (`unreal_plugin_terms`, `FOLDER_TERMS`, licence kinds). With each service, how it was found (a plugin, a package, a setting, a web address).
- If anyone can read the repository on github.com, gitlab.com or bitbucket.org, its address (`github.com/owner/repo`).
- A file's name, only if you mark that file with `--third-party`.
- Kinds of credentials found and how many files (never the text), kinds and sizes of data files, licence kinds, years in copyright notices, dates of changes.
- Test-coverage figures: each report's format, date and counts (never the names of the files it covers), and the kinds of raw coverage data found.
- Counts of what the game holds and how the studio works: classes, prefabs and data assets by kind; levels, those the project's settings put in the build and those named like test levels; assets by owner; test definitions; files of build-automation and AI-tool settings; documents and their lines; links to documents kept elsewhere, by service; art and audio tools' files; files with multiplayer code or web requests; web hosts in the code and settings; changes marked as made with AI tools; changes naming a reviewer; contributors who changed code.
- Error messages under "Problems while scanning" and for tools or databases that couldn't be used, with the scanned folder replaced by `<project>`, your home folder by `~`, and anything else that looks like a path, or a quoted file name, by `<path>` (`scrub`, `describe`). An unquoted bare file name (`main.c`) in a message would not be replaced; Python's own error messages quote file names.

It never holds source code, author names or email addresses (they're read to count people, and kept in memory only: `history`, `authors_in`), credentials, commit messages, or rows from database tables. Nor does it hold the names of classes, levels, prefabs or other assets, web addresses or their hosts, or links to documents: they're kept in memory only, to tie things together and count each once (`GameContent`, `OnlineServices.hosts`, `Practices.links`); a web host is named only as one of the known services it belongs to. Locations of SourceSafe databases named in the project's files are printed on screen only, never saved (`sourcesafe_lines`).

**With `--reports`**, two more files are saved beside it, for attaching to a form: the lines by language (files, lines, code, comments, blank lines and bytes for each language, laid out as scc's JSON report is) and the duplication totals (for each language and in all, and the date, as jscpd's report's `statistics` are) (`Measures.figures`). Neither holds code or file names: the copies of code found are only counted, never kept.

## Protections against a hostile project

The script is meant to be safe to run on a copy of code you don't control. Specifically:

- **Nothing from the project is executed.** Test coverage is only read from reports the project's tests already wrote; the tests are never run, and raw coverage data that needs the project's own tools is only named, never interpreted (`CoverageReports`). The script never imports, evaluates or unpickles anything from the project (no `eval`, `exec`, `pickle` or `marshal`). It parses with regular expressions, `json`, `csv`, `xml.etree.ElementTree`, `zipfile`, `tarfile` (Unity packages: entry names only, streamed) and `struct`. No archive is ever extracted to disk, so archive entry names can't write anywhere: `.dacpac`, `.bacpac` and `.ispac` members are read into memory by name (`read_dac_package`, `database_file`),.
- **Symbolic links and junctions are not followed**: the walk skips linked folders and linked files and counts them (`is_link`, `size_project`), and skips named pipes and devices (`S_ISREG`).
- **Git ownership.** Git refuses a repository that belongs to another user account ("dubious ownership"). The script never uses `safe.directory=*`. Only when Git refuses a repository for that reason is the same command run again with `safe.directory=<that repository>` on its command line, with all the overrides above still in place (`run`, `other_owners_repository`, `command`). Your Git settings aren't changed, and the report says when this happened.
- **Git settings that run programs** (hooks, fsmonitor, external diff and textconv drivers, signature checkers, credential helpers, `ext::` URLs, remote helper programs, lazy fetches) are overridden or blocked on every command (see the table above). Remote URLs are passed after `--`, so one can't pose as an option.
- **Mercurial, Darcs, CVS and Perforce settings that run programs** are ignored or refused (see the table above).
- **Network locations in project files aren't opened by default**: SourceSafe locations in project files and a `Data_Path` in `srcsafe.ini` that point to a network share (`SourceSafe.histories`, `vss_data_path`), and Git remotes in a folder on a network share (`remote_on_network_share`). The script only opens a network location you name (`--sourcesafe`, `SSDIR`, the folder you scan), or, with `--network-sourcesafe`, the SourceSafe locations the project files name. Use that option only for a project you trust: on Windows, opening a share can send your sign-in to that computer.
- **Access databases**: opened only as a temporary copy, only after Access confirms that macros and VBA are force-disabled, and never with `--offline` (`read_access_database`, `ACCESS_POWERSHELL`).
- **Programs on Windows** are never taken from the current folder or run as batch files (`windows_program`).
- **The report can't be redirected**: a link planted where a report file goes is replaced, not followed (`write_report_file`).

## Residual risks

These are the risks we know of and judge acceptable; the mitigation for each is `--offline`, a disposable machine, or both.

- **Online, servers named in a copied working copy are contacted.** Without `--offline`, the Git remotes, SVN, CVS, Bazaar, Plastic and TFVC servers that the copy's own settings name are asked for history, with whatever credentials your tools hold for those servers. If `P4CONFIG` is set, a Perforce settings file in the project can point `p4` at another server, which then receives your Perforce user name (and the password, if you keep one in `P4PASSWD`).
- **On Windows, version-control data can name a network share.** A hostile repository's own files can make the version-control tool, not the script, open a folder on another computer: for example Git's `include.path` setting, a `.git` file's `gitdir:` line, or `objects/info/alternates`; Mercurial's `sharedpath`; a Fossil checkout's repository path. Windows may then send your sign-in (NTLM) to that computer. `--offline` does not prevent this. For untrusted code on Windows, use a virtual machine, or block outgoing SMB (port 445).
- **Microsoft Access** (Windows, without `--offline`): with macros and VBA force-disabled, a database's startup form can still open, and a form bound to a linked table makes Access connect to where that table is, with your sign-in.
- **Other programs parse the project's files**: Git and the other version-control tools, mdbtools and Microsoft Access. A flaw in one of them is outside the script's control. Keep them up to date: the script refuses Mercurial older than 5.4 and works around CVS's program-starting roots, but it doesn't work around old, since-fixed flaws in other tools (for example ssh host names beginning with `-` in old SVN and Bazaar).
- **Resource use.** The script's own parsers are pure Python, so a malformed file can't corrupt memory, but a hostile project can make the scan slow or memory-hungry (the duplication count keeps the tokens of every file of the studio's own under 1 MB in memory: about 2 GB for 3 million lines) (huge files, decompression bombs in `.dacpac` or `.ispac` files; JSON and text coverage reports are read whole, up to 256 MB each). XML is parsed with Python's `expat`, whose versions from 2.4.1 on limit entity expansion.
- **A few files are opened by name and do follow links**, such as `ProjectSettings/ProjectVersion.txt`, a `.uproject`, `Build.version`, `project.godot`, `.gitmodules`, `CVS/Root`, `srcsafe.ini`, a Unity `.meta` file and the licence file at the top. Only a version, guid or similar short field is taken from them (and the licence's kind). A link from one of them to a device could stall the scan.
- **Leftover temporary files.** If a run is killed, a copy of an Access database stays in your temporary folder until a later run removes it a day later. Delete `size_codebase_*` folders there by hand if you need them gone sooner.

## Verifying your copy

Each release is tagged `v<version>` in the public repository, <https://github.com/patinasource/size-codebase>, which also has a `SHA256SUMS` file with the SHA-256 of `size_codebase.py`. The version is in the file (`__version__`), on the first line of every report (for example `size_codebase.py 1.2.0`), in the JSON (`script_version`), and on the first line of `--help`.

Compute the checksum of your copy and compare it with `SHA256SUMS` at that release's tag:

- macOS: `shasum -a 256 size_codebase.py`
- Linux: `sha256sum size_codebase.py`
- Windows (PowerShell): `Get-FileHash size_codebase.py -Algorithm SHA256` (it prints the hash in capitals; compare without regard to case)

## Reporting a security problem

Email hello@patinasource.com. Please include the script's version and how to reproduce the problem.
