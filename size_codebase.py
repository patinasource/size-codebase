#!/usr/bin/env python3
"""
size_codebase.py — size up a codebase. Understands Unity, Unreal (every version from
Unreal Engine 1 to 5: C++, Blueprints, UnrealScript, Kismet, AngelScript, Verse ...),
Ren'Py, Python and JavaScript/TypeScript projects out of the box, and counts most other
languages too, and systems built with Microsoft Access and SQL Server (forms, reports, queries, VBA,
stored procedures, SSIS and SSRS). Counts commits, contributors and pull requests from Git, Perforce,
SVN, Mercurial, Plastic SCM (Unity Version Control), Team Foundation (TFVC), Bazaar, Fossil, Darcs, CVS
and Visual SourceSafe, counting each change once when a project moved from one system to another
(even several times) and two or more of them hold it; without version control, counts the people
named as authors in the code.

Usage (Windows, macOS or Linux):
    python3 size_codebase.py "/path/to/project"  ["/path/to/other" ...]
    python3 size_codebase.py            (asks for the folder; drag it into the window)
    python3 size_codebase.py "/path/to/Program.mdb"     (a single file, e.g. an Access database)
On Windows, "py" instead of "python3" also works, and so does double-clicking the script.

If it gets a folder wrong, say so (paths relative to the project folder, or absolute; repeatable):
    python3 size_codebase.py "/path/to/project" --third-party Source/Game/SomeLib --own Plugins/MyPlugin

Code in a language it doesn't know (one of the studio's own, say) is listed as text files of unknown
kinds. Name each extension; it's then counted as code (every non-blank line), and scc and jscpd
(below) read it as text, or as a known language whose comments it shares (C, C++, Ada, SQL, Lisp,
Python, Pascal, Lua or Visual Basic); repeatable:
    python3 size_codebase.py "/path/to/project" --code-ext .par=PARLANSE --code-ext ".atg=DMS grammar:Ada"

Visual SourceSafe: its history is read straight from the SourceSafe database (the folder with
srcsafe.ini and a data folder), found inside the project, through the SSDIR setting, or where the
project files say it is, if that's on this computer (a database the project files place on a
network share isn't opened by itself: name it with --sourcesafe). If it's somewhere else, name it;
its history is then put together with the others, without counting work that is in both twice:
    py size_codebase.py "C:\\path\\to\\project" --sourcesafe "D:\\OldVSS"
SourceSafe has no server program: its database is just a folder of files, so a copy of it (from a
backup or an old disk) works as well as the original, as does its data folder on its own.

Microsoft Access and SQL Server: Access databases (.accdb, .mdb ...) are read in full on Windows
with Microsoft Access installed (on a copy, with their macros and code switched off; if Access
can't switch them off, the database isn't opened), and without their VBA through mdbtools
elsewhere. Code that lives only inside a SQL Server database is read from the running server,
through sqlcmd, with your Windows sign-in (or set SQLCMDUSER and SQLCMDPASSWORD). sqlcmd checks the
server's certificate; for a server you trust that has its own (self-signed) certificate, add
--trust-server-certificate:
    py size_codebase.py "C:\\path\\to\\project" --sql-server MYSERVER\\SQLEXPRESS [--sql-database Sales]

It doesn't change the project or its history, only reads them (version-control tools may update
their own caches, such as Mercurial's and Darcs's). It prints a summary and saves it
next to this script (or, if it can't write there, in the current or home folder) as
size_report_<folder>.txt, with the same numbers for computers in size_report_<folder>.json. They
hold counts, and names of folders, branches, languages, libraries and packages (and the
repository's web address, if anyone can read it): no source code and no author names. They name
files only where you do (a file given on its own, or marked with --third-party), and error
messages in them have their paths replaced by <project>, ~ or <path>. From databases it reads
only code (stored procedures, queries, VBA ...) and the list of objects: never the rows in a
table, so no customer data. Nothing about the project is uploaded anywhere: servers are only
asked the questions below.

The report ends with the standard measures buyers' codebase forms ask for: logical lines of code
and generated lines (scc), duplication (jscpd), commits on the main branch without merges or
reverts, and the primary language. scc and jscpd are downloaded for this, once, from their
official releases (github.com, registry.npmjs.org), over HTTPS with the certificate checked, and
checked against fixed checksums, as is the program each time before it runs; nothing needs
installing, and they're kept in a cache folder (on Windows %LOCALAPPDATA%\\size_codebase_tools).
No other copy of them is ever run. If one can't be downloaded, its figures are left out of the
report, which says why. To also save scc's report and a summary of jscpd's beside this one, for
attaching to a form:
    python3 size_codebase.py "/path/to/project" --reports
(Both hold counts only. jscpd's full report, which holds copies of the duplicated code, is never
saved: only its totals are, as forms ask.)

Test coverage is read from the reports the project's tests already wrote (lcov.info, coverage.xml,
jacoco.xml, coverage-final.json, a Go cover profile, an OpenCover or ReportGenerator summary from
Unity's Code Coverage package ...), wherever they are in the project, build output included. The
tests themselves are never run. To include coverage, run them with it turned on first.

Connecting to other computers. Besides downloading scc and jscpd, it asks servers only for what the
history needs, read-only, with the access you already have (it never stops to ask for a password):
  - Git: each remote, for the pull requests it keeps (git ls-remote); GitHub, through its gh
    command if that's installed and signed in, for the merged pull requests; and GitHub, GitLab or
    Bitbucket, without signing in, whether anyone can read the repository.
  - Perforce, Plastic SCM and TFVC, and SVN, CVS or Bazaar where the history is on a server: their
    own commands ask the server for the history.
  - --sql-server: that SQL Server. --sourcesafe or SSDIR: the folder named, even on a network share.
  - --network-sourcesafe: SourceSafe databases on network shares that the project files name.
Options:
  --offline        Connect to no other computer at all: no downloads (a copy of scc or jscpd
                   downloaded before still runs, after its checksum is checked), no version-control
                   servers, no network shares besides the folder you name, and no Access database
                   opened in Microsoft Access. The report says what that left out. Can't be used
                   with --sql-server.
  --no-download    Don't download scc or jscpd (copies downloaded before are still used).
  --reports        Save scc's report and jscpd's totals beside this one (see above).
  --trust-server-certificate
                   With --sql-server: trust the server's certificate without checking it (sqlcmd -C).
  --network-sourcesafe
                   Also open SourceSafe databases on network shares (\\\\server\\share) that the project
                   files name, and a data folder on a network share that a database's srcsafe.ini
                   names. Without it they're named on screen but not opened, since the project's
                   files could name any computer. Can't be used with --offline.
  --third-party, --own, --code-ext, --sourcesafe, --sql-server, --sql-database: see above.
  -h, --help       Show this help.

Needs Python 3.8+ and nothing else (https://www.python.org/downloads/).
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from collections import Counter, defaultdict, namedtuple
from datetime import datetime, timezone
from stat import S_ISREG

__version__ = "1.4.0"


# #######################################
# General utilities
# #######################################

# ##############################
# Formatting
# ##############################

def fmt(value):
    return f"{value:,}" if isinstance(value, int) else str(value)


def plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def counted(n, label):
    """"1 stored procedure", "2 queries": label is the plural."""
    if n != 1:
        return f"{n:,} {label}"
    words = label.split(" ")
    word = words[-1] if words[-1] != "(e.g." else words[0]
    single = word[:-3] + "y" if word.endswith("ies") else word[:-1] if word.endswith("s") else word
    return f"1 {label.replace(word, single, 1)}"


# ##############################
# Text
# ##############################

def as_text(data):
    """A file's bytes, with UTF-16 files (common for Windows C++, C# and UnrealScript) turned into
    UTF-8: read as bytes, their blank lines aren't blank."""
    bom = data[:2] in (b"\xff\xfe", b"\xfe\xff")
    if bom or (len(data) >= 64 and data[1:64:2].count(0) > 24):
        try:
            return data.decode("utf-16" if bom else "utf-16-le").encode("utf-8", "replace")
        except UnicodeDecodeError:
            pass
    return data


def text_lines(data):
    """The non-blank lines of a file's bytes."""
    return [line for line in as_text(data).splitlines() if line.strip()]


def count_text_lines(text):
    return sum(1 for line in text.splitlines() if line.strip())


# ####################
# Error messages, for the saved report
# ####################
# An error's message can name files and folders ("Permission denied: '/Users/ann/Game/secret.c'"),
# which the saved report and its .json never do: the scanned folder becomes <project>, the home
# folder ~, and then whatever still looks like a path or a file name <path>.
QUOTED_PATH = re.compile(r"""(['"])(?:(?:(?!\1).)*?(?:[\\/]|<project>|~)(?:(?!\1).)*|[^'"\s]+\.[A-Za-z0-9]{1,8})\1""")
UNQUOTED_PATH = re.compile(r"""(?<![\w.:/\\])(?:<project>|~|[A-Za-z]:)?(?:[\\/]+[^\s\\/'"<>|]+)+[\\/]*""")


def scrub(text, root=None):
    """text (an error's message) without paths or file names in it."""
    text = str(text)
    for folder, label in ((root, "<project>"), (os.path.expanduser("~"), "~")):
        if not folder:
            continue
        forms = set()
        for form in (folder, os.path.abspath(folder), os.path.realpath(folder)):
            form = short_path(form).rstrip("\\/")
            forms |= {form, form.replace("\\", "/"), form.replace("/", "\\"), long_path(form)}
        for form in sorted((f for f in forms if len(f) > 1), key=len, reverse=True):
            text = re.sub(re.escape(form) + r"(?![\w.-])", label, text, flags=re.I if os.name == "nt" else 0)
    text = QUOTED_PATH.sub("<path>", text)
    return UNQUOTED_PATH.sub("<path>", text)


def describe(error, root=None):
    """An exception, for the saved report: its kind and its message, scrubbed."""
    return f"{type(error).__name__}: {scrub(error, root)}"


# ##############################
# Files and paths
# ##############################

def read_json(path):
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def find_path(dirpath, *parts):
    """dirpath/parts..., matching names case-insensitively, or None if it doesn't exist. Linux (and
    some Mac drives) tell "Classes" from "classes"; Windows, where most projects are made, doesn't."""
    path = dirpath
    for part in parts:
        candidate = os.path.join(path, part)
        if not os.path.exists(candidate):
            try:
                candidate = next(os.path.join(path, n) for n in os.listdir(path) if n.lower() == part.lower())
            except (OSError, StopIteration):
                return None
        path = candidate
    return path


def list_files(path):
    try:
        return os.listdir(path) if path else []
    except OSError:
        return []


def is_network_path(path):
    """A folder on another computer: \\\\server\\share (or //server/share) or, on Windows, a drive
    letter mapped to a network share. Reading it means connecting to that computer."""
    path = (path or "").strip().strip('"')
    if path.startswith(("\\\\?\\", "\\\\.\\")):   # Windows' long and device paths: \\?\C:\... or \\?\UNC\server\...
        rest = path[4:]
        return rest.upper().startswith("UNC\\") or is_network_path(rest)
    if path.startswith(("\\\\", "//")):
        return True
    if os.name == "nt" and re.match(r"^[A-Za-z]:", path):
        import ctypes
        drive_remote = 4   # DRIVE_REMOTE
        try:
            return ctypes.windll.kernel32.GetDriveTypeW(path[:2] + "\\") == drive_remote
        except (AttributeError, OSError):
            return False
    return False


def file_sha256(path):
    """A file's SHA-256 checksum, or None if it can't be read."""
    import hashlib
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def is_link(path):
    """A symbolic link or (Windows) junction. Not followed: they can loop, or lead to code counted twice."""
    if os.path.islink(path):
        return True
    if hasattr(os.path, "isjunction"):   # Python 3.12+
        return os.path.isjunction(path)
    try:
        return bool(os.lstat(path).st_file_attributes & 0x400)   # FILE_ATTRIBUTE_REPARSE_POINT (Windows)
    except (OSError, AttributeError):
        return False


def long_path(path):
    """On Windows, lets us read files whose full path is longer than 260 characters."""
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return path
    if path.startswith("\\\\"):   # network share, \\server\share
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path


def short_path(path):
    """Undoes long_path()."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    return path[4:] if path.startswith("\\\\?\\") else path


def is_within(path, folder):
    try:
        path, folder = (os.path.normcase(os.path.abspath(short_path(p))) for p in (path, folder))
        return os.path.commonpath([path, folder]) == folder
    except ValueError:   # different drives
        return False


def find_up(path, name, levels=6):
    """Does `name` exist in this folder or one of the folders above it?"""
    return nearest(path, name, levels) is not None


def nearest(path, name, levels=6):
    """path/name, or the same in the nearest folder above that has it; None if none does."""
    for _ in range(levels):
        if os.path.exists(os.path.join(path, name)):
            return os.path.join(path, name)
        path = os.path.dirname(path)
    return None


def is_lfs_pointer(path):
    """A Git LFS placeholder: the real file is on the server, not downloaded."""
    try:
        with open(path, "rb") as f:
            return f.read(40).startswith(b"version https://git-lfs")
    except OSError:
        return False


# ##############################
# Temporary folders
# ##############################
# The temporary folders this script makes, by what they're for: jscpd's report (it holds copies of
# the duplicated code) and copies of Access databases, with the PowerShell script that reads them.
# Each is deleted as soon as it's done with; one left behind by a run that was stopped (Ctrl-C) is
# deleted by a later run, once it's a day old (younger ones may belong to a run still going).
TEMP_PREFIXES = {"jscpd": "size_codebase_jscpd_", "access": "size_codebase_access_"}
TEMP_MAX_AGE = 86400   # seconds


def temp_folder(kind):
    import tempfile
    return tempfile.mkdtemp(prefix=TEMP_PREFIXES[kind])


def remove_old_temp_folders():
    """Deletes this script's temporary folders left behind by earlier runs. Returns how many."""
    import tempfile
    import time
    base, removed = tempfile.gettempdir(), 0
    for name in list_files(base):
        path = os.path.join(base, name)
        if not name.startswith(tuple(TEMP_PREFIXES.values())) or is_link(path) or not os.path.isdir(path):
            continue
        try:
            if time.time() - os.lstat(path).st_mtime < TEMP_MAX_AGE:
                continue
        except OSError:
            continue
        shutil.rmtree(path, ignore_errors=True)
        removed += not os.path.exists(path)
    return removed


# ##############################
# Running command-line tools
# ##############################

# ####################
# Finding them
# ####################
# Where version-control tools are often installed on Windows without being on PATH.
WINDOWS_TOOL_PATHS = {
    "git": [r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe", r"%LOCALAPPDATA%\Atlassian\SourceTree\git_local\cmd\git.exe",
            r"%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe"],
    "svn": [r"C:\Program Files\TortoiseSVN\bin\svn.exe", r"C:\Program Files\SlikSvn\bin\svn.exe",
            r"C:\Program Files (x86)\Subversion\bin\svn.exe"],
    "hg": [r"C:\Program Files\TortoiseHg\hg.exe", r"C:\Program Files\Mercurial\hg.exe"],
    "p4": [r"C:\Program Files\Perforce\p4.exe", r"C:\Program Files (x86)\Perforce\p4.exe"],
    "cm": [r"C:\Program Files\PlasticSCM5\client\cm.exe", r"C:\Program Files\Unity\Version Control\client\cm.exe",
           r"C:\Program Files\Unity Version Control\client\cm.exe", r"C:\Program Files\Unity VCS\client\cm.exe"],
    "tf": [r"C:\Program Files\Microsoft Visual Studio\*\*\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation"
           r"\Team Explorer\TF.exe",
           r"C:\Program Files (x86)\Microsoft Visual Studio\*\*\Common7\IDE\CommonExtensions\Microsoft"
           r"\TeamFoundation\Team Explorer\TF.exe",
           r"C:\Program Files (x86)\Microsoft Visual Studio *\Common7\IDE\TF.exe"],
    "brz": [r"C:\Program Files\Breezy\brz.exe"],
    "bzr": [r"C:\Program Files (x86)\Bazaar\bzr.exe", r"C:\Program Files\Bazaar\bzr.exe"],
    "fossil": [r"C:\Program Files\Fossil\fossil.exe"],
    "cvs": [r"C:\Program Files (x86)\CVSNT\cvs.exe", r"C:\Program Files\CVSNT\cvs.exe",
            r"C:\Program Files\TortoiseCVS\cvs.exe"],
}


# The same on macOS and Linux, where an app's installer may not have linked its tool onto PATH.
POSIX_TOOL_PATHS = {
    "cm": ["/Applications/PlasticSCM.app/Contents/MacOS/cm", "/Applications/PlasticSCM.app/Contents/Applications/cm.app"
           "/Contents/MacOS/cm", "/opt/plasticscm5/client/cm"],
}


def tool_path(name):
    """Where a command-line tool is installed. On Windows, tools that came with GitHub Desktop,
    TortoiseSVN, P4V, Visual Studio and the like often aren't on PATH."""
    if os.name != "nt":
        return shutil.which(name) or next((p for p in POSIX_TOOL_PATHS.get(name, []) if os.access(p, os.X_OK)), None)
    found = windows_program(name, os.environ.get("PATH", ""))
    if found:
        return found
    import glob
    for pattern in WINDOWS_TOOL_PATHS.get(name, []):
        matches = sorted(glob.glob(os.path.expandvars(pattern)), reverse=True)   # newest version first
        if matches:
            return matches[0]
    return None


def windows_program(name, path):
    """name.exe (or .com) in one of the folders on path (Windows' PATH), or None. Not shutil.which,
    which on Windows looks in the current folder first (so a project's own git.exe would run if this
    were started from inside it), and also finds .bat and .cmd files, which Windows runs through
    cmd.exe, which can read their arguments as more commands."""
    if os.path.dirname(name):   # a full path already (scc's and jscpd's, say)
        return name if os.path.isfile(name) else None
    for folder in path.split(os.pathsep):
        folder = folder.strip().strip('"')
        if not folder or not os.path.isabs(folder):   # "" and "." mean the current folder
            continue
        for ext in (".exe", ".com"):
            candidate = os.path.join(folder, name + ext)
            if os.path.isfile(candidate):
                return candidate
    return None


def command(args, logins=False):
    """args with the tool's full path, and for git the settings below. logins: let git use the
    user's own credential helpers and password prompts (only for asking a server, from outside the
    repository: see ls_remote)."""
    exe = tool_path(args[0])
    if exe is None:
        return None
    if args[0] != "git":
        return [exe, *args[1:]]
    exceptions = [o for repo in _git_other_owners for o in ("-c", f"safe.directory={repo}")]
    return [exe, *GIT_SAFE_OPTIONS, *([] if logins else GIT_NO_LOGINS), *exceptions, *args[1:]]


# ####################
# Git, safely
# ####################
# Settings in a repository's own configuration that would make git run a program, overridden on
# every git command, as a repository copied from elsewhere could hold any of them: hooks, an
# fsmonitor program, an external diff program (diff commands also get GIT_NO_PROGRAMS, for diff
# drivers and textconv), a signature checker (log.showSignature runs gpg.program), credential
# helpers and password prompts (GIT_NO_LOGINS), and the ext:: transport, which runs any command.
# core.sshCommand is outranked by GIT_SSH_COMMAND, set in quiet_env; core.gitProxy, the remote's
# uploadpack and the like only apply where git contacts a server, which happens outside the
# repository (ls_remote). Lazy fetches of a partial clone, and every other connection outside
# ls_remote, are turned off in quiet_env.
GIT_SAFE_OPTIONS = ["-c", "core.fsmonitor=", "-c", "core.hooksPath=" + os.devnull, "-c", "diff.external=",
                    "-c", "log.showSignature=false", "-c", "protocol.ext.allow=never",
                    "-c", "uploadpack.packObjectsHook="]
GIT_NO_LOGINS = ["-c", "credential.helper=", "-c", "core.askPass="]
GIT_NO_PROGRAMS = ["--no-ext-diff", "--no-textconv"]
# Git refuses a repository that belongs to another user account (on an external drive, or copied
# from another computer): its settings could run programs as whoever reads it. With the settings
# above overridden, it's read anyway, naming just that repository as safe (never "safe.directory=*").
DUBIOUS_OWNERSHIP = re.compile(r"dubious ownership in repository at '([^'\r\n]+)'"
                               r"|unsafe repository \('([^'\r\n]+)' is owned by someone else\)")
_git_other_owners = []   # those repositories, as git names them (see run); emptied for each project


def other_owners_repository(stderr):
    """The repository git refused for belonging to another user account, as git names it (always
    with forward slashes, as safe.directory needs them on Windows too), or None."""
    m = DUBIOUS_OWNERSHIP.search(stderr or "")
    return (m.group(1) or m.group(2)).replace("\\", "/") if m else None


# ####################
# Connecting to other computers
# ####################
OFFLINE = False            # --offline: connect to no other computer at all
NETWORK_SOURCESAFE = False  # --network-sourcesafe: open SourceSafe databases the project files name on a network share
_left_out_offline = []     # what --offline left out of the project's report; emptied for each project


def left_out_offline(what):
    if what not in _left_out_offline:
        _left_out_offline.append(what)


# ####################
# Showing progress
# ####################
_last_progress = [0.0]


def progress(message=None):
    """Shows what a long scan is doing, on one line that keeps being overwritten. Only when a person
    is watching, and at most twice a second. progress() clears the line."""
    if not sys.stderr.isatty():
        return
    import time
    now = time.monotonic()
    if message is not None and now - _last_progress[0] < 0.5:
        return
    _last_progress[0] = now
    sys.stderr.write("\r" + (message or "")[:78].ljust(78) + ("" if message else "\r"))
    sys.stderr.flush()


# ####################
# Running them
# ####################

def quiet_env():
    """Never stop to ask for a password: if a server needs one we don't already have, skip it. And
    plain, UTF-8 output whatever the user's settings. Mercurial ignores a repository's own settings,
    whose hooks and extensions could run programs (HGRCSKIPREPO; 5.4 and later, see hg_history). Git
    never fetches what a partial clone left on the server (GIT_NO_LAZY_FETCH), and may use no
    transport at all (GIT_ALLOW_PROTOCOL empty), so it can't connect anywhere, even before Git 2.44,
    which ignores GIT_NO_LAZY_FETCH (a lazy fetch follows the repository's own settings for its
    remote). Only ls_remote, which asks servers, allows some transports, and not with --offline."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_NO_LAZY_FETCH="1", HGPLAIN="1",
               HGENCODING="utf-8", HGRCSKIPREPO="1", PYTHONIOENCODING="utf-8", GIT_ALLOW_PROTOCOL="")
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    return env


def run(args, cwd, timeout=900, env=None, logins=False):
    """stdout of a command, or None if it isn't installed, fails or takes too long. env: more
    environment variables; logins: see command(). A git command refused because the repository
    belongs to another user account is run again, naming that repository as safe (see
    DUBIOUS_OWNERSHIP)."""
    full = command(args, logins)
    if full is None:
        return None
    env = dict(quiet_env(), **(env or {}))
    env["PWD"] = os.path.abspath(cwd)   # p4 finds its settings (P4CONFIG) from $PWD, not the real folder
    try:
        out = subprocess.run(full, cwd=cwd, capture_output=True, timeout=timeout, env=env, stdin=subprocess.DEVNULL)
        repo = other_owners_repository(out.stderr.decode("utf-8", "replace")) if args[0] == "git" else None
        if out.returncode != 0 and repo and repo not in _git_other_owners:
            _git_other_owners.append(repo)
            out = subprocess.run(command(args, logins), cwd=cwd, capture_output=True, timeout=timeout, env=env,
                                 stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


# #######################################
# Recognising projects
# #######################################

# ##############################
# Kinds of project
# ##############################
UNREAL_KINDS = {"Unreal", "Unreal Engine source", "Unreal Engine 3", "Unreal Engine 1/2", "UnrealScript"}
PYTHON_MARKERS = {"pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "pipfile"}
UNITY_BUILD_FILES = {"unityplayer.dll", "unityplayer.so", "unityplayer.dylib", "globalgamemanagers",
                     "gameassembly.dll", "gameassembly.so", "gameassembly.dylib", "assembly-csharp.dll"}


def detect_kinds(dirpath, filenames, dirnames):
    """Which kinds of project have their root in this folder?"""
    kinds = {}
    names = {f.lower() for f in filenames}
    subdirs = {d.lower() for d in dirnames}

    # ####################
    # Unity
    # ####################
    pv = find_path(dirpath, "ProjectSettings", "ProjectVersion.txt")
    if pv or {"assets", "projectsettings"} <= subdirs:
        version = "(version unknown)"
        if pv:
            with open(pv, errors="replace") as f:
                for line in f:
                    if line.startswith("m_EditorVersion:"):
                        version = line.split(":", 1)[1].strip()
        kinds["Unity"] = version

    # ####################
    # Unreal, every version
    # ####################
    association = engine_association(dirpath, filenames)
    if any(f.lower().endswith(".uefnproject") for f in filenames):
        kinds["Unreal"] = "(UEFN, Unreal Editor for Fortnite)"
    elif association is not None:
        kinds["Unreal"] = association if re.match(r"^\d+\.\d+", association) else CUSTOM_ENGINE
    build_version = find_path(dirpath, "Build", "Build.version")
    if build_version:   # this folder is Engine/ in a source build of Unreal 4 or 5
        v = read_json(build_version)
        kinds["Unreal Engine source"] = "{}.{}.{}".format(v.get("MajorVersion", "?"), v.get("MinorVersion", "?"),
                                                          v.get("PatchVersion", "?"))
    if "development" in subdirs and find_path(dirpath, "Development", "Src"):
        kinds["Unreal Engine 3"] = ""
    elif "system" in subdirs and subdirs & {"maps", "textures", "sounds", "music"}:
        if any(f.lower().endswith((".u", ".int")) for f in list_files(find_path(dirpath, "System"))):
            kinds["Unreal Engine 1/2"] = ""
    if "classes" in subdirs:
        if any(f.lower().endswith(".uc") for f in list_files(find_path(dirpath, "Classes"))):
            kinds["UnrealScript"] = "package"

    # ####################
    # JavaScript, Ren'Py and Python
    # ####################
    if "package.json" in names:
        kinds["JavaScript"] = "+ TypeScript" if "tsconfig.json" in names else ""
    if "game" in subdirs:
        if any(f.lower().endswith((".rpy", ".rpyc", ".rpa")) for f in list_files(find_path(dirpath, "game"))):
            kinds["Ren'Py"] = ""
    if names & PYTHON_MARKERS:
        kinds["Python"] = ""

    # ####################
    # Everything else
    # ####################
    kinds.update(engine_and_build_kinds(dirpath, filenames, names, subdirs, kinds))
    return kinds


def engine_and_build_kinds(dirpath, filenames, names, subdirs, kinds):
    """Other engines and frameworks, and C/C++, .NET, Java, Rust and Go build systems."""
    found = {}
    ends = lambda *exts: [f for f in filenames if f.lower().endswith(exts)]

    # ####################
    # Engines and frameworks
    # ####################
    if "project.godot" in names:
        version = ""
        try:
            with open(os.path.join(dirpath, "project.godot"), encoding="utf-8", errors="replace") as f:
                text = f.read(20000)
            features = re.search(r'config/features\s*=\s*PackedStringArray\(\s*"(\d+\.\d+)', text)
            config = re.search(r"config_version\s*=\s*(\d+)", text)   # 5: Godot 4, 4: Godot 3
            version = features.group(1) if features else {"5": "4.x", "4": "3.x"}.get(config.group(1), "") if config else ""
        except OSError:
            pass
        found["Godot"] = version
    if ends(".yyp", ".project.gmx"):
        found["GameMaker"] = "Studio 2" if ends(".yyp") else "Studio 1"
    if "game.project" in names:
        found["Defold"] = ""
    if ends(".c3proj", ".capx", ".c3p", ".caproj"):
        found["Construct"] = "(its event sheets are logic this script doesn't count)"
    if ends(".rmmzproject", ".rpgproject") or (subdirs >= {"js", "data"} and any(
            f in list_files(os.path.join(dirpath, "js")) for f in ("rpg_core.js", "rmmz_core.js"))):
        found["RPG Maker"] = "MZ" if ends(".rmmzproject") else "MV"
    if {"main.lua", "conf.lua"} <= names:
        found["LOVE (Love2D)"] = ""
    if "gameinfo.txt" in names or ({"game", "public", "tier1"} <= subdirs):
        found["Source engine (Valve)"] = ""
    if ends(".cryproject"):
        found["CRYENGINE"] = ""
    if ends(".sdpkg", ".sdsln"):
        found["Stride"] = ""
    if ends(".flaxproj"):
        found["Flax"] = ""
    if ends(".mgcb"):
        found["MonoGame"] = ""
    if ends(".contentproj"):
        found["XNA"] = ""
    if ends(".hxml") or ("project.xml" in names and "Unity" not in kinds and _mentions(dirpath, "project.xml", b"haxelib")):
        found["Haxe (OpenFL / HaxeFlixel / Kha)"] = ""
    if names & {"plugins.cfg", "resources.cfg", "ogre.cfg"}:
        found["Ogre3D"] = ""

    # ####################
    # Build systems
    # ####################
    if ends(".sln"):
        n = sum(_count(os.path.join(dirpath, f), b"\nProject(") for f in ends(".sln"))
        found["Visual Studio solution"] = plural(n, "project")
    if ends(".vcxproj", ".vcproj"):
        found["C/C++ (Visual Studio)"] = ""
    if ends(".csproj", ".fsproj", ".vbproj") and "Unity" not in kinds:
        found[".NET"] = ""
    if "cmakelists.txt" in names:
        found["C/C++ (CMake)"] = ""
    if any(re.match(r"premake\d?\.lua$", n) for n in names):
        found["C/C++ (premake)"] = ""
    if names & {"meson.build"}:
        found["Meson"] = ""
    if names & {"sconstruct"}:
        found["SCons"] = ""
    if any(d.endswith(".xcodeproj") for d in subdirs):
        found["Xcode project"] = ""
    if names & {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}:
        found["Java/Kotlin (Gradle)"] = ""
    if "pom.xml" in names:
        found["Java (Maven)"] = ""
    if "cargo.toml" in names:
        found["Rust"] = ""
    if "go.mod" in names:
        found["Go"] = ""
    if ends(".vbp", ".vbg"):
        found["Visual Basic 6"] = ""

    # ####################
    # Databases and their tools
    # ####################
    access = ends(*ACCESS_EXTS)
    if access:
        found["Microsoft Access"] = plural(len(access), "database")
    if os.path.basename(dirpath).lower().endswith((".accdb.src", ".accda.src", ".mdb.src", ".adp.src")):
        found["Microsoft Access (exported as text)"] = ""
    if ends(".sqlproj"):
        found["SQL Server database project (SSDT)"] = ""
    if ends(".dtproj"):
        found["SQL Server Integration Services (SSIS)"] = ""
    if ends(".rptproj"):
        found["SQL Server Reporting Services (SSRS)"] = ""
    return found


def _mentions(dirpath, name, needle):
    try:
        with open(os.path.join(dirpath, name), "rb") as f:
            return needle in f.read(100_000)
    except OSError:
        return False


def _count(path, needle):
    try:
        with open(path, "rb") as f:
            return f.read(5_000_000).count(needle)
    except OSError:
        return 0


# ##############################
# Custom-built Unreal engines
# ##############################
CUSTOM_ENGINE = "(custom-built engine)"


def engine_association(dirpath, filenames):
    """The engine a .uproject in this folder is built with: a version like "4.27" for Epic's builds,
    an id or "" for a custom-built engine. None if there's no .uproject."""
    uproject = next((f for f in filenames if f.lower().endswith(".uproject")), None)
    if uproject is None:
        return None
    return str(read_json(os.path.join(dirpath, uproject)).get("EngineAssociation", ""))


def registered_unreal_engines():
    """{engine id: folder} for the custom-built engines registered on this computer. Unreal keeps
    them in the registry on Windows and in Install.ini on macOS and Linux."""
    engines = {}
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Epic Games\Unreal Engine\Builds") as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _ = winreg.EnumValue(key, i)
                    engines[name.strip("{}").lower()] = str(value)
        except OSError:
            pass
        return engines
    import configparser
    for ini in ("~/.config/Epic/UnrealEngine/Install.ini",                          # Linux
                "~/Library/Application Support/Epic/UnrealEngine/Install.ini"):    # macOS
        parser = configparser.RawConfigParser(strict=False)
        try:
            parser.read(os.path.expanduser(ini), encoding="utf-8")
        except (configparser.Error, OSError, UnicodeDecodeError):
            continue
        if parser.has_section("Installations"):
            for name, value in parser.items("Installations"):
                engines[name.strip("{}").lower()] = value
    return engines


def find_custom_engine(project_dir, association):
    """The folder of the custom-built engine a project uses (the one holding Engine/), or None. An
    empty association means the project lives inside the engine's own folder tree."""
    if association:
        candidates = [registered_unreal_engines().get(association.strip("{}").lower())]
    else:
        candidates, d = [], project_dir
        for _ in range(5):
            d = os.path.dirname(d)
            candidates.append(d)
    for candidate in candidates:
        if candidate and association and OFFLINE and is_network_path(candidate):
            left_out_offline("the custom Unreal Engine this project is built with, registered on a network share")
            continue
        if candidate and find_path(candidate, "Engine", "Build", "Build.version"):
            return os.path.abspath(short_path(candidate))
        if candidate and os.path.basename(candidate.rstrip("/\\")).lower() == "engine" and \
                find_path(candidate, "Build", "Build.version"):
            return os.path.dirname(os.path.abspath(short_path(candidate)))
    return None


# #######################################
# Sorting files and folders
# #######################################

# ##############################
# Folders to skip
# ##############################
# Caches, dependencies and tool folders: skipped wherever they appear.
ALWAYS_SKIP = {
    ".git", ".svn", ".hg", ".bzr", ".plastic", "_darcs", ".jj", ".sl", ".pijul", "_mtn", "{arch}", ".arch-ids", ".lore",
    ".diversion", ".jazz5", ".sbas", ".sgdrawer", "$tf", ".$tf", "_sgvault", "sccs", ".vs", ".idea", ".vscode",
    "node_modules", "bower_components", "jspm_packages", ".yarn", ".pnpm-store",
    ".next", ".nuxt", ".output", ".svelte-kit", ".turbo", ".parcel-cache", ".vercel", ".cache",
    "__pycache__", ".venv", "venv", ".tox", ".nox", ".eggs", "site-packages",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".ipynb_checkpoints", ".gradle",
    "__macosx", ".spotlight-v100", ".trashes", ".fseventsd", ".temporaryitems", "$recycle.bin",
    "system volume information", "lost+found",
    ".history", ".sass-cache", "pods", "carthage", ".swiftpm", ".build", ".dart_tool", ".pub-cache",
}
# Build output: skipped only directly inside a project of that kind, so that a
# folder like Assets/Scripts/Library is still counted.
ROOT_SKIP = {
    "Unity": {"library", "temp", "obj", "logs", "usersettings", "build", "builds", "memorycaptures"},
    "Unreal": {"intermediate", "saved", "deriveddatacache", "binaries", "build",
               # packaged builds of the game, if made into the project folder
               "windows", "windowsnoeditor", "windowsclient", "windowsserver", "linux", "linuxnoeditor",
               "linuxserver", "mac", "macnoeditor", "android", "ios", "stagedbuilds", "archivedbuilds"},
    "Unreal Engine source": {"intermediate", "saved", "deriveddatacache", "binaries"},
    "Unreal Engine 3": {"intermediate", "binaries"},
    "JavaScript": {"dist", "build", "out", "coverage", "storybook-static"},
    "Python": {"build", "dist", "htmlcov"},
    ".NET": {"bin", "obj"},
    "SQL Server database project (SSDT)": {"bin", "obj"},
    "SQL Server Integration Services (SSIS)": {"bin", "obj"},
    "SQL Server Reporting Services (SSRS)": {"bin", "obj"},
    "C/C++ (Visual Studio)": {"debug", "release", "x64", "win32", "x86", "arm64", "ipch"},
    "Java/Kotlin (Gradle)": {"build", ".gradle", ".cxx"},
    "Java (Maven)": {"target"},
    "Rust": {"target"},
    "Godot": {".godot", ".import"},
    "GameMaker": {"options", "tmp"},
}
UNREAL_PLUGIN_SKIP = {"intermediate", "binaries"}


# ##############################
# Kinds of file
# ##############################

# ####################
# Code
# ####################
CODE_EXTS = {
    ".cs": "C#", ".boo": "Boo",
    ".py": "Python", ".pyi": "Python", ".pyx": "Cython",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".vue": "Vue", ".svelte": "Svelte",
    ".html": "HTML", ".htm": "HTML", ".css": "CSS", ".scss": "CSS", ".sass": "CSS", ".less": "CSS",
    ".c": "C/C++", ".cc": "C/C++", ".cpp": "C/C++", ".cxx": "C/C++",
    ".h": "C/C++", ".hh": "C/C++", ".hpp": "C/C++", ".inl": "C/C++",
    ".m": "Objective-C", ".mm": "Objective-C",
    ".shader": "Shaders", ".cginc": "Shaders", ".hlsl": "Shaders",
    ".glsl": "Shaders", ".compute": "Shaders", ".usf": "Shaders", ".ush": "Shaders",
    ".uc": "UnrealScript", ".uci": "UnrealScript", ".verse": "Verse", ".sk": "SkookumScript",
    ".lua": "Lua", ".java": "Java", ".kt": "Kotlin", ".swift": "Swift",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".gd": "GDScript",
    ".rpy": "Ren'Py", ".rpym": "Ren'Py",
    ".as": "ActionScript", ".pas": "Pascal", ".asm": "Assembly", ".sql": "SQL",
    ".sh": "Shell", ".bash": "Shell", ".ps1": "PowerShell",
    ".c++": "C/C++", ".cppm": "C/C++", ".ixx": "C/C++", ".ipp": "C/C++", ".tcc": "C/C++", ".hxx": "C/C++",
    ".h++": "C/C++", ".cu": "CUDA", ".cuh": "CUDA",
    ".fx": "Shaders", ".fxh": "Shaders", ".cg": "Shaders", ".vert": "Shaders", ".frag": "Shaders", ".geom": "Shaders",
    ".tesc": "Shaders", ".tese": "Shaders", ".vsh": "Shaders", ".psh": "Shaders", ".metal": "Shaders",
    ".wgsl": "Shaders", ".slang": "Shaders", ".gdshader": "Shaders", ".gdshaderinc": "Shaders", ".glslinc": "Shaders",
    ".gml": "GML (GameMaker)", ".hx": "Haxe", ".bb": "BlitzBasic", ".bmx": "BlitzMax", ".agc": "AppGameKit",
    ".nut": "Squirrel", ".luau": "Luau (Roblox)", ".moon": "MoonScript", ".monkey": "Monkey", ".monkey2": "Monkey",
    ".vb": "Visual Basic", ".fsx": "F#", ".dart": "Dart", ".scala": "Scala", ".zig": "Zig", ".nim": "Nim",
    ".coffee": "CoffeeScript", ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang", ".hs": "Haskell", ".ml": "OCaml",
    ".clj": "Clojure", ".groovy": "Groovy", ".pl": "Perl", ".tcl": "Tcl", ".bat": "Batch", ".cmd": "Batch",
    ".ink": "Ink (narrative)", ".yarn": "Yarn Spinner (dialogue)", ".twee": "Twine", ".tw": "Twine",
    ".nani": "Naninovel", ".cmake": "CMake (build scripts)", ".gradle": "Gradle (build scripts)",
    ".bas": "Visual Basic / VBA", ".cls": "Visual Basic / VBA", ".frm": "Visual Basic / VBA",
    ".ctl": "Visual Basic / VBA", ".dsr": "Visual Basic / VBA", ".pag": "Visual Basic / VBA", ".dob": "Visual Basic / VBA",
    ".vbs": "VBScript", ".tsql": "SQL", ".pks": "PL/SQL", ".pkb": "PL/SQL", ".prc": "PL/SQL", ".fnc": "PL/SQL",
    # Enterprise and legacy languages
    ".cbl": "COBOL", ".cob": "COBOL", ".cpy": "COBOL", ".f": "Fortran", ".for": "Fortran", ".f77": "Fortran",
    ".f90": "Fortran", ".f95": "Fortran", ".f03": "Fortran", ".f08": "Fortran", ".adb": "Ada", ".ads": "Ada",
    ".abap": "ABAP", ".jcl": "JCL", ".pli": "PL/I", ".pl1": "PL/I", ".rpgle": "RPG", ".sqlrpgle": "RPG",
    ".vhd": "VHDL", ".vhdl": "VHDL", ".sv": "Verilog", ".svh": "Verilog", ".vh": "Verilog", ".dpr": "Pascal",
}
# Extensions that mean code only inside a certain kind of project (elsewhere they're something else).
CONTEXT_CODE_EXTS = {
    ".script": ("Defold", "Lua (Defold)"), ".gui_script": ("Defold", "Lua (Defold)"),
    ".render_script": ("Defold", "Lua (Defold)"), ".fs": (".NET", "F#"),
}
# Build scripts, by name: the studio's code, but not the game's.
BUILD_SCRIPTS = re.compile(r"^(premake\d?\.lua|.*\.premake\.lua|cmakelists\.txt|makefile|gnumakefile|.*\.mk|"
                           r"sconstruct|sconscript|meson\.build|build\.ninja|jamfile|jamroot|.*\.jam|wscript)$", re.I)
BUILD_SCRIPT_LANGUAGE = {".lua": "Lua (build scripts)", ".txt": "CMake (build scripts)", ".build": "Meson (build scripts)"}
# Text files that aren't code, kept out of the list of unknown kinds that may be.
NOT_CODE_TEXT = {".txt", ".md", ".markdown", ".rst", ".adoc", ".json", ".jsonc", ".json5", ".xml", ".yml", ".yaml",
                 ".toml", ".ini", ".cfg", ".conf", ".config", ".properties", ".plist", ".log", ".lock", ".meta",
                 ".asset", ".csv", ".tsv", ".sln", ".csproj", ".vcxproj", ".filters", ".user", ".props", ".targets",
                 ".resx", ".editorconfig", ".gitignore", ".gitattributes", ".map", ".po", ".pot", ".strings", ".tex",
                 ".bib", ".patch", ".diff", ".srt", ".vtt", ".obj", ".mtl", ".ply", ".gltf", ".tmx", ".tsx", ".svg"}
UNKNOWN_TEXT_MIN_FILES = 5


# ####################
# Assets
# ####################
ASSET_EXTS = {
    "Scenes/levels": {".unity", ".scene", ".umap", ".unr", ".ut2", ".ut3", ".udk", ".rom", ".dx", ".un2",
                      ".tscn", ".scn", ".tmx", ".ldtk", ".vmf", ".bsp"},
    "Prefabs": {".prefab"},
    "3D models": {".fbx", ".obj", ".blend", ".max", ".ma", ".mb", ".dae", ".3ds", ".usx", ".mesh", ".gltf", ".glb",
                  ".usd", ".usda", ".usdc", ".usdz", ".lwo", ".c4d", ".skp", ".3dm", ".mdl", ".smd", ".ztl", ".zpr"},
    "Textures/images": {".png", ".psd", ".tga", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".dds", ".bmp", ".svg",
                        ".utx", ".vtf", ".ktx", ".ktx2", ".astc", ".pvr", ".webp", ".gif", ".hdr", ".psb", ".kra",
                        ".xcf", ".aseprite", ".ase", ".spp", ".sbs", ".sbsar"},
    "Audio": {".wav", ".ogg", ".mp3", ".aif", ".aiff", ".flac", ".bank", ".uax", ".umx", ".wem", ".bnk", ".fsb",
              ".opus", ".m4a"},
    "Animations": {".anim", ".controller", ".ukx", ".skeleton", ".skel", ".abc"},
    "Materials": {".mat", ".material", ".vmt", ".program"},
    "Visual effects": {".particle", ".compositor", ".vfx", ".pfx"},
    "UI layouts": {".layout", ".imageset", ".scheme", ".looknfeel", ".uxml", ".uss", ".csd", ".fontdef"},
    "Fonts": {".ttf", ".otf", ".fnt"},
    "Video": {".mp4", ".webm", ".bik", ".bk2", ".usm", ".ogv", ".avi", ".mov", ".wmv"},
    "Godot resources": {".tres"},
    "Documents (design docs, specs ...)": {".pdf", ".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".ppt",
                                           ".pptx", ".odp", ".pages", ".key", ".numbers"},
    "Jupyter notebooks": {".ipynb"},
    "Ren'Py compiled scripts": {".rpyc", ".rpymc"},
    "Ren'Py archives (.rpa)": {".rpa"},
    "Unreal packages (.upk, .upx)": {".upk", ".upx"},
    "Compiled UnrealScript (.u)": {".u"},
    "Unreal assets (type unknown)": {".uasset"},
    "Packaged Unreal game archives": {".pak", ".utoc"},
}


# ####################
# Tests and generated code
# ####################
TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "e2e", "editmode", "playmode"}
TEST_FILE = re.compile(r"(^test_.*\.py$|_test\.py$|^conftest\.py$|\.(test|spec)\.[cm]?[jt]sx?$)", re.I)
GENERATED_FILE = re.compile(r"(\.min\.(js|css)$|\.bundle\.js$|\.designer\.cs$|\.g\.cs$|\.generated\.\w+$|_pb2(_grpc)?\.py$"
                            r"|\.pb\.(cc|h)$|_generated\.h$|^moc_.*\.cpp$|^ui_.*\.h$|^qrc_.*\.cpp$|_wrap\.cx*$"
                            r"|^lex\.yy\.c$|\.tab\.[ch]$)", re.I)
GENERATED_HEADER = re.compile(rb"auto-?generated|@generated|do not edit", re.I)
MINIFIABLE_EXTS = {".js", ".mjs", ".cjs", ".css"}


# ##############################
# Someone else's code
# ##############################

# ####################
# Third-party folders
# ####################
# Folders whose code is probably someone else's: reported separately.
THIRD_PARTY_DIRS = {"vendor", "vendors", "_vendor", "vendored", "third_party", "thirdparty",
                    "third-party", "external", "externals", "extern",
                    "python-packages",   # where Ren'Py games bundle pip libraries
                    "fonts"}             # font vendors' demo pages and CSS
# Unity: Plugins/ anywhere under Assets (mostly SDKs and Asset Store code), and Unity's own
# add-ons imported directly into Assets.
UNITY_PLUGIN_DIRS = {"plugins"}
UNITY_ASSETS_THIRD_PARTY_DIRS = {"textmesh pro", "samples", "standard assets", "sample assets", "assetstoretools"}
# Ren'Py: a released game ships the engine (renpy/) and a copy of Python (lib/) next to game/.
RENPY_ROOT_THIRD_PARTY_DIRS = {"renpy", "lib"}
# Unreal: Epic's sample content and asset packs, directly under Content/.
UNREAL_CONTENT_THIRD_PARTY_DIRS = {"startercontent", "animstarterpack", "mannequin", "levelprototyping",
                                   "megascans", "marketplace", "fab"}
# Unreal Engine 1-3: Epic's own UnrealScript/C++ packages, which licensees and modders ship
# alongside their own (Core/Classes, Engine/Src, Development/Src/UTGame ...).
EPIC_UNREAL_PACKAGES = {
    "core", "engine", "editor", "unrealed", "fire", "ipdrv", "ipserver", "uweb", "ubrowser", "uwindow",
    "umenu", "utmenu", "utbrowser", "utserveradmin", "botpack", "unrealshare", "unreali", "render",
    "windrv", "window", "launch", "galaxy", "opengldrv", "d3ddrv", "d3d9drv", "d3d11drv", "alaudio",
    "xaudio2", "windows", "gameplay", "unrealgame", "xgame", "xinterface", "xadmin", "xwebadmin",
    "xpickups", "xeffects", "xweapons", "xvoting", "gui2k4", "onslaught", "onslaughtfull",
    "ut2k4assault", "ut2k4assaultfull", "utclassic", "bonuspack", "skaarjpack", "streamlinefx",
    "vehicles", "gameframework", "gfxui", "gfxuieditor", "udkbase", "utgame", "utgamecontent",
    "uteditor", "unrealscripttest", "onlinesubsystemsteamworks", "onlinesubsystemgamespy",
    "onlinesubsystemlive", "onlinesubsystempc",
}


def is_bought_unreal_plugin(uplugin_path):
    """A plugin from the Unreal Marketplace / Fab, or one of Epic's, copied into the project."""
    p = read_json(uplugin_path)
    return bool(p.get("MarketplaceURL") or p.get("FabURL") or p.get("Installed")
                or str(p.get("CreatedBy", "")).startswith("Epic Games"))


# ####################
# Libraries copied in
# ####################
# Libraries that studios often copy straight into their own source folders (Source/MyGame/boost/ ...).
KNOWN_LIBRARY_DIRS = {
    "boost", "sqlite", "sqlite3", "zlib", "zlib-ng", "libpng", "libjpeg", "libjpeg-turbo", "eigen", "eigen3",
    "glm", "rapidjson", "nlohmann", "fmt", "spdlog", "imgui", "freetype", "bullet", "bullet3", "physx",
    "openssl", "curl", "libcurl", "protobuf", "googletest", "gtest", "gmock", "catch2", "stb", "tinyxml",
    "tinyxml2", "pugixml", "yaml-cpp", "asio", "websocketpp", "msgpack", "flatbuffers", "zstd", "lz4",
    "openvr", "sdl2", "glfw", "glew", "assimp", "box2d", "luajit", "sol2", "enet", "libuv", "opus",
    "libogg", "libvorbis", "recastnavigation", "fastnoise", "fastnoiselite", "libnoise", "cereal", "xxhash",
    "concurrentqueue", "abseil", "absl", "tbb", "openal", "openal-soft", "bgfx", "mimalloc", "jemalloc",
    "tracy", "optick", "minizip", "libzip", "lzma", "brotli", "harfbuzz", "icu", "libsodium", "cryptopp",
    "mbedtls", "grpc", "poco", "cpprestsdk", "unlua", "sluaunreal", "discord-rpc", "discord_game_sdk",
}
KNOWN_LIBRARY_FILES = [   # (file name, library)
    (re.compile(r"^sqlite3\w*\.[ch]$", re.I), "SQLite"),
    (re.compile(r"^stb_\w+\.h$", re.I), "stb"),
    (re.compile(r"^(imgui\w*|imconfig|imstb_\w+)\.(h|cpp)$", re.I), "Dear ImGui"),
    (re.compile(r"^json\.hpp$", re.I), "nlohmann/json"),
    (re.compile(r"^(miniz\w*|lz4\w*|xxhash|zstd)\.[ch]$", re.I), "compression libraries"),
    (re.compile(r"^(tinyxml2?|pugixml|pugiconfig)\.(h|hpp|cpp)$", re.I), "XML libraries"),
    (re.compile(r"^(httplib|cgltf|miniaudio|dr_\w+|picojson|rapidxml\w*|cxxopts|doctest)\.(h|hpp)$", re.I),
     "single-header libraries"),
    (re.compile(r"^fastnoise\w*\.(h|cpp)$", re.I), "FastNoise"),
    (re.compile(r"^((blocking)?concurrentqueue|readerwriterqueue)\.h$", re.I), "moodycamel queues"),
    (re.compile(r"^(rpg|rmmz)_(core|managers|objects|scenes|sprites|windows)\.js$", re.I), "RPG Maker engine"),
    (re.compile(r"^(pixi|effekseer|lz-string|localforage|iphone-inline-video)(\.min)?\.js$", re.I), "RPG Maker's libraries"),
]
# A folder with its own licence file, copied in among a project's own code files, is a library.
# (One sitting among other packages, like Plugins/X or Mods/X, may well be the studio's own.)
LICENSE_FILE = re.compile(r"^(licen[cs]e|copying|copyright)([._-].*)?$", re.I)


# ####################
# Licence notices
# ####################
# Licence notices at the top of a file that say it's someone else's code.
LICENSE_HEADERS = [   # (notice, library or licence)
    (re.compile(rb"Boost Software License|LICENSE_1_0\.txt|SPDX-License-Identifier: *BSL-1\.0"), "Boost"),
    (re.compile(rb"The author disclaims copyright to this source code"
                rb"|amalgamation of many separate C source files from SQLite"), "SQLite"),
    (re.compile(rb"Permission is hereby granted, free of charge|SPDX-License-Identifier: *MIT\b"), "MIT-licensed code"),
    (re.compile(rb"Licensed under the Apache License|SPDX-License-Identifier: *Apache"), "Apache-licensed code"),
    (re.compile(rb"GNU (Lesser |Library |Affero )?General Public License|SPDX-License-Identifier: *[AL]?GPL"),
     "GPL/LGPL code"),
    (re.compile(rb"Redistribution and use in source and binary forms|SPDX-License-Identifier: *BSD"),
     "BSD-licensed code"),
    (re.compile(rb"This software is provided 'as-is', without any express or implied|SPDX-License-Identifier: *Zlib"),
     "zlib-licensed code"),
    (re.compile(rb"Mozilla Public License|SPDX-License-Identifier: *MPL"), "MPL-licensed code"),
    (re.compile(rb"free and unencumbered software released into the public domain"
                rb"|SPDX-License-Identifier: *(Unlicense|CC0)"), "public-domain code"),
]
# Epic's notice. NOT a sign of someone else's code: Unreal's templates put it on a project's first
# files, and developers keep it on files they start by copying those.
EPIC_HEADER = re.compile(rb"Copyright (\(c\) )?([\d-]+,? )?Epic Games")
# Other engine makers' notices: their SDK's files, or ones begun from them. Pointed out, not excluded.
VENDOR_NOTICES = [
    ("Valve's copyright notice (Source SDK)", re.compile(rb"Copyright[^\n]{0,40}Valve Corporation")),
    ("Crytek's copyright notice (CRYENGINE)", re.compile(rb"Crytek GmbH|Copyright[^\n]{0,40}Crytek")),
    ("Unity Technologies' copyright notice", re.compile(rb"Copyright[^\n]{0,40}Unity Technologies")),
    ("Amazon's copyright notice (Lumberyard / O3DE)",
     re.compile(rb"Copyright[^\n]{0,40}Amazon\.com|Contributors to the Open 3D Engine Project")),
]
EPIC_NOTICE = "Epic's copyright notice"
ENGINE_NOTICES = {EPIC_NOTICE} | {notice for notice, _ in VENDOR_NOTICES}


# ####################
# Unity Asset Store packages
# ####################
# Unity Asset Store packages: the studio can't license them (it didn't write them), and they unpack
# into folders with any name under Assets/. Recognised by (1) the packages Unity downloaded on this
# computer, (2) a readme pointing to the Asset Store, or documentation plus demo folders, the usual
# layout of a package, and (3) the folder names of widely used packages:
UNITY_ASSET_STORE_DIRS = {
    "demigiant", "dotween", "sirenix", "odin inspector", "playmaker", "rewired", "photon",
    "photon unity networking", "photonunitynetworking", "unirx", "rootmotion", "finalik", "puppetmaster",
    "amplifyshadereditor", "amplifyimpostors", "amplifycolor", "amplifymotion", "gaia", "procedural worlds",
    "easy save 3", "easysave3", "behavior designer", "opsive", "pixelcrushers", "dialogue system", "i2",
    "moremountains", "nicevibrations", "corgiengine", "topdownengine", "ludiq", "qfsw", "animancer",
    "astarpathfindingproject", "a* pathfinding project", "easytouch", "easytouchbundle", "hedgehog team",
    "ngui", "leantween", "leantouch", "doozy", "naughtyattributes", "kinematiccharactercontroller", "obi",
    "ultimate character controller", "ufps", "vegetation studio", "enviro", "microsplat", "bakery",
    "borodar", "polybrush", "procore", "camerapath3", "camera path animator", "procamera2d", "tk2d",
    "tk2dtk", "2dtoolkit", "spine", "spine examples", "fmod", "fmodunity", "wwise", "steamworks.net",
    "facebooksdk", "googlemobileads", "gameanalytics", "playfabsdk", "gamesparks", "chartboost",
    "ironsource", "maxsdk", "applovin", "prime31", "vuforia", "zenject", "extenject", "itween", "hotween",
    "besthttp", "best http", "uniwebview", "nativegallery", "nativeshare", "jsondotnet", "json .net",
    "meshbaker", "mesh baker", "simple waypoint system", "ootii", "invector", "dynamicbone", "dynamic bone",
    "magica cloth", "magicacloth", "uma", "uma2", "crazyminnow", "salsa", "adventure creator",
    "adventurecreator", "fungus", "yarn spinner", "articy", "febucci", "text animator", "michsky",
    "modern ui pack", "layer lab", "quest machine", "mmfeedbacks", "dreamteck", "curvy",
    "polyfew", "realistic car controller", "edy's vehicle physics", "nwh", "rpg builder", "unistorm",
    "azure sky", "suimono", "aquas", "ceto", "hx volumetric lighting", "beautify",
    "ultimate game tools", "obi cloth", "obi rope", "puppet3d", "anima2d", "lipsync", "rogo digital",
}
ASSET_STORE_MENTION = re.compile(rb"assetstore\.unity3?d?\.com|u3d\.as/|\bAsset ?Store\b", re.I)
README_FILE = re.compile(r"^(read[ _-]?me|documentation|manual|guide|getting[ _-]?started|quick[ _-]?start|"
                         r"change[ _-]?log|release[ _-]?notes|version|about|support|licen[cs]e|eula)\b.*"
                         r"\.(txt|md|html?|rtf)$", re.I)
PACKAGE_DOC_DIRS = {"documentation", "docs", "doc", "manual", "help"}
PACKAGE_DEMO_DIRS = {"demo", "demos", "example", "examples", "demo scenes", "example scenes", "demoscenes",
                     "examplescenes", "_demo", "_demos", "_examples"}


def looks_like_asset_store_package(dirpath, filenames, dirnames):
    """A folder laid out like an Asset Store package: a readme that points to the Asset Store, or
    documentation and demo folders side by side (a studio's own folders rarely ship demos)."""
    subdirs = {d.lower() for d in dirnames}
    if subdirs & PACKAGE_DOC_DIRS and subdirs & PACKAGE_DEMO_DIRS:
        return True
    for name in filenames:
        if README_FILE.match(name):
            try:
                with open(os.path.join(dirpath, name), "rb") as f:
                    if ASSET_STORE_MENTION.search(f.read(200_000)):
                        return True
            except OSError:
                pass
    return False


def asset_store_download_folders():
    """Where Unity keeps the Asset Store packages downloaded on this computer."""
    home = os.path.expanduser("~")
    if os.name == "nt":
        base = os.path.join(os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming"), "Unity")
    elif sys.platform == "darwin":
        base = os.path.join(home, "Library", "Unity")
    else:
        base = os.path.join(home, ".local", "share", "unity3d")
    folders = [os.path.join(base, n) for n in list_files(base) if n.lower().startswith("asset store")]
    if os.environ.get("ASSETSTORE_CACHE_PATH"):   # Unity 2022+ lets the cache be moved
        folders.append(os.environ["ASSETSTORE_CACHE_PATH"])
    return [f for f in folders if not (OFFLINE and is_network_path(f))]   # --offline: not even on a network share


ASSET_STORE_TIME_LIMIT = 300   # seconds spent reading downloaded packages, at most
_asset_store = []              # read once per run: (guids, packages read, packages found)


def asset_store_guids():
    """({asset guid: package name}, packages read, packages found) for the Asset Store packages
    downloaded on this computer. Unity keeps an asset's guid (in its .meta file) when importing it,
    so this recognises a package's files in a project even if they were moved or renamed."""
    if _asset_store:
        return _asset_store[0]
    import tarfile
    import time
    import zlib
    packages = []
    for folder in asset_store_download_folders():
        for dirpath, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".unitypackage"):
                    try:
                        packages.append((os.path.getsize(os.path.join(dirpath, f)), os.path.join(dirpath, f)))
                    except OSError:
                        pass
    guids, read, deadline = {}, 0, time.monotonic() + ASSET_STORE_TIME_LIMIT
    for _, path in sorted(packages):   # small (code) packages first, big art packs last
        if time.monotonic() > deadline:
            break
        name = os.path.splitext(os.path.basename(path))[0]
        progress(f"Reading Unity's Asset Store downloads: {name}")
        try:
            with tarfile.open(path, mode="r|gz") as tar:   # each asset is a folder named by its guid
                for member in tar:
                    guid = member.name.lstrip("./").split("/", 1)[0].lower()
                    if re.fullmatch(r"[0-9a-f]{32}", guid):
                        guids[guid] = name
            read += 1
        except (OSError, EOFError, tarfile.TarError, zlib.error):
            continue
    progress()
    _asset_store.append((guids, read, len(packages)))
    return _asset_store[0]


def meta_guid(path):
    """The guid in a Unity asset's .meta file, or None."""
    try:
        with open(path + ".meta", "rb") as f:
            m = re.search(rb"guid:\s*([0-9a-fA-F]{32})", f.read(400))
    except OSError:
        return None
    return m.group(1).decode().lower() if m else None


# #######################################
# Reading source files
# #######################################

# ##############################
# Languages named with --code-ext
# ##############################
# Languages this script doesn't know, named with --code-ext (".par=PARLANSE", ".atg=DMS grammar:Ada"):
# extension -> (name, the known language whose comments it shares). This script counts every
# non-blank line of them, as of every language; scc and jscpd are told to read them as that known
# language (scc's name for it, jscpd's), "text" (the default) as plain text.
EXTRA_CODE = {}
LIKE_LANGUAGES = {"text": ("Plain Text", "txt"), "C": ("C", "c"), "C++": ("C++", "cpp"), "Ada": ("Ada", "ada"),
                  "SQL": ("SQL", "sql"), "Lisp": ("Lisp", "lisp"), "Python": ("Python", "python"),
                  "Pascal": ("Pascal", "pascal"), "Lua": ("Lua", "lua"), "Visual Basic": ("Visual Basic", "visual-basic")}

# Code this script counts that the pinned scc doesn't recognise (it skips the files) and jscpd
# doesn't read: extension -> the known language whose comments it shares (LIKE_LANGUAGES). When
# the studio's own code has some, scc and jscpd are told to read them as that language, as with
# --code-ext, so the standard measures include them, and the report says so. Not Visual Basic 6's
# form and control files (.frm, .ctl ...): read whole, their designer section would count as code.
UNRECOGNISED_CODE = {
    ".rpy": "Python", ".rpym": "Python", ".verse": "Python",                     # Ren'Py, Verse: # comments
    ".ink": "C", ".sk": "C", ".nut": "C", ".agc": "C", ".pl1": "C", ".pli": "C",   # // or /* */ comments
    ".cg": "C", ".cginc": "C", ".compute": "C", ".fx": "C", ".fxh": "C", ".gdshader": "C", ".gdshaderinc": "C",
    ".glslinc": "C", ".hlsl": "C", ".psh": "C", ".shader": "C", ".usf": "C", ".ush": "C",   # shaders
    ".tcc": "C++", ".moon": "Lua", ".dpr": "Pascal", ".tsql": "SQL", ".nani": "Lisp",       # Naninovel: ; comments
    ".bmx": "Visual Basic", ".monkey": "Visual Basic", ".monkey2": "Visual Basic", ".vbs": "Visual Basic",   # ' comments
    ".rpgle": "text", ".sqlrpgle": "text", ".tw": "text", ".twee": "text"}


def add_code_extension(spec):
    """--code-ext: count files with this extension as code in a language of their own. Raises
    ValueError for a spec it can't read."""
    m = re.fullmatch(r"\s*\.?([^=.\s/\\]+)\s*=\s*([^:]*?)\s*(?::\s*(.+?))?\s*", spec)
    if not m or not m.group(2):
        raise ValueError(f"--code-ext {spec!r}: give it as .ext=Name, or .ext=Name:Like (Like: a language whose"
                         f" comments it shares: {', '.join(LIKE_LANGUAGES)})")
    ext, name = "." + m.group(1).lower(), m.group(2)
    like = next((k for k in LIKE_LANGUAGES if k.lower() == (m.group(3) or "text").lower()), None)
    if like is None:
        raise ValueError(f"--code-ext {spec!r}: {m.group(3)!r} isn't one of {', '.join(LIKE_LANGUAGES)}")
    EXTRA_CODE[ext] = (name, like)
    CODE_EXTS[ext] = name


# ##############################
# What else a file shows
# ##############################

# ####################
# Includes and copyright years
# ####################
C_FAMILY_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hh", ".hpp", ".hxx", ".h++", ".inl", ".ipp", ".tcc",
                 ".m", ".mm", ".cu", ".cuh"}
INCLUDE = re.compile(rb'^[ \t]*#[ \t]*(?:include|import)[ \t]*[<"]([^>"\r\n]+)[>"]', re.M)
COPYRIGHT_YEARS = re.compile(rb"(?:Copyright|\(c\)|\xc2\xa9)[^\n\d]{0,40}((?:19[89]|20[0-4])\d)"
                             rb"(?:\s*[-\x96,]\s*((?:19[89]|20[0-4])\d))?", re.I)


# ####################
# Authors
# ####################
# A file's author named in a comment ("@author Jane Doe", "Author: Jane", Xcode's "Created by Jane Doe
# on 3/4/15.", Python's __author__): without version control, the only trace of who wrote the code.
# Only counted, never reported by name.
AUTHOR_LINE = re.compile(rb"^[ \t]*(?://+|/?\*+|#+|'+|--+|;+|rem\b|<!--|\{|\(\*)[ \t]*"
                         rb"(?:@author\b|authors?[ \t]*:|(?:written|created|coded|programmed)[ \t]+by\b"
                         rb"|programmers?[ \t]*:)[ \t]*:?[ \t]*([^\r\n]+)", re.I | re.M)
PY_AUTHOR = re.compile(rb"^__author__[ \t]*=[ \t]*[rbuRBU]?['\"]([^'\"\r\n]+)['\"]", re.M)
NOT_AUTHOR_WORDS = {"the", "a", "an", "this", "that", "these", "see", "me", "us", "you", "hand", "unity", "unreal",
                    "epic", "microsoft", "visual", "xcode", "wizard", "generator", "tool", "tools", "script", "auto",
                    "automatically", "and", "of", "on", "in", "is", "for", "with", "using", "via", "from", "to",
                    "not", "no", "various", "many", "several", "individual", "other", "others", "contributors",
                    "unknown", "anonymous", "jr", "sr", "january", "february", "march", "april", "may", "june",
                    "july", "august", "september", "october", "november", "december"}
PLACEHOLDER_AUTHORS = {"john doe", "jane doe", "your name", "first last", "firstname lastname", "author name"}


def authors_in(text):
    """The people named as authors in a file's comments (see AUTHOR_LINE), each a tuple of identities
    (name, email) as count_people takes them."""
    found = []
    for raw in AUTHOR_LINE.findall(text) + PY_AUTHOR.findall(text):
        line = re.sub(r"\s*(\*/|-->|\*\)|\})\s*$", "", raw.decode("utf-8", "replace"))
        emails = re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", line)
        # What comes before an email, a date, a year or a note: "Jane Doe <jane@x.com>", "Jane Doe on 3/4/15."
        head = re.split(r"\s*[<(\[;]|\s+on\s+\d|\s+\d|\s+-\s|\s+at\s+|\s+for\s+|\s+in\s+", line, maxsplit=1)[0]
        names = []
        for part in re.split(r"\s*(?:,|&|/|\band\b)\s*", head):
            name = part.strip(" \t.:-*'\"")
            words = name.split()
            if (1 <= len(words) <= 4 and len(name) <= 40 and all(w[0].isalpha() for w in words)
                    and words[0].lower().rstrip(".") not in NOT_AUTHOR_WORDS
                    and name.lower() not in GENERIC_NAMES | PLACEHOLDER_AUTHORS
                    and not re.search(r"[$%{}=\\@]", name)):
                names.append(name)
        if len(names) == 1:
            found.append(tuple([names[0]] + emails[:1]))
        else:
            found += [(n,) for n in names] + ([(emails[0],)] if not names and emails else [])
    return found


# ####################
# Data pasted into the code
# ####################
# Lines that are just numbers in a list: an image, font or sound pasted into the code as an array.
# (Checked value by value: one regular expression over the whole line can take forever on long ones.)
DATA_VALUE = re.compile(rb"(?:0[xX][0-9a-fA-F]+|-?\d+(?:\.\d+)?[fFuUlL]*|'\\?.'|\"(?:\\x[0-9a-fA-F]{2})+\")")


def is_data_line(line):
    values = [v.strip() for v in line.strip().rstrip(b";}").split(b",")]
    values = [v for v in values if v]
    return bool(values) and all(DATA_VALUE.fullmatch(v) for v in values)


# ####################
# Credentials
# ####################
# Credentials that would have to be removed before the code changes hands. Only their kind is
# reported, never the text.
SECRETS = [
    ("private keys", re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY")),
    ("AWS access keys", re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Google API keys", re.compile(rb"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("GitHub tokens", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack tokens", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe secret keys", re.compile(rb"\b[sr]k_live_[0-9A-Za-z]{20,}")),
    ("passwords in connection strings", re.compile(rb"(?i)\b(?:password|pwd)=[^;\s\"'<>]{4,};")),
]


def secrets_in(data):
    return {kind for kind, pattern in SECRETS if pattern.search(data)}


# ##############################
# Reading one file
# ##############################

def read_code_file(path, ext):
    """What's in one source file, as a dict: lines (non-blank), generated, licence (the library or
    licence its header names, or EPIC_NOTICE, or None), data (mostly an embedded data array, not
    code), includes (#include paths, C-family only), years (in copyright notices), authors (people
    named as authors in comments, see authors_in), secrets (kinds of credentials found) and digest
    (to spot the same file in several places)."""
    facts = {"lines": 0, "generated": False, "licence": None, "data": False, "includes": [], "years": [],
             "authors": [], "secrets": set(), "digest": None}
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return facts

    # ####################
    # Lines
    # ####################
    import hashlib
    text = as_text(data)
    lines = [line for line in text.splitlines() if line.strip()]
    facts["lines"] = len(lines)
    facts["digest"] = hashlib.sha1(data).hexdigest()

    # ####################
    # Whose it is: licence notices; generated or pasted-in data
    # ####################
    minified = ext in MINIFIABLE_EXTS and len(data) > 20_000 and lines and len(data) / len(lines) > 300
    head = data[:6000]
    licence = next((label for pattern, label in LICENSE_HEADERS if pattern.search(head)), None)
    if licence is None and EPIC_HEADER.search(head[:1500]):
        licence = EPIC_NOTICE
    if licence is None:
        licence = next((notice for notice, pattern in VENDOR_NOTICES if pattern.search(head[:1500])), None)
    facts["licence"] = licence
    facts["generated"] = bool(minified or GENERATED_HEADER.search(data[:1500]))
    if len(lines) >= 40:
        sample = lines[:: max(1, len(lines) // 400)]
        facts["data"] = sum(1 for line in sample if is_data_line(line)) >= 0.8 * len(sample)

    # ####################
    # What else it shows
    # ####################
    if ext in C_FAMILY_EXTS:
        facts["includes"] = [m.decode("utf-8", "replace").strip() for m in INCLUDE.findall(data)]
    facts.update(database_code_facts(path, ext, data, lines))
    for start, end in COPYRIGHT_YEARS.findall(head):
        facts["years"] += [int(start)] + ([int(end)] if end else [])
    facts["authors"] = authors_in(b"\n".join(lines))
    facts["secrets"] = secrets_in(data)
    return facts


# #######################################
# Unreal packages
# #######################################

# Unreal packages (.uasset, .umap, .upk, .u, ...): the engine version that saved each one, the
# class of its main asset, and its visual-scripting nodes (Blueprints, Kismet, materials ...).
# Only the package's header tables are read, never the asset data itself.

# ##############################
# Reading binary values
# ##############################

class Bytes:
    """Reads values from a buffer, little- or big-endian. Reading past the end raises."""

    def __init__(self, data, pos=0, endian="<"):
        self.data, self.pos, self.endian = data, pos, endian

    def _unpack(self, fmt, size):
        value = struct.unpack_from(self.endian + fmt, self.data, self.pos)[0]
        self.pos += size
        return value

    # ####################
    # Numbers
    # ####################

    def i32(self):
        return self._unpack("i", 4)

    def u32(self):
        return self._unpack("I", 4)

    def u16(self):
        return self._unpack("H", 2)

    def skip(self, n):
        if n < 0 or self.pos + n > len(self.data):
            raise ValueError("past the end")
        self.pos += n

    # ####################
    # Strings
    # ####################

    def string(self, length):
        """A string of `length` characters; a negative length means UTF-16."""
        size = -2 * length if length < 0 else length
        if size > 1 << 20 or self.pos + size > len(self.data):
            raise ValueError("bad string")
        raw = self.data[self.pos:self.pos + size]
        self.pos += size
        encoding = "latin-1" if length >= 0 else ("utf-16-le" if self.endian == "<" else "utf-16-be")
        return raw.decode(encoding, "replace").rstrip("\0")

    def fstring(self):
        return self.string(self.i32())

    def compact(self):
        """Unreal Engine 1/2's variable-length integer."""
        b = self.data[self.pos]
        self.pos += 1
        value, negative, more, shift = b & 0x3F, b & 0x80, b & 0x40, 6
        while more and shift < 35:
            b = self.data[self.pos]
            self.pos += 1
            value |= (b & 0x7F) << shift
            more, shift = b & 0x80, shift + 7
        return -value if negative else value


# ##############################
# Visual-scripting nodes
# ##############################
UE3_KISMET_NODE = re.compile(r"Seq(Act|Event|Cond|Var)?_")
NOT_A_NODE = re.compile(r"Comment|Knot|Reroute")
BLUEPRINT_NODE_PREFIXES = ("K2Node_", "AnimGraphNode_", "AnimStateNode", "AnimStateTransitionNode",
                           "AnimStateConduitNode", "AnimStateEntryNode", "AnimStateAliasNode")


def node_kind(cls, engine):
    """Which kind of visual-scripting node an object of class `cls` is, or None. Comments and
    reroute knots aren't counted, just as blank lines aren't counted in code."""
    if NOT_A_NODE.search(cls):
        return None
    if engine == "UE3":
        if UE3_KISMET_NODE.search(cls):
            return "kismet"
        return "material" if cls.startswith("MaterialExpression") else None
    if cls.startswith(BLUEPRINT_NODE_PREFIXES):
        return "blueprint"
    if cls.startswith("MaterialExpression"):
        return "material"
    if cls.startswith("MaterialGraphNode"):   # the editor's twin of a MaterialExpression
        return None
    if re.search(r"Graph\w*Node", cls) or cls.startswith("NiagaraNode"):   # behavior trees, sound cues,
        return "graph"                                                     # Control Rig, PCG, MetaSounds ...
    return None


# ##############################
# Reading a package
# ##############################
UNREAL_PACKAGE_EXTS = {".uasset", ".umap", ".u", ".upk", ".upx", ".udk", ".ut3", ".unr", ".ut2", ".utx",
                       ".uax", ".umx", ".usx", ".ukx", ".rom", ".dx", ".un2"}
UE4_FILTER_EDITOR_ONLY = 0x80000000   # package flag: cooked for a packaged game, editor data stripped
UE3_COOKED, UE3_COMPRESSED = 0x8, 0x02000000
MAX_PACKAGE_READ = 256 * 1024 * 1024
GRAPH_TRACES = re.compile(rb"K2Node_|EdGraph|BlueprintGeneratedClass|AnimGraphNode_|SeqAct_|SeqEvent_")
MAX_IMPORT_SIZE, MAX_EXPORT_SIZE = 48, 160


def read_unreal_package(path):
    """Returns None if the file isn't an Unreal package, otherwise a dict:
        engine       "UE1" ... "UE5"
        version      "4.27" (the engine that saved it), or e.g. "UE2, package version 128"
        cooked       True if from a packaged game: editor-only data, like Blueprint graphs, is gone
        main_class   class of the package's main asset, e.g. "Blueprint" or "World" (UE4/5)
        nodes        Counter of visual-scripting nodes: "blueprint", "material", "kismet", "graph"
        classes, script_lines   UnrealScript classes compiled into a UE1/2 .u and the
                                non-blank lines of their source, which .u files carry along
        status       "read" (its tables were read, nodes and all), "header" (only its version: a
                     kind of package without graphs), "cooked", or "unreadable"
        looks_like_blueprint   for an unreadable one: does it seem to hold graphs we couldn't count?
    """
    info = {"engine": "?", "version": None, "cooked": False, "main_class": None, "nodes": Counter(),
            "classes": 0, "script_lines": 0, "status": "unreadable", "looks_like_blueprint": False}
    stem, ext = os.path.splitext(os.path.basename(path))
    try:
        with open(path, "rb") as f:
            head = f.read(65536)
            if len(head) < 64:
                return None
            if head[1:4] == b"\x83\x2a\x9e":     # 0x9E2A83C1 (Red Orchestra uses ...C2)
                endian = "<"
            elif head[0:3] == b"\x9e\x2a\x83":   # big-endian: Xbox 360 / PS3 builds
                endian = ">"
            else:
                return None

            def read_upto(end):
                if end <= len(head):
                    return head
                if end > MAX_PACKAGE_READ:
                    raise ValueError("too big")
                f.seek(0)
                return f.read(end)

            r = Bytes(head, 4, endian)
            if r.i32() < 0:
                read_ue4_package(head, read_upto, endian, stem, info, os.fstat(f.fileno()).st_size)
            else:
                r.pos = 4
                version_word = r.u32()
                version, licensee = version_word & 0xFFFF, version_word >> 16
                if version >= 150:
                    read_ue3_package(head, read_upto, endian, version, licensee, info)
                else:
                    info["engine"] = "UE1" if version < 100 else "UE2"
                    info["version"] = "{}, package version {}{}".format(
                        info["engine"], version, f", licensee {licensee}" if licensee else "")
                    if ext.lower() == ".u":
                        size = os.fstat(f.fileno()).st_size
                        read_ue12_script_package(read_upto(size), endian, version, info)
                    else:
                        info["status"] = "header"
    except (OSError, ValueError, IndexError, KeyError, struct.error):
        pass   # unreadable or an unusual licensee format: keep whatever was found so far
    if info["status"] == "unreadable":
        info["looks_like_blueprint"] = bool(GRAPH_TRACES.search(head))
    return info


# ####################
# Unreal Engine 4 and 5
# ####################

def read_ue4_package(head, read_upto, endian, stem, info, file_size):
    # ####################
    # The package summary: versions and flags
    # ####################
    r = Bytes(head, 4, endian)
    legacy = r.i32()                 # -2 (early UE4) ... -9 (UE 5.6)
    if legacy != -4:
        r.i32()                      # UE3 version, for old tools
    ue4 = r.i32()
    ue5 = r.i32() if legacy <= -8 else 0
    r.i32()                          # licensee version
    info["engine"] = "UE5" if ue5 >= 1000 else "UE4"
    if legacy <= -9:
        r.skip(24)                   # saved hash, header size
    custom_versions = r.i32()
    if not 0 <= custom_versions < 10000:
        raise ValueError("bad header")
    for _ in range(custom_versions):
        if legacy == -2:
            r.skip(8)
        elif legacy >= -5:
            r.skip(20)
            r.fstring()
        else:
            r.skip(20)
    if legacy > -9:
        r.i32()                      # header size
    r.fstring()                      # package name
    flags = r.u32()
    if ue4 == 0 or flags & UE4_FILTER_EDITOR_ONLY:
        info["cooked"] = True        # unversioned or cooked: can't (and needn't) read further
        info["version"] = info["engine"] + " (cooked, version unknown)"
        info["status"] = "cooked"
        return

    # ####################
    # Where the tables are, and the engine version
    # ####################
    name_count, name_offset = r.i32(), r.i32()
    if ue5 >= 1008:
        r.skip(8)                    # soft object paths
    if ue4 >= 516:
        r.fstring()                  # localization id
    if ue4 >= 459:
        r.skip(8)                    # gatherable text
    export_count, export_offset, import_count, import_offset = r.i32(), r.i32(), r.i32(), r.i32()
    if ue5 >= 1015:
        r.skip(16)                   # Verse cells
    if ue5 >= 1014:
        r.skip(4)                    # metadata offset
    depends_offset = r.i32()
    try:
        r.skip((8 if ue4 >= 384 else 0) + (4 if ue4 >= 510 else 0) + 4 + (16 if ue5 < 1016 else 0)
               + (16 if ue4 >= 518 else 0) + (16 if 518 <= ue4 < 520 else 0))
        generations = r.i32()
        r.skip(8 * generations)
        if ue4 >= 336:
            major, minor = r.u16(), r.u16()
            if major in (4, 5):
                info["version"] = f"{major}.{minor}"
            elif major == 0:
                info["version"] = info["engine"] + " (custom-built engine)"
    except (ValueError, struct.error):
        pass
    if info["version"] is None:
        info["version"] = info["engine"]

    # ####################
    # The name, import and export tables
    # ####################
    # The import table lists the classes used; the export table the objects in this package. Their
    # entries have fixed sizes, which depend on the version (and, in some modified engines, on the
    # licensee). Work them out from where the tables start and end; if that doesn't add up, try
    # each plausible size, keeping it only if every entry in the table makes sense.
    if not (0 < name_offset and 0 < name_count < 10_000_000 and 0 <= import_count < 10_000_000
            and 0 < export_count < 10_000_000 and 0 < import_offset and 0 < export_offset):
        return
    end = max(depends_offset, export_offset + export_count * MAX_EXPORT_SIZE,
              import_offset + import_count * MAX_IMPORT_SIZE)
    data = read_upto(min(end, MAX_PACKAGE_READ))
    r = Bytes(data, name_offset, endian)
    names = []
    for _ in range(name_count):
        names.append(r.fstring())
        if ue4 >= 504:
            r.skip(4)                # name hashes
    unpack = struct.Struct(endian + "ii").unpack_from

    def imports_ok(size):
        if import_offset + import_count * size > len(data):
            return False
        return all(0 <= unpack(data, import_offset + i * size + 8)[0] < name_count
                   and 0 <= unpack(data, import_offset + i * size + 20)[0] < name_count for i in range(import_count))

    # Where each export's data is in the file: after the name and the object flags, as 64-bit
    # numbers from 4.15 (VER_UE4_64BIT_EXPORTMAP_SERIALSIZES), 32-bit before.
    serial = struct.Struct(endian + ("qq" if ue4 >= 511 else "ii"))

    def exports_ok(size, name_at):
        tables_end = export_offset + export_count * size
        if tables_end > len(data) or name_at + 12 + serial.size > size:
            return False
        for i in range(export_count):
            pos = export_offset + i * size
            class_index, outer = unpack(data, pos)[0], unpack(data, pos + name_at - 4)[0]
            serial_size, serial_offset = serial.unpack_from(data, pos + name_at + 12)
            if not (-import_count <= class_index <= export_count and -import_count <= outer <= export_count
                    and 0 <= unpack(data, pos + name_at)[0] < name_count
                    and 0 <= serial_size and tables_end <= serial_offset and serial_offset + serial_size <= file_size):
                return False
        return True

    # ####################
    # Working out the table entries' sizes
    # ####################
    def computed(start, stop, count):
        size, rest = divmod(stop - start, count) if count and stop > start else (0, 1)
        return [size] if not rest else []

    import_size = 0
    if import_count:
        import_size = next((size for size in computed(import_offset, export_offset, import_count) + [28, 32, 36, 40, 44, 48]
                            if 24 <= size <= MAX_IMPORT_SIZE and imports_ok(size)), None)
    export_size = name_at = None
    for name_at in ([12, 16] if ue4 < 508 else [16, 12]):   # ObjectName follows TemplateIndex from 4.14 on
        export_size = next((size for size in computed(export_offset, depends_offset, export_count)
                            + list(range(56, MAX_EXPORT_SIZE + 1, 4))
                            if 56 <= size <= MAX_EXPORT_SIZE and exports_ok(size, name_at)), None)
        if export_size:
            break
    if import_size is None or not export_size:
        return

    # ####################
    # Counting nodes, and finding the main asset
    # ####################
    imports = [names[unpack(data, import_offset + i * import_size + 20)[0]] for i in range(import_count)]
    nodes = Counter()
    for i in range(export_count):
        pos = export_offset + i * export_size
        class_index = unpack(data, pos)[0]
        cls = imports[-class_index - 1] if class_index < 0 else None
        if cls:
            kind = node_kind(cls, "UE4")
            if kind:
                nodes[kind] += 1
        outer = unpack(data, pos + name_at - 4)[0]
        name_index, number = unpack(data, pos + name_at)
        name = names[name_index] + (f"_{number - 1}" if number else "")
        if outer == 0 and name.lower() == stem.lower():
            info["main_class"] = cls
    info["nodes"] = nodes
    info["status"] = "read"


# ####################
# Unreal Engine 3
# ####################

def read_ue3_package(head, read_upto, endian, version, licensee, info):
    info["engine"] = "UE3"
    info["version"] = "UE3, package version {}{}".format(version, f", licensee {licensee}" if licensee else "")
    r = Bytes(head, 8, endian)
    if version >= 249:
        r.i32()                      # header size
    if version >= 269:
        r.fstring()                  # folder name
    flags = r.u32()
    name_count, name_offset, export_count, export_offset, import_count, import_offset = (
        r.i32(), r.i32(), r.i32(), r.i32(), r.i32(), r.i32())
    depends_offset = r.i32() if version >= 415 else 0
    info["cooked"] = bool(flags & UE3_COOKED)

    # ####################
    # Kismet and material nodes
    # ####################
    # Kismet and material nodes, from the export table. Its layout varies between UE3 versions and
    # licensees, so it's only trusted if it ends exactly where the next table starts.
    if flags & UE3_COMPRESSED:
        info["status"] = "cooked"    # its tables are compressed
        return
    if version < 491:
        info["status"] = "header"    # early UE3: before Kismet as we know it
        return
    if not 0 < name_offset < import_offset < export_offset < depends_offset:
        return
    data = read_upto(depends_offset)
    r = Bytes(data, name_offset, endian)
    names = []
    for _ in range(name_count):
        names.append(r.fstring())
        r.skip(8)                    # name flags
    r.pos = import_offset
    imports = []
    for _ in range(import_count):
        r.skip(20)                   # class package, class name, outer
        imports.append(names[r.i32()])
        r.skip(4)
    r.pos = export_offset
    nodes = Counter()
    for _ in range(export_count):
        class_index = r.i32()
        r.skip(28)                   # super, outer, name, archetype, flags
        r.skip(8)                    # serial size and offset
        if version < 543:
            r.skip(12 * r.i32())     # component map
        r.skip(4)                    # export flags
        r.skip(4 * r.i32())          # net object counts
        r.skip(20)                   # package guid and flags
        if class_index < 0:
            kind = node_kind(imports[-class_index - 1], "UE3")
            if kind:
                nodes[kind] += 1
    if r.pos == depends_offset:
        info["nodes"] = nodes
        info["status"] = "read"


# ####################
# Unreal Engine 1 and 2
# ####################

def read_ue12_script_package(data, endian, version, info):
    """A UE1/2 .u holds compiled UnrealScript classes, and usually each class's source text too."""
    r = Bytes(data, 12, endian)
    name_count, name_offset, export_count, export_offset, import_count, import_offset = (
        r.i32(), r.i32(), r.i32(), r.i32(), r.i32(), r.i32())

    # ####################
    # The name and import tables
    # ####################
    r.pos = name_offset
    names = []
    for _ in range(name_count):
        if version >= 64:
            names.append(r.string(r.compact()))
        else:
            end = data.index(b"\0", r.pos)
            names.append(data[r.pos:end].decode("latin-1"))
            r.pos = end + 1
        r.skip(4)                    # name flags
    r.pos = import_offset
    imports = []
    for _ in range(import_count):
        r.compact()
        r.compact()
        r.i32()
        imports.append(names[r.compact()])

    # ####################
    # Classes and their source text, from the export table
    # ####################
    r.pos = export_offset
    for _ in range(export_count):
        class_index = r.compact()
        r.compact()                  # super
        r.i32()                      # outer
        name = names[r.compact()]
        r.skip(4)                    # flags
        size = r.compact()
        offset = r.compact() if size > 0 else 0
        if class_index == 0:         # the object is a class
            info["classes"] += 1
        elif class_index < 0 and size > 0 and name == "ScriptText" and imports[-class_index - 1] == "TextBuffer":
            text = Bytes(data, offset, endian)
            if names[text.compact()] == "None":   # end of the (empty) property list
                text.skip(8)                      # cursor position
                source = text.string(text.compact())
                info["script_lines"] += sum(1 for line in source.splitlines() if line.strip())
    info["status"] = "read"


# ##############################
# What a package is, for the report
# ##############################
UNREAL_ASSET_KINDS = [   # (start of the main asset's class name, asset kind)
    (("World",), "Scenes/levels"),
    (("Texture", "MediaTexture", "VolumeTexture"), "Textures/images"),
    (("StaticMesh", "SkeletalMesh", "Skeleton", "PhysicsAsset", "GeometryCollection", "DestructibleMesh"),
     "3D models"),
    (("Material", "PhysicalMaterial", "SubsurfaceProfile"), "Materials"),
    (("Anim", "BlendSpace", "AimOffset", "PoseAsset", "IKRig", "IKRetargeter"), "Animations"),
    (("Sound", "MetaSound", "Dialogue", "Reverb"), "Audio"),
    (("Niagara", "Particle"), "Visual effects"),
    (("DataTable", "CompositeDataTable", "CurveTable", "StringTable", "UserDefined", "Curve"), "Data tables"),
    (("BehaviorTree", "Blackboard", "EnvQuery", "StateTree"), "AI (behavior trees etc.)"),
    (("LevelSequence", "TemplateSequence"), "Cinematics"),
    (("Font",), "Fonts"),
]


def unreal_asset_kind(info, ext, rel):
    """What kind of asset a .uasset / .umap is, for the Assets section."""
    if "__externalactors__" in rel.lower() or "__externalobjects__" in rel.lower():
        return "Level actors (World Partition)"
    cls = info and info["main_class"]
    if not cls:
        if info and info["cooked"]:
            return "Unreal assets (cooked)"
        return "Scenes/levels" if ext == ".umap" else "Unreal assets (type unknown)"
    if cls.endswith(("Blueprint", "BlueprintGeneratedClass")):
        return "Blueprints"
    for prefixes, kind in UNREAL_ASSET_KINDS:
        if cls.startswith(prefixes):
            return kind
    return "Other Unreal assets"


GRAPH_ROWS = ["Blueprints", "Widget Blueprints (UI)", "Animation Blueprints", "Level Blueprints",
              "Kismet (UE3 levels)", "Materials", "Behavior trees (AI)",
              "Other node graphs (Niagara, sound, Control Rig ...)"]


def graph_rows(info):
    """[(row of the visual-scripting table, nodes)] for one package."""
    nodes = info["nodes"]
    if info["engine"] == "UE3":
        return [(row, nodes[kind]) for kind, row in (("kismet", "Kismet (UE3 levels)"), ("material", "Materials"))
                if nodes[kind]]
    cls, total = info["main_class"] or "", sum(nodes.values())
    if cls.endswith("WidgetBlueprint"):
        return [("Widget Blueprints (UI)", total)]
    if cls.endswith("AnimBlueprint"):
        return [("Animation Blueprints", total)]
    if cls.endswith("Blueprint"):   # data-only Blueprints count too, with 0 nodes
        return [("Blueprints", total)]
    if not total:
        return []
    if cls == "World":
        return [("Level Blueprints", total)]
    if cls.startswith("Material") or (not cls and nodes["material"] == total):
        return [("Materials", total)]
    if cls == "BehaviorTree":
        return [("Behavior trees (AI)", total)]
    if not cls and nodes["blueprint"]:
        return [("Blueprints", total)]
    return [("Other node graphs (Niagara, sound, Control Rig ...)", total)]


# #######################################
# Version control
# #######################################

# Version control: commits, merges, contributors and pull requests.

# ##############################
# Counting people
# ##############################
# Names shared by many people (build machines, defaults), never used to tie identities together.
GENERIC_NAMES = {"root", "admin", "administrator", "unknown", "user", "your name", "build", "builder",
                 "buildbot", "jenkins", "teamcity", "ci", "github", "gitlab", "dev", "developer", "default",
                 "(no author)", "no author", "none", "anonymous", "system", "unreal", "unity"}
COMMON_FIRST_NAMES = set("""
james john robert michael william david richard joseph thomas charles christopher daniel matthew anthony mark
donald steven paul andrew joshua kenneth kevin brian george timothy ronald edward jason jeffrey ryan jacob gary
nicholas eric jonathan stephen larry justin scott brandon benjamin samuel gregory alexander frank patrick
raymond jack dennis jerry tyler aaron henry adam douglas nathan peter zachary kyle walter harold jeremy ethan
carl keith roger gerald christian terry sean arthur austin noah lawrence jesse joe bryan billy jordan albert
dylan bruce willie gabriel alan juan logan wayne ralph roy eugene randy vincent russell louis philip bobby
johnny bradley mary patricia jennifer linda elizabeth barbara susan jessica sarah karen nancy lisa betty
margaret sandra ashley kimberly emily donna michelle dorothy carol amanda melissa deborah stephanie rebecca
sharon laura cynthia kathleen amy shirley angela helen anna brenda pamela nicole emma samantha katherine
christine debra rachel catherine carolyn janet ruth maria heather diane virginia julie joyce victoria olivia
kelly christina lauren joan evelyn judith megan cheryl andrea hannah martha jacqueline frances gloria ann
teresa kathryn sara janice jean alice madison doris abigail julia judy grace denise amber marilyn beverly
danielle theresa sophia marie diana brittany natalie isabella charlotte rose alexis kayla alex chris mike
dave matt steve tony andy dan nick tom sam ben max leo luca marco pablo carlos miguel jose luis javier diego
pedro jorge sergio andrea marco giulia sofia lucas mateo hugo louis pierre jean marie paul anna lena julia
felix lukas jonas leon finn elias noah emil anton oliver jakob tobias florian sebastian stefan markus andreas
thomas michael daniel martin simon david christian
""".split())


def identities(author):
    """The names and email addresses in an author string like "Jane Doe <jane@studio.com>"."""
    m = re.match(r"^\s*(.*?)\s*<([^>]*)>\s*$", author or "")
    return (m.group(1), m.group(2)) if m else (author or "",)


def count_people(authors):
    """How many people made the changes. Each author is a tuple of identities (name, email ...);
    identities seen together belong to one person, so someone who committed both as
    "Jane Doe <jane@home.net>" and as "Jane Doe <jane@studio.com>" counts once."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for ids in authors:
        linkable = linkable_identities(ids)
        for other in linkable[1:]:
            parent[find(other)] = find(linkable[0])
        for i in linkable[:1]:
            find(i)
    return len({find(x) for x in parent})


def linkable_identities(ids):
    """The identities of one change's author that may tie it to the same person's other changes."""
    ids = [i.strip().lower() for i in ids if i and i.strip()]
    # GitHub's privacy address (12345+jane@users.noreply.github.com) is the person's user name.
    ids += [m.group(1) for i in ids for m in [re.match(r"^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$", i)] if m]
    # Emails, full names and distinctive handles ("Hominghead") tie identities together; a lone
    # first name ("alex") or a shared default ("root", "Unity") doesn't.
    return [i for i in ids if i not in GENERIC_NAMES and ("@" in i or " " in i or len(ids) == 1 or (
        len(i) >= 5 and i not in COMMON_FIRST_NAMES))] or ids[:1]


def people_shares(authors):
    """How many changes each person made, busiest first (see count_people for who is one person)."""
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    keys = []
    for ids in authors:
        linkable = linkable_identities(ids)
        for other in linkable[1:]:
            parent[find(other)] = find(linkable[0])
        keys.append(linkable[0] if linkable else "")
        if linkable:
            find(linkable[0])
    return sorted(Counter(find(k) for k in keys if k).values(), reverse=True)


def contributors_across(histories):
    """How many people made the changes in all these histories together (say, a studio's several
    repositories), each person once however many repositories they worked in."""
    return count_people(a for h in histories for a in h.get("authors", ()))


# ##############################
# What commit messages name
# ##############################
# Pull requests named in merge and squash commit messages. GitHub and Bitbucket number them "#N",
# GitLab "!N" and Azure DevOps "PR N", each in its own sequence.
PR_IN_MESSAGE = [
    ("#", re.compile(r"^Merge pull request #(\d+)", re.M)),               # GitHub, Bitbucket Server
    ("#", re.compile(r"^Merged in \S+ \(pull request #(\d+)\)", re.M)),   # Bitbucket Cloud
    ("!", re.compile(r"See merge request \S*!(\d+)")),                    # GitLab
    ("PR", re.compile(r"^Merged PR (\d+):", re.M)),                       # Azure DevOps
]
PR_IN_SUBJECT = re.compile(r"\(#(\d+)\)\s*$")   # GitHub squash merges: "Fix the crash (#123)"
REVIEWS_IN_MESSAGE = {
    "Gerrit code reviews": re.compile(r"^Change-Id: (I[0-9a-f]{40})", re.M),
    "Phabricator code reviews": re.compile(r"^Differential Revision: \S*?D(\d+)", re.M),
    "Perforce Swarm code reviews": re.compile(r"#review-(\d+)"),
}
# History brought in from another system: what conversion tools write into each converted
# change's message. (label, pattern, the system it came from, the group naming the original change
# there or None). Each original change counts once.
IMPORTED_HISTORY = [
    ("Perforce changelists imported (git-p4)", re.compile(r"\[git-p4: depot-paths = .*?: change = (\d+)"), "Perforce", 1),
    ("Perforce changelists imported (p4-fusion)", re.compile(r"\[p4-fusion: depot-paths = .*?: change = (\d+)\]"),
     "Perforce", 1),
    ("Perforce changelists copied to Git by Git Fusion", re.compile(r"^Copied from Perforce[ \t]*\r?\n[ \t]*Change: (\d+)",
                                                                    re.M), "Perforce", 1),
    ("SVN revisions imported (git-svn)", re.compile(r"^git-svn-id: \S+?@(\d+)(?=\s|$)", re.M), "SVN", 1),
    ("SVN revisions imported (svn2git --add-metadata)", re.compile(r"^svn path=.*?; revision=(\d+)", re.M), "SVN", 1),
    ("TFS changesets imported (git-tfs)", re.compile(r"^git-tfs-id: .+?;C(\d+)[ \t]*\r?$", re.M), "Team Foundation (TFVC)", 1),
    ("Git commits pushed to Perforce through Git Fusion", re.compile(r"^Imported from Git[ \t]*\r?$(?:\n[ \t].*)*?\n[ \t]+sha1: "
                                                                     r"([0-9a-f]{40})", re.M), "Git", 1),
    ("SourceSafe check-ins converted to TFS (VSSConverter)", re.compile(
        r"\A\s*\{\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4} \d{1,2}[.:]\d\d(?:[.:]\d\d)?(?: ?[AaPp]\.?[Mm]\.?)?\}"), "Visual SourceSafe", None),
    ("SourceSafe file versions converted (VSSMigrate)", re.compile(r"\(vss \d+\)\s*\Z"), "Visual SourceSafe", None),
    ("commits made up by cvs2svn while converting from CVS", re.compile(
        r"^This commit was (?:manufactured|generated) by cvs2svn\b|^Standard project directories initialized by cvs2svn\.",
        re.M), "CVS", None),
    ("Mercurial changesets converted with hg-git", re.compile(r"^--HG--[ \t]*\r?$", re.M), "Mercurial", None),
    ("Bazaar revisions converted with Breezy (--BZR--)", re.compile(r"^--BZR--[ \t]*\r?$", re.M), "Bazaar", None),
    ("changes converted with reposurgeon (Legacy-ID)", re.compile(r"^Legacy-ID: (\S+)[ \t]*\r?$", re.M | re.I), None, 1),
]
# Lines conversion tools add, which aren't the change's own message, and what they put before it.
CONVERSION_LINE = re.compile(r"^(git-svn-id|git-tfs-id|git-tfs-work-item|legacy-id): |^\[(git-p4|p4-fusion): |^svn path=.*; revision="
                             r"|^--(HG|BZR)--$", re.I)
CONVERSION_PREFIX = re.compile(r"\A\s*\{\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4} [^}\n]{4,16}\}\s*")   # VSSConverter's date
CONVERSION_AFFIXES = re.compile(r"^\d+ - (?=.)|\s*\(vss \d+\)$")   # p4-fusion's changelist, VSSMigrate's file version
EMPTY_MESSAGES = {"", "*** empty log message ***", "(no message)", "no message", "no comment", "(no comment)",
                  "<no comment>", "none", "-", "."}


def message_key(message):
    """A change's message as converting it to another system leaves it: its first line of its own
    (without the lines and prefixes conversion tools add), in lower case, spaces collapsed. "" for
    a message that says nothing."""
    for line in CONVERSION_PREFIX.sub("", message, count=1).splitlines():
        line = line.strip()
        if line and not CONVERSION_LINE.match(line):
            break
    else:
        return ""
    key = " ".join(CONVERSION_AFFIXES.sub("", line).lower().split()).rstrip(".!")
    return "" if key in EMPTY_MESSAGES else key[:200]


# One change in a history, for telling the same change apart in another system's history (see
# across_systems). date: "YYYY-MM-DD", a year, or ""; id: its number or hash in its own system
# (SVN revision, Perforce changelist, Git commit ...) or None; key: message_key of its message;
# origins: ((system, number or None), ...) the change it was converted from, as markers name it;
# standard: whether forms count it (main branch, no merges or reverts), or None if unknown.
Change = namedtuple("Change", "date id key origins standard")


class MessageScan:
    """Pull requests, code reviews and imported history named in commit messages."""

    def __init__(self):
        self.prs, self.reviews, self.imported = defaultdict(set), defaultdict(set), defaultdict(set)
        self.reverts = self.merges = 0   # changes whose first line says so (forms leave both out)
        self.n = 0

    def add(self, message):
        """Notes what the message names. (message_key, origins, whether forms leave the change out
        for its message: a merge or a revert)."""
        self.n += 1
        subject = message.strip().split("\n", 1)[0]
        revert, merge = bool(re.search("revert", subject, re.I)), bool(re.match(r"merg(e|ed|ing)\b", subject, re.I))
        self.reverts += revert
        self.merges += merge
        self.prs["#"].update(PR_IN_SUBJECT.findall(subject))
        for numbering, pattern in PR_IN_MESSAGE:
            self.prs[numbering].update(pattern.findall(message))
        for label, pattern in REVIEWS_IN_MESSAGE.items():
            self.reviews[label].update(pattern.findall(message))
        origins = []
        for label, pattern, vcs, group in IMPORTED_HISTORY:
            m = pattern.search(message)
            if m:
                self.imported[label].update(pattern.findall(message) if group else [self.n])
                origins.append((vcs, m.group(group) if group else None))
        return message_key(message), tuple(origins), revert or merge

    def reviews_found(self):
        return ([("merged pull requests named in commit messages", sum(len(s) for s in self.prs.values()))]
                + [(label, len(s)) for label, s in self.reviews.items()])

    def imports_found(self):
        return [(label, len(s)) for label, s in self.imported.items() if s]


# ##############################
# Summing up a history
# ##############################

# When each system was first released: a change dated before then was converted from an earlier one.
SYSTEM_RELEASED = {"CVS": ("1986-07-01", "1986"), "Visual SourceSafe": ("1994-01-01", "1994"),
                   "Perforce": ("1995-01-01", "1995"), "SVN": ("2000-10-20", "October 2000"),
                   "Darcs": ("2003-03-03", "March 2003"), "Team Foundation (TFVC)": ("2004-01-01", "2004"),
                   "Bazaar": ("2005-03-26", "March 2005"), "Git": ("2005-04-07", "April 2005"),
                   "Mercurial": ("2005-04-19", "April 2005"), "Plastic SCM": ("2006-01-01", "2006"),
                   "Fossil": ("2007-07-21", "July 2007")}


def before(date, day):
    """Is date ("YYYY-MM-DD", or a year) before day ("YYYY-MM-DD")? A year only if it's an earlier year."""
    return bool(date) and (date[:4] < day[:4] if len(date) == 4 else date < day)


def dated_before_row(vcs, dates):
    """The report row for changes dated before their system existed, or None."""
    day, when = SYSTEM_RELEASED.get(vcs, (None, None))
    n = sum(1 for d in dates if before(d, day)) if day else 0
    return (f"dated before {vcs} existed ({when}): converted from an earlier system", n) if n else None


def history(vcs, unit, changes, merges=None, reviews=(), notes=(), scan=None, records=None):
    """A version-control history for the report. changes: [(date "YYYY-MM-DD" or year, author)], the
    author being a tuple of identities (see count_people) or a plain name. scan: the MessageScan of
    their messages, for the changes forms count (without merges or reverts; a system that doesn't
    record merges has the ones its messages name left out), and the history they say was imported.
    records: a Change for each of changes, in the same order, for matching them in other systems."""
    dates = sorted(d for d, _ in changes if d)
    authors = [a if isinstance(a, tuple) else (a,) for _, a in changes]
    shares = people_shares(authors)
    rows = [(unit, len(changes))]
    if merges is not None:
        rows.append(("merge commits", merges))
    rows += [("contributors", len(shares)),
             ("first change", dates[0] if dates else "?"), ("last change", dates[-1] if dates else "?")]
    if len(shares) > 1:
        rows.append(("  the busiest person's share of them", f"{100 * shares[0] // len(changes)}%"))
    per_year = Counter(d[:4] for d in dates if re.match(r"\d{4}", d))
    # "authors" stays in memory, to count people across repositories; reports never name anyone
    standard = None if scan is None else max(0, len(changes) - (scan.merges if merges is None else merges) - scan.reverts)
    if scan is not None and vcs != "Git":   # Git adds these after rows of its own
        rows += scan.imports_found()
        rows += [r for r in [dated_before_row(vcs, dates)] if r]
    return {"vcs": vcs, "unit": unit, "rows": rows, "reviews": [(label, n) for label, n in reviews if n],
            "notes": list(notes), "per_year": dict(sorted(per_year.items())), "dates": dates,
            "authors": sorted(set(authors)), "standard_commits": standard,
            "records": records or [Change(d, None, "", (), None) for d, _ in changes]}


# ##############################
# Git
# ##############################

# ####################
# Reading the history
# ####################
GIT_READ_SIZE = 1 << 20


def git_log(root, extra):
    """Yields (hash, date, name, email, parents, message) for every commit, as git produces them: a
    fork of Unreal Engine has hundreds of thousands of commits, too many to hold in memory at once.
    Names and emails go through the repository's .mailmap, if it has one."""
    args = command(["git", "log", "--all", "--date=short", "--format=%x1e%H%x1f%ad%x1f%aN%x1f%aE%x1f%P%x1f%B",
                    *extra])
    if args is None:
        return
    try:
        proc = subprocess.Popen(args, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                stdin=subprocess.DEVNULL, env=quiet_env())
    except OSError:
        return
    pending = b""
    try:
        for chunk in iter(lambda: proc.stdout.read(GIT_READ_SIZE), b""):
            *records, pending = (pending + chunk).split(b"\x1e")
            for record in records:
                if record:
                    yield (record.decode("utf-8", "replace").split("\x1f", 5) + [""] * 5)[:6]
        if pending:
            yield (pending.decode("utf-8", "replace").split("\x1f", 5) + [""] * 5)[:6]
    finally:
        proc.stdout.close()
        proc.wait()


def git_top(path):
    top = (run(["git", "rev-parse", "--show-toplevel"], path, 60) or "").strip()
    return os.path.normcase(os.path.abspath(top)) if top else None


def git_history(root):
    if run(["git", "rev-parse", "--is-inside-work-tree"], root, 60) is None:
        return None
    top = (run(["git", "rev-parse", "--show-toplevel"], root, 60) or "").strip()
    try:
        whole_repo = bool(top) and os.path.samefile(top, root)
    except OSError:
        whole_repo = False

    # ####################
    # Commits
    # ####################
    # In a subfolder of a repository, only the commits that touched it. --full-history keeps the
    # merge commits that brought changes into it (by default git hides them).
    limit = [] if whole_repo else ["--full-history", "--", "."]
    # Commits on the main branch (whatever is checked out), as opposed to all branches.
    on_main = set((run(["git", "rev-list", "HEAD", *limit], root) or "").split())
    changes, records, merges, epic_commits, main_commits, vss_messages = [], [], 0, 0, 0, 0
    scan = MessageScan()
    for sha, date, name, email, parents, body in git_log(root, limit):
        progress(f"Reading the Git history of {os.path.basename(root)}: {len(changes) + epic_commits:,} commits")
        if EPIC_COMMIT.search(body) or EPIC_EMAIL.search(email):   # Epic's own history, in an engine fork
            epic_commits += 1
            continue
        changes.append((date, (name, email)))
        main_commits += sha in on_main
        if len(parents.split()) > 1:
            merges += 1
        key, origins, _ = scan.add(body)
        records.append(Change(date, sha, key, origins, None))
        vss_messages += bool(VSS_IN_MESSAGE.search(body))
    progress()
    if not changes and not epic_commits:
        return None

    # ####################
    # Pull requests and code reviews
    # ####################
    found = scan.reviews_found()
    unreachable = []
    if OFFLINE:
        if git_remotes(root):
            left_out_offline("pull requests on the Git server (asked with git ls-remote and GitHub's gh)")
    else:
        for remote, count in git_server_pull_requests(root, unreachable):
            found.append((f"all pull requests on {remote} (open, closed, merged)", count))
        for remote, count in github_merged_pull_requests(root):
            found.append((f"merged pull requests on GitHub ({remote})", count))
    for remote in unreachable:
        found.append((f"pull requests on {remote}", "couldn't connect"))

    # ####################
    # The history
    # ####################
    notes = []
    if (run(["git", "rev-parse", "--is-shallow-repository"], root, 60) or "").strip() == "true":
        notes.append("This is a shallow clone: older history is missing. Run \"git fetch --unshallow\" first.")
    standard = git_standard_commits(root, [] if whole_repo else ["--", "."])
    counted = standard[2] if standard else None
    records = [r._replace(standard=None if counted is None else r.id in counted) for r in records]
    h = history("Git", "commits by the studio (not Epic's)" if epic_commits else "commits", changes, merges, found,
                notes, records=records)
    h["standard_commits"], h["standard_branch"] = standard[:2] if standard else (None, None)
    h["rows"].insert(1, ("  of which on the main branch (the one checked out)", main_commits))
    h["rows"] += scan.imports_found() + git_conversion_traces(root)
    h["vss_messages"] = vss_messages

    # ####################
    # History from elsewhere: earlier systems, Epic's engine
    # ####################
    h["rows"] += [r for r in [dated_before_row("Git", h["dates"])] if r]
    if epic_commits:
        h["rows"].insert(0, ("commits from Epic (Unreal Engine's own history)", epic_commits))
        h["rows"] += changes_to_epic_code(root, [] if whole_repo else ["--", "."])
    elif is_engine_repository(root) or is_engine_repository(top or root):
        h["rows"] += engine_changes_without_epic_history(root, [] if whole_repo else ["--", "."])
    return h


# ####################
# History converted from other systems, as Git keeps it
# ####################
# What conversion tools leave in a repository besides the commit messages (IMPORTED_HISTORY):
# refs, and files in the .git folder. (ref pattern or file, row label)
GIT_CONVERSION_REFS = [
    ("refs/svn/map", "SVN history converted by SubGit (its refs/svn/map)"),
    ("refs/tags/TFS_C*", "TFS changesets imported (git-tf's TFS_C tags)"),
    ("refs/cl/", "Perforce changelists imported (p4-fusion's refs/cl)"),
    ("refs/notes/hg", "Mercurial history converted (git-remote-hg or hg-fast-export: refs/notes/hg)"),
    ("refs/cinnabar/", "Mercurial history converted by git-cinnabar"),
]
GIT_CONVERSION_FILES = [
    ("svn", "SVN history imported with git-svn (its .git/svn folder)"),
    ("git-tf", "TFS history imported with git-tf (its .git/git-tf)"),
    ("hg2git-mapping", "Mercurial history converted by hg-fast-export (its .git/hg2git-mapping)"),
    ("cvs-revisions", "CVS history imported with git cvsimport (its .git/cvs-revisions)"),
]


def git_conversion_traces(root):
    """Report rows for the traces conversion tools left outside the commit messages: how many refs
    they made (one per original change, for tags and refs/cl), or "found"."""
    import fnmatch
    refs = (run(["git", "for-each-ref", "--format=%(refname)", *(p.rstrip("/") for p, _ in GIT_CONVERSION_REFS)],
                root, 120) or "").split()
    rows = []
    for pattern, label in GIT_CONVERSION_REFS:
        n = sum(1 for ref in refs if fnmatch.fnmatchcase(ref, pattern) or (pattern.endswith("/") and ref.startswith(pattern))
                or ref == pattern)
        if n:
            rows.append((label, n if pattern.endswith(("*", "/cl/")) else "found"))
    git_dir = (run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root, 60)   # Git 2.31 and later
               or run(["git", "rev-parse", "--absolute-git-dir"], root, 60) or "").strip()
    if git_dir:
        rows += [(label, "found") for name, label in GIT_CONVERSION_FILES if os.path.exists(os.path.join(git_dir, name))]
    return rows


# ####################
# Forks of Unreal Engine
# ####################
# Every commit in Epic's Unreal Engine repository ends like "[CL 16428889 by george rolfe in
# ue5-main branch]". A studio's engine fork carries all of them, alongside its own changes.
EPIC_COMMIT = re.compile(r"\[CL (\d+) by [^\]\n]+ in ([^\]\n]+) branch\]")
EPIC_EMAIL = re.compile(r"@epicgames\.(com|net)$", re.I)
EPIC_REMOTE = re.compile(r"epicgames/unrealengine", re.I)
EPIC_GREP = r"\[CL [0-9]+ by .* branch\]"   # EPIC_COMMIT, for git log --grep -E


def is_engine_repository(root):
    """Is this (part of) a source copy of Unreal Engine 4 or 5?"""
    return bool(find_path(root, "Engine", "Build", "Build.version") or find_path(root, "Build", "Build.version"))


BULK_IMPORT_FILES, BULK_IMPORT_LINES = 3000, 300_000


def engine_changes_without_epic_history(root, pathspec):
    """An engine repository that starts from a copy of Epic's source rather than Epic's history: what
    the studio's commits changed, leaving out the bulk commits that brought in (new versions of)
    Epic's code. Unlike the comparison with Epic's commit, this adds up every change, including
    ones later changed again."""
    progress(f"Measuring the engine changes in {os.path.basename(root)} ...")
    branch = studio_branch(root)
    out = run(["git", "log", "--no-merges", *GIT_NO_PROGRAMS, "--format=%x1e", "--shortstat", branch,
               *(pathspec or ["--"])], root, 3600)
    progress()
    if out is None:
        return []
    imports = files = added = removed = 0
    for record in out.split("\x1e")[1:]:
        n = {what: int(v) for v, what in re.findall(r"(\d+) (file|insertion|deletion)", record)}
        if n.get("file", 0) >= BULK_IMPORT_FILES or n.get("insertion", 0) >= BULK_IMPORT_LINES:
            imports += 1
            continue
        files += n.get("file", 0)
        added += n.get("insertion", 0)
        removed += n.get("deletion", 0)
    return [("no Epic history: changes in the studio's commits", f"{plural(imports, 'bulk import')} left out"),
            ("  in branch", branch),
            ("  files changed (summed over commits)", files),
            ("  lines added", added),
            ("  lines removed", removed)]


def studio_branch(root):
    """The local branch with the most of the studio's own commits (not Epic's), where its engine work
    is, even if another branch (say, Epic's release branch) happens to be checked out."""
    heads = (run(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"], root, 60) or "").split()
    best, most = "HEAD", -1
    for ref in ["HEAD"] + heads[:30]:
        n = (run(["git", "rev-list", "--count", "--invert-grep", "-E", "--grep", EPIC_GREP, ref], root, 600) or "").strip()
        if n.isdigit() and int(n) > most:
            best, most = ref, int(n)
    if best == "HEAD":
        best = (run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root, 60) or "HEAD").strip()
    return best


def changes_to_epic_code(root, pathspec):
    """How much a fork of Unreal Engine changed Epic's code: the difference between the newest Epic
    commit in the studio's branch and that branch."""
    progress(f"Comparing {os.path.basename(root)} with Epic's code ...")
    branch = studio_branch(root)
    base = run(["git", "log", "-1", "--format=%H%x1f%B", "-E", "--grep", EPIC_GREP, branch, "--"], root)
    if not base or "\x1f" not in base:
        progress()
        return []
    sha, body = base.split("\x1f", 1)
    stat = run(["git", "diff", *GIT_NO_PROGRAMS, "--shortstat", sha.strip(), branch, *(pathspec or ["--"])], root) or ""
    progress()
    numbers = {}
    for n, what in re.findall(r"(\d+) (file|insertion|deletion)", stat):
        numbers[what] = int(n)
    cl = EPIC_COMMIT.search(body)
    return [("changes to Epic's code (vs. Epic's newest commit)", f"CL {cl.group(1)}" if cl else "?"),
            ("  in branch", branch),
            ("  files changed", numbers.get("file", 0)),
            ("  lines added", numbers.get("insertion", 0)),
            ("  lines removed", numbers.get("deletion", 0))]


# ####################
# Pull requests on the server
# ####################

def git_remotes(root):
    """[(remote, url)], leaving out Epic's own repository: its pull requests aren't the studio's."""
    out = []
    for remote in (run(["git", "remote"], root, 60) or "").split():
        url = (run(["git", "remote", "get-url", remote], root, 60) or "").strip()
        if not EPIC_REMOTE.search(url):
            out.append((remote, url))
    return out


GIT_REMOTE_PROTOCOLS = "https:http:ssh:git:file"   # file: a repository in a folder on this computer


def remote_on_network_share(url):
    """Is this remote a repository in a folder on another computer (\\\\server\\share\\game.git,
    file://server/...)? Such a remote keeps no pull requests (hosting services do), and opening it
    would connect to whatever computer the repository's settings name."""
    return is_network_path(url) or bool(re.match(r"(?i)^file://(?!/)", url))


def ls_remote(root, url, *patterns, options=(), login=True, timeout=180):
    """git ls-remote's output for the repository at url, or None. Run outside the repository (as if
    it weren't one: GIT_DIR names nothing), so that only the user's own git settings apply, never the
    repository's, which could run a program or turn off certificate checks. Relative paths start from
    the repository's top folder. login=False: ask as anyone would, without the user's logins. Only
    git's own transports may be used (GIT_REMOTE_PROTOCOLS), not a helper program a URL could name."""
    if OFFLINE:
        return None
    top = git_top(root) or root
    return run(["git", "ls-remote", *options, "--", url, *patterns], top, timeout, logins=login,
               env={"GIT_DIR": os.devnull, "GIT_ALLOW_PROTOCOL": GIT_REMOTE_PROTOCOLS,
                    **({} if login else {"GIT_ASKPASS": ""})})


def git_server_pull_requests(root, unreachable=None):
    """[(remote, number of pull requests)]. GitHub, GitLab and Bitbucket Server keep a ref for every
    pull request ever opened (refs/pull/N/..., refs/merge-requests/N/..., refs/pull-requests/N/...).
    Remotes that can't be reached (say, they need a login we don't have) are added to `unreachable`."""
    found = []
    for remote, url in git_remotes(root):
        if remote_on_network_share(url):
            continue
        progress(f"Asking {remote} for its pull requests ...")
        refs = ls_remote(root, url, "refs/pull/*", "refs/merge-requests/*", "refs/pull-requests/*") if url else None
        progress()
        if refs is None and unreachable is not None:
            unreachable.append(remote)
        numbers = set(re.findall(r"refs/(?:pull|merge-requests|pull-requests)/(\d+)/", refs or ""))
        if numbers:
            found.append((remote, len(numbers)))
    return found


def github_merged_pull_requests(root):
    """[(remote, merged pull requests)] for GitHub remotes, asked through GitHub's own command-line
    tool (gh), if it's installed and logged in."""
    found = []
    for remote, url in ([] if OFFLINE else git_remotes(root)):
        m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
        if not m:
            continue
        # Run from the temporary folder, not the repository, so that gh has no repository to read.
        import tempfile
        out = run(["gh", "api", "-X", "GET", "search/issues", "-f", f"q=repo:{m.group(1)}/{m.group(2)} is:pr is:merged",
                   "--jq", ".total_count"], tempfile.gettempdir(), 60)
        if out and out.strip().isdigit():
            found.append((remote, int(out.strip())))
    return found


# ####################
# Commits on the main branch, as forms count them
# ####################

def git_default_branch(root):
    """The repository's main branch: the one origin's HEAD names, else main, master, trunk or develop,
    else whatever is checked out."""
    head = (run(["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], root, 60) or "").strip()
    names = [head[len("refs/remotes/origin/"):]] if head.startswith("refs/remotes/origin/") else []
    for name in names + ["main", "master", "trunk", "develop"]:
        for ref in (f"refs/heads/{name}", f"refs/remotes/origin/{name}"):
            if run(["git", "rev-parse", "--verify", "--quiet", ref + "^{commit}"], root, 60) is not None:
                return ref
    return "HEAD"


def git_standard_commits(root, pathspec):
    """(commits, branch, {their hashes}): forms' "git log --oneline --no-merges | grep -v -i revert |
    wc -l" on the main branch, leaving out Epic's own commits in a fork of Unreal Engine. None if git
    fails."""
    ref = git_default_branch(root)
    out = run(["git", "log", "--no-merges", "--invert-grep", "-E", "--grep", EPIC_GREP, "--format=%H%x1f%ae%x1f%s", ref,
               *(pathspec or ["--"])], root, 3600)
    if out is None:
        return None
    counted = {fields[0] for fields in (line.split("\x1f", 2) for line in out.splitlines())
               if len(fields) == 3 and not EPIC_EMAIL.search(fields[1]) and not re.search("revert", fields[2], re.I)}
    if ref == "HEAD":   # no main branch: the one checked out
        return len(counted), (run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root, 60) or "HEAD").strip(), counted
    return len(counted), re.sub(r"^refs/(heads|remotes)/", "", ref), counted


# ##############################
# Other version-control systems
# ##############################

def perforce_history(root):
    """Submitted changelists under this folder, if it's in a Perforce workspace and p4 is logged in."""
    path = os.path.join(root, "...")
    if perforce_port_starts_a_program(root):
        return None
    if not (run(["p4", "changes", "-m", "1", "-s", "submitted", path], root, 20) or "").startswith("Change "):
        return None
    out = run(["p4", "changes", "-l", "-s", "submitted", path], root) or ""
    changes, records, scan = [], [], MessageScan()
    # "Change 123 on 2020/01/02 by jane@workspace", then the full description, indented by a tab.
    for block in re.split(r"^(?=Change \d+ on )", out, flags=re.M):
        m = re.match(r"Change (\d+) on (\d{4}/\d\d/\d\d) by ([^@\s]+)@\S*(.*)", block, re.S)
        if m:
            date = m.group(2).replace("/", "-")
            changes.append((date, m.group(3)))
            key, origins, left_out = scan.add(re.sub(r"^\t", "", m.group(4), flags=re.M))
            records.append(Change(date, m.group(1), key, origins, not left_out))
    return history("Perforce", "submitted changelists", changes, reviews=scan.reviews_found(), scan=scan,
                   records=records) if changes else None


def svn_history(root):
    """Revisions of the checked-out path, up to the newest on the server: by default svn log stops at
    the revision the checkout was last updated to. Decades of history take a while to fetch."""
    out = run(["svn", "log", "--xml", "--non-interactive", "-r", "HEAD:1", root], root, 7200)
    if not out:   # say, the path is gone at HEAD: the history as far as this checkout goes
        out = run(["svn", "log", "--xml", "--non-interactive", root], root, 7200)
    if not out:
        return None
    import xml.etree.ElementTree as ET
    try:
        entries = ET.fromstring(out).iter("logentry")
        changes, records, scan = [], [], MessageScan()
        for e in entries:
            date = (e.findtext("date") or "")[:10]
            changes.append((date, e.findtext("author") or "(no author)"))
            key, origins, left_out = scan.add(e.findtext("msg") or "")
            records.append(Change(date, e.get("revision"), key, origins, not left_out))
    except ET.ParseError:
        return None
    if not changes:
        return None
    h = history("SVN", "revisions", changes, reviews=scan.reviews_found(), scan=scan, records=records)
    # Which path was counted: forms count trunk's revisions, not those of every branch.
    path = (run(["svn", "info", "--show-item", "relative-url", "--non-interactive", root], root, 120) or "").strip()
    if path.startswith("^/"):
        h["standard_branch"] = path
        if not re.search(r"(^|/)trunk(/|$)", path, re.I):
            h["notes"].append(f"Counted the revisions of {path}, not of a trunk: if that includes branches, run this"
                              " on a checkout of trunk for the count of trunk's revisions.")
    return h


HG_SKIPS_REPOSITORY_SETTINGS = (5, 4)   # the first Mercurial that obeys HGRCSKIPREPO (see quiet_env) everywhere


def hg_skips_repository_settings():
    """Is this Mercurial new enough to ignore a repository's own settings (.hg/hgrc), whose hooks and
    extensions could run programs? Older ones read them whatever HGRCSKIPREPO says. Asked from the
    temporary folder, where no repository's settings apply."""
    import tempfile
    m = re.search(r"version (\d+)\.(\d+)", run(["hg", "version", "-q"], tempfile.gettempdir(), 60) or "")
    return bool(m) and (int(m.group(1)), int(m.group(2))) >= HG_SKIPS_REPOSITORY_SETTINGS


def hg_converted_from(extras):
    """(system, its number for the change) that hg convert or hg-git recorded in a changeset's
    extras, or None. hg convert's convert_revision: "svn:<uuid><path>@<revision>" from SVN, the
    commit hash from Git, the changelist from Perforce (also in "p4"), a revision id from Bazaar."""
    rev = extras.get("convert_revision", "")
    if extras.get("p4"):
        return "Perforce", extras["p4"]
    if rev.startswith("svn:"):
        m = re.search(r"@(\d+)$", rev)
        return "SVN", m.group(1) if m else None
    if re.fullmatch(r"[0-9a-f]{40}", rev):
        return "Git", rev
    if rev:
        return None, rev
    if extras.get("hg-git-rename-source") == "git":   # hg-git, pulling from Git
        return "Git", None
    return None


def hg_history(root):
    if not hg_skips_repository_settings():
        return None
    out = run(["hg", "log", "--template", "{node}\\x1f{date|shortdate}\\x1f{author|person}\\x1f{author|email}\\x1f"
               "{p2rev}\\x1f{extras % '{key}={value}\\x1d'}\\x1f{desc}\\x1e", "."], root)
    # hg-git keeps the Git commit each changeset is: "<git hash> <hg hash>" lines.
    git_of = {}
    try:
        with open(os.path.join(nearest(root, ".hg") or "", "git-mapfile"), encoding="ascii", errors="replace") as f:
            git_of = {hg: git for git, hg in (line.split() for line in f if len(line.split()) == 2)}
    except OSError:
        pass
    changes, records, merges, converted, scan = [], [], 0, Counter(), MessageScan()
    for record in (out or "").split("\x1e"):
        fields = record.split("\x1f", 6)
        if len(fields) == 7:
            node, date, name, email, p2, extras, desc = fields
            node, date = node.strip(), date.strip()
            changes.append((date, (name, email)))
            merges += p2.strip() != "-1"
            key, origins, left_out = scan.add(desc)
            source = hg_converted_from(dict(e.split("=", 1) for e in extras.split("\x1d") if "=" in e))
            if source:
                converted[source[0] or "another system"] += 1
            origins += tuple(o for o in [source, ("Git", git_of[node]) if node in git_of else None] if o)
            records.append(Change(date, node, key, origins, not left_out and p2.strip() == "-1"))
    if not changes:
        return None
    h = history("Mercurial", "commits", changes, merges, scan.reviews_found(), scan=scan, records=records)
    h["rows"] += [(f"changesets converted from {vcs} (hg convert or hg-git)", n) for vcs, n in sorted(converted.items())]
    if git_of:
        h["rows"].append(("changesets also in Git (hg-git's .hg/git-mapfile)", sum(1 for r in records if r.id in git_of)))
    return h


def bzr_history(root):
    """Bazaar, through Breezy (brz) or the original bzr. Revision ids name the change a revision
    was converted from: "svn-v4:<uuid>:<path>:<revision>" (bzr-svn), "git-v1:<hash>" (brz git)."""
    out = run(["brz", "log", "--long", "--show-ids", "-n0", "."], root)
    if out is None:
        out = run(["bzr", "log", "--long", "--show-ids", "-n0", "."], root)
    changes, records, converted, scan = [], [], Counter(), MessageScan()
    for block in re.split(r"^\s*-{20,}\s*$", out or "", flags=re.M):
        if not re.search(r"^\s*revno:", block, re.M):
            continue
        who = re.search(r"^\s*authors?:\s*(.+)$", block, re.M) or re.search(r"^\s*committer:\s*(.+)$", block, re.M)
        when = re.search(r"^\s*timestamp:\s*\w+ (\d{4}-\d\d-\d\d)", block, re.M)
        revid = re.search(r"^\s*revision-id:\s*(\S+)", block, re.M)
        date = when.group(1) if when else ""
        changes.append((date, identities(who.group(1).split(",")[0]) if who else ("",)))
        key, origins, left_out = scan.add(block.split("message:", 1)[-1])
        svn = re.match(r"svn-v\d+(?:-\w+)?:[^:]*:.*:(\d+)$", revid.group(1)) if revid else None
        git = re.match(r"git-v\d+:([0-9a-f]{40})$", revid.group(1)) if revid else None
        if svn or git:
            converted["SVN" if svn else "Git"] += 1
            origins += (("SVN", svn.group(1)) if svn else ("Git", git.group(1)),)
        records.append(Change(date, revid.group(1) if revid else None, key, origins, not left_out))
    if not changes:
        return None
    h = history("Bazaar", "revisions", changes, reviews=scan.reviews_found(), scan=scan, records=records)
    h["rows"] += [(f"revisions converted from {vcs} (their revision ids say so)", n) for vcs, n in sorted(converted.items())]
    return h


def darcs_history(root):
    # At the repository's root, "." would match nothing; darcs may print a notice before the XML.
    here = [] if os.path.isdir(os.path.join(root, "_darcs")) else ["."]
    # Its settings (_darcs/prefs/defaults) can name hooks: programs to run with any command.
    out = run(["darcs", "log", "--xml-output", "--no-prehook", "--no-posthook", *here], root)
    if not out or "<changelog" not in out:
        return None
    import xml.etree.ElementTree as ET
    try:
        patches = list(ET.fromstring(out[out.index("<changelog"):]).iter("patch"))
    except ET.ParseError:
        return None
    changes, records, scan = [], [], MessageScan()
    for p in patches:
        d = p.get("date", "")
        date = f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) >= 8 else ""
        changes.append((date, identities(p.get("author", ""))))
        key, origins, left_out = scan.add((p.findtext("name") or "") + "\n" + (p.findtext("comment") or ""))
        records.append(Change(date, p.get("hash"), key, origins, not left_out))
    return history("Darcs", "patches", changes, reviews=scan.reviews_found(), scan=scan,
                   records=records) if changes else None


def fossil_history(root):
    out = run(["fossil", "timeline", "-n", "0", "-t", "ci", "-W", "0", "-p", ".", "-F", "%H|%a|%d|%c"], root)
    changes, records, scan = [], [], MessageScan()
    for line in (out or "").splitlines():
        fields = line.split("|", 3)
        if len(fields) == 4 and re.fullmatch(r"[0-9a-f]{20,}", fields[0]) and fields[3] != "initial empty check-in":
            changes.append((fields[2][:10], fields[1]))
            key, origins, left_out = scan.add(fields[3])
            records.append(Change(fields[2][:10], fields[0], key, origins, not left_out))
    if not changes:
        return None
    h = history("Fossil", "check-ins", changes, reviews=scan.reviews_found(), scan=scan, records=records)
    # fossil import --svn tags each check-in with its SVN revision (--rev-tags, implied by -i).
    svn_tags = sum(1 for tag in (run(["fossil", "tag", "list"], root, 120) or "").split() if re.fullmatch(r"svn-rev-\d+", tag))
    if svn_tags:
        h["rows"].append(("SVN revisions imported (fossil import's svn-rev tags)", svn_tags))
    return h


def cvs_history(root):
    """CVS keeps a history per file; a commit is the file revisions sharing a commit id (or, from
    before CVS had them, the same author, minute and message)."""
    if cvs_root_starts_a_program(cvs_root(root)):
        return None
    out = run(["cvs", "-q", "log"], root)
    commits = {}
    for m in re.finditer(r"^revision [\d.]+\n(date: (\d{4}[-/]\d\d[-/]\d\d) (\d\d:\d\d)[^\n]*?author: ([^;]+);[^\n]*)\n"
                         r"(?:branches:[^\n]*\n)?(.*?)(?=^-{28}$|^={77}$)", out or "", re.M | re.S):
        info, date, minute, author, message = m.groups()
        cid = re.search(r"commitid: (\w+)", info)
        key = cid.group(1) if cid else (author, date, minute, message.strip())
        commits[key] = (date.replace("/", "-"), author.strip(), message)
    scan, records = MessageScan(), []
    for date, _, message in commits.values():
        key, origins, left_out = scan.add(message)
        records.append(Change(date, None, key, origins, not left_out))
    changes = [(date, author) for date, author, _ in commits.values()]
    return history("CVS", "commits", changes, reviews=scan.reviews_found(), scan=scan,
                   records=records) if changes else None


def tfvc_history(root):
    """Team Foundation Version Control (Azure DevOps / TFS), through Visual Studio's tf command. The
    brief format cuts comments short, so they're read for what conversion tools put at their start
    (SourceSafe's dates, from VSSConverter), not matched with other systems' messages."""
    flag = "/" if os.name == "nt" else "-"
    out = run(["tf", "history", ".", f"{flag}recursive", f"{flag}noprompt", f"{flag}format:brief"], root)
    changes, records, scan = [], [], MessageScan()
    for line in (out or "").splitlines():
        m = re.match(r"^\s*(\d+)\s+(.+?)\s{2,}(\S+)(?:\s+(.*))?$", line)   # changeset, user, date (in the local format), comment
        if m:
            year = re.search(r"\d{4}", m.group(3))
            changes.append((year.group(0) if year else "", m.group(2).strip()))
            _, origins, _ = scan.add(m.group(4) or "")
            records.append(Change(changes[-1][0], m.group(1), "", origins, None))
    if not changes:
        return None
    h = history("Team Foundation (TFVC)", "changesets", changes, records=records)
    h["rows"] += scan.imports_found() + [r for r in [dated_before_row(h["vcs"], h["dates"])] if r]
    return h


def cm_find(root, query, fields, dated=False):
    """Records of cm find (Plastic SCM): [[field, ...]] for each object, or None if cm fails. Fields
    are split by control characters, as comments can hold any other character. With dated, dates
    come in ISO form (--dateformat=o), not in the computer's own format, unless this cm is too old
    to take the option."""
    fmt = "--format=" + "\x1f".join("{%s}" % f for f in fields) + "\x1e"
    out = None
    if dated:
        out = run(["cm", "find", *query, fmt, "--dateformat=o", "--nototal", "--encoding=utf-8"], root)
    if out is None:
        out = run(["cm", "find", *query, fmt, "--nototal"], root)
    if out is None:
        return None
    records = (r.lstrip("\r\n").split("\x1f", len(fields) - 1) for r in out.split("\x1e"))
    return [r for r in records if len(r) == len(fields)]


def plastic_date(text):
    """A date as cm find prints it: "YYYY-MM-DD" from its ISO form; otherwise (the computer's own
    format, so day and month may be either way round) only the year."""
    text = text.strip()
    if re.match(r"\d{4}-\d\d-\d\d", text):
        return text[:10]
    return (re.findall(r"\d{4}", text) or [""])[0]


def plastic_history(root):
    """Plastic SCM (Unity Version Control): the changesets of the workspace's repository (all its
    branches), its merges, and its code reviews (Plastic's pull requests). cm asks the server."""
    found = cm_find(root, ["changeset"], ["changesetid", "date", "owner", "branch", "comment"], dated=True)
    if not found:
        return None
    # Changeset 0 is the empty one every repository starts with.
    found = [r for r in found if r[0].strip() != "0"]
    if not found:
        return None
    merged_into = cm_find(root, ["merge", "where type = 'merge'"], ["dstchangeset"])   # cherry-picks aren't merges
    merge_ids = {m.group(0) for m in (re.search(r"\d+", r[0]) for r in merged_into or []) if m}
    changes, records, scan = [], [], MessageScan()
    on_main = 0
    for cid, date, owner, branch, comment in found:
        cid, date, branch = cid.strip(), plastic_date(date), branch.strip()
        changes.append((date, owner.strip()))
        key, origins, left_out = scan.add(comment)
        merge = cid in merge_ids
        main = branch == "/main"
        records.append(Change(date, cid, key, origins, main and not merge and not left_out))
        on_main += main
    reviews = run(["cm", "find", "review", "--format={id}", "--nototal"], root)
    review_count = len([line for line in (reviews or "").splitlines() if line.strip()])
    h = history("Plastic SCM", "changesets", changes, len(merge_ids & {r.id for r in records}) if merged_into is not None
                else None, reviews=[("Plastic code reviews", review_count)] + scan.reviews_found(), scan=scan,
                records=records)
    if on_main:   # forms count the main branch's changesets
        h["rows"].insert(1, ("  of which on the main branch (/main)", on_main))
        h["standard_commits"], h["standard_branch"] = sum(1 for r in records if r.standard), "/main"
    return h


# ####################
# Where their history comes from
# ####################
# Most of these systems keep the history on the computer; a few ask their server for it. A copied
# folder's settings name that server, and two of them can name a program to start instead: a CVS
# root can set CVS_RSH (":ext;CVS_RSH=...:"), or pass ssh an option as a host name ("-oProxyCommand=..."),
# and a Perforce P4PORT of "rsh:..." starts a command. Neither is used unless the user set it.

def cvs_root(root):
    """The CVS root (where the repository is) recorded in this checkout, or ""."""
    try:
        with open(nearest(root, os.path.join("CVS", "Root")) or "", encoding="latin-1") as f:
            return f.readline().strip()
    except OSError:
        return ""


def cvs_root_starts_a_program(cvsroot):
    return bool(re.match(r"^:[^:]*;", cvsroot) or re.match(r"^(:[^:]*:)?([^@:/\\]*@)?-", cvsroot))


def perforce_port_starts_a_program(root):
    """Is p4 set (by a settings file in the folder, P4CONFIG, or the registry, not by the user's own
    P4PORT variable) to start a program, "rsh:<command>"? p4 set reads the settings without asking
    the server."""
    out = run(["p4", "set", "-q", "P4PORT"], root, 20) or ""
    port = next((line.split("=", 1)[1].strip() for line in out.splitlines() if line.upper().startswith("P4PORT=")), "")
    return port.lower().startswith("rsh:") and port != os.environ.get("P4PORT", "").strip()


def history_from_server(name, root):
    """Would reading this system's history here connect to its server? Plastic SCM and TFVC always
    ask theirs; SVN does unless its repository is a folder on this computer (file://); CVS unless
    its root is local; Bazaar when this is a lightweight checkout of a branch elsewhere. The others
    hold their whole history in the working copy."""
    if name in ("Plastic SCM", "Team Foundation (TFVC)"):
        return True
    if name == "SVN":
        url = run(["svn", "info", "--show-item", "repos-root-url", "--non-interactive", root], root, 60) or ""
        return not url.strip().lower().startswith("file://")
    if name == "CVS":
        cvsroot = cvs_root(root)
        if cvsroot.startswith(":"):
            return cvsroot[1:].split(":", 1)[0].split(";", 1)[0].lower() not in ("local", "fork")
        return bool(re.match(r"^[^/\\:]{2,}:", cvsroot))   # host:/path, as opposed to /path or C:\path
    if name == "Bazaar":
        bzr = nearest(root, ".bzr")
        try:
            with open(os.path.join(bzr or "", "branch", "location"), encoding="utf-8") as f:
                location = f.read().strip()
        except OSError:
            return False   # not a lightweight checkout: the history is here
        return bool(re.match(r"^[a-z][a-z0-9+.-]+:", location, re.I)) and not location.lower().startswith("file:")
    return False


# ##############################
# Finding the version control
# ##############################
# Version-control systems: how to recognise a working copy (a file or folder in it or a folder
# above), which command reads its history, and the function that does.
VERSION_CONTROL = [
    ("Git", [".git"], ["git"], git_history),
    ("SVN", [".svn"], ["svn"], svn_history),
    ("Mercurial", [".hg"], ["hg"], hg_history),
    ("Plastic SCM", [".plastic"], ["cm"], plastic_history),
    ("Bazaar", [".bzr"], ["brz", "bzr"], bzr_history),
    ("Darcs", ["_darcs"], ["darcs"], darcs_history),
    ("Fossil", [".fslckout", "_FOSSIL_"], ["fossil"], fossil_history),
    ("CVS", [os.path.join("CVS", "Root")], ["cvs"], cvs_history),
    ("Team Foundation (TFVC)", ["$tf", ".$tf", ".tfignore"], ["tf"], tfvc_history),
    # Found, but their history can't be read from the command line here: their tools need their
    # server (and a login), or are rarely installed, or would obey the working copy's own settings.
    ("Jujutsu", [".jj"], [], None),   # beside Git (colocated), its history is Git's
    ("Unity Collaborate", [".collabignore"], [], None),
    ("Visual SourceSafe", ["vssver2.scc", "vssver.scc", "mssccprj.scc"], [], None),
    ("SourceGear Vault", ["_sgvault"], [], None),
    ("Lore", [".lore", ".loreignore"], [], None),            # Epic's, for games (2026)
    ("Diversion", [".diversion", ".dvignore"], [], None),     # a cloud system for games
    ("Sapling", [".sl"], [], None),
    ("Pijul", [".pijul"], [], None),
    ("BitKeeper", [os.path.join("BitKeeper", "etc")], [], None),
    ("Monotone", ["_MTN"], [], None),
    ("GNU Arch", ["{arch}"], [], None),
    ("ClearCase", [".view.dat", "view.dat"], [], None),      # a snapshot view's root
    ("IBM Rational Team Concert (Jazz)", [".jazz5"], [], None),
    ("Rational Synergy", ["_ccmwaid.inf"], [], None),
    ("PTC Integrity (MKS)", ["project.pj"], [], None),
    ("StarTeam", [".sbas"], [], None),
    ("Surround SCM", [".MySCMServerInfo"], [], None),
    ("CA Harvest", ["harvest.sig"], [], None),
    ("Veracity", [".sgdrawer"], [], None),
    ("RCS", ["RCS"], [], None),     # RCS/ folders of ",v" files beside the files
    ("SCCS", ["SCCS"], [], None),   # SCCS/ folders of "s." files beside the files
]
# Their markers in a folder, for spotting repositories inside the scanned folder.
REPOSITORY_MARKERS = {m: name for name, markers, _, _ in VERSION_CONTROL for m in markers if name != "Visual SourceSafe"}


def marker_is(path, marker):
    """Is the file or folder at path (named marker) really that system's? Names that other
    programs may use too are checked: a ClearCase view.dat names its view, an RCS or SCCS folder
    holds their history files."""
    name = os.path.basename(marker)
    try:
        if name == "view.dat":
            with open(path, "rb") as f:
                head = f.read(8192)
            return b"view_uuid" in head or b"ws_oid" in head
        if name in ("RCS", "SCCS"):
            files = os.listdir(path)[:200]
            return any(f.endswith(",v") if name == "RCS" else f.startswith("s.") for f in files)
    except OSError:
        return False
    return os.path.exists(path)


def marker_found(root, marker):
    """The marker in root or a folder above it (see find_up), if it's really that system's."""
    found = nearest(root, marker)
    return found is not None and marker_is(found, marker)
PERFORCE_MARKERS = {".p4config", ".p4ignore", "p4config.txt", "p4ignore.txt", ".p4ignore.txt"}


def version_control(root):
    """(what was found, [history of each]). Something found that can't be read says why."""
    found, histories = [], []
    for name, markers, tools, read in VERSION_CONTROL:
        if name == "Visual SourceSafe":   # read from its database (see SourceSafe), wherever that is
            if any(find_up(root, m) for m in markers):
                found.append(f"{name} (its history comes from its database: see below)")
            continue
        if name == "Git":
            present = run(["git", "-C", root, "rev-parse"], root, 60) is not None or find_up(root, ".git")
        else:
            present = any(marker_found(root, m) for m in markers)
        if not present:
            continue
        if name == "Jujutsu" and "Git" in found:
            found.append("Jujutsu (on top of Git: its history is the Git history)")
        elif read is None:
            found.append(f"{name} (its history can't be read by this script: please ask for an export)")
        elif not any(tool_path(t) for t in tools):
            found.append(f"{name} (but the {tools[0]} command isn't installed, so no history)")
        elif OFFLINE and history_from_server(name, root):
            found.append(f"{name} (history not read: it comes from the {name} server, and --offline was given)")
            left_out_offline(f"the {name} history (read from its server)")
        elif name == "CVS" and cvs_root_starts_a_program(cvs_root(root)):
            found.append("CVS (history not read: the checkout's CVS/Root would start a program to reach the server)")
        elif name == "Mercurial" and not hg_skips_repository_settings():
            found.append("Mercurial (history not read: this hg is older than 5.4, so it would obey the repository's own"
                         " settings, which can start programs; update Mercurial to include it)")
        else:
            h = read(root)
            if h:
                found.append(name)
            elif name == "Git" and run(["git", "rev-parse", "HEAD"], root, 60) is None:
                found.append("Git (no commits yet)")
            else:
                found.append(f"{name} (no history could be read)")
            histories.append(h)

    # ####################
    # Perforce
    # ####################
    # Perforce settings often live in the registry or environment rather than a file, so ask p4.
    p4_marker = any(find_up(root, m) for m in PERFORCE_MARKERS | {os.environ.get("P4CONFIG", ".p4config")})
    if OFFLINE:   # p4 asks the server even whether this folder is in a workspace
        if p4_marker or tool_path("p4"):
            left_out_offline("Perforce: whether this folder is in a Perforce workspace, and its changelists"
                             " (p4 asks the server)")
        if p4_marker:
            found.append("Perforce (history not read: it comes from the Perforce server, and --offline was given)")
        return found, [h for h in histories if h]
    p4 = perforce_history(root)
    if p4:
        found.append("Perforce")
        histories.append(p4)
    elif p4_marker and tool_path("p4") and perforce_port_starts_a_program(root):
        found.append("Perforce (history not read: its settings file would start a program to reach the server)")
    elif p4_marker:
        found.append("Perforce (no history: is p4 installed and logged in?)" if tool_path("p4")
                     else "Perforce (but the p4 command isn't installed, so no history)")
    return found, [h for h in histories if h]


# ##############################
# Report lines
# ##############################

def history_lines(h, indent=""):
    out = [f"{indent}  {k:<52} {fmt(v):>12}" for k, v in h["rows"]]
    if h["reviews"]:
        out.append(f"{indent}  Pull requests and code reviews found:")
        out += [f"{indent}    {k:<50} {fmt(v):>12}" for k, v in h["reviews"]]
    elif h["vcs"] == "Git":
        out.append(f"{indent}  Pull requests: none found in commit messages"
                   + (" (the server wasn't asked: --offline)" if OFFLINE else
                      " or on the server (which doesn't mean there were none)"))
    per_year = h.get("per_year") or {}
    if len(per_year) > 1:
        line = ", ".join(f"{year}: {n:,}" for year, n in per_year.items())
        out.append(f"{indent}  Changes per year: {line}")
    out += [f"{indent}  NOTE: {note}" for note in h.get("notes", ())]
    return out


HISTORY_CAVEATS = [
    "About the history numbers: they count what this copy of the history holds. Commits on all branches",
    "include unmerged work, and squash merges turn many commits into one. Deleted branches, and history from",
    "before the code was imported or migrated, are missing. One person committing under several names counts",
    "once only when the names share an email address or name (or are joined in a .mailmap file). Pull requests",
    "are found only where the hosting service leaves traces in the repository, so ask the studio for the",
    "count on its hosting service (GitHub, GitLab, Azure DevOps, Bitbucket, Perforce Swarm ...).",
]


# ##############################
# Projects that moved between systems
# ##############################
# A project that moved from one system to another (SourceSafe to SVN to Git, CVS to Mercurial,
# Perforce to Plastic ...), maybe more than once, often has an older system's history, whole or in
# part, inside a newer one's too, and may still have both. Before the histories of one folder are
# added together, each change in more than one of them is found and counted once, in the newest:
# by the original change a conversion tool's marker names (git-svn's revision, git-p4's changelist,
# hg convert's ...), by the same message within a couple of days, or by the same long message on any
# date (some conversions date every change the day they ran). Where messages are too few to go by
# (SourceSafe's are often empty), the histories are fitted together by their dates.
SAME_CHANGE_DAYS = 2    # one change's date in two systems differs by time zone, or a conversion run overnight
DISTINCT_MESSAGE = 24   # characters: a message this long, found once in each history, is the same change
CONVERTED_SHARE = 0.5   # of the older history's changes in the newer one: it was converted into it
SAME_WORK_SHARE = 0.1   # of the older history's changes while both were in use: they hold the same work
COMMON_MESSAGE_TIMES, COMMON_MESSAGE_SHARE = 3, 0.01   # a message more changes than both have says nothing
SHORT_NAMES = {"Visual SourceSafe": "SourceSafe", "Team Foundation (TFVC)": "TFVC"}


def short_name(vcs):
    return SHORT_NAMES.get(vcs, vcs)


def change_unit(h):
    """What a history's changes are called: "commits", "check-ins", "submitted changelists" ..."""
    return re.sub(r" \(.*", "", h.get("unit") or "changes")


def date_range(date):
    """(first day, last day) that a date ("YYYY-MM-DD", or a year) stands for."""
    return (date + "-01-01", date + "-12-31") if len(date) == 4 else (date, date)


def day_number(date):
    """The day as a number, or None for a date that's only a year (or isn't one)."""
    from datetime import date as day
    try:
        return day.fromisoformat(date).toordinal() if len(date) == 10 else None
    except ValueError:
        return None


def same_changes(old, new):
    """({old's change: new's change}, how many of them a conversion marker named) for the changes
    in both histories, as indexes into their records."""
    a, b = old["records"], new["records"]
    pairs, taken = {}, set()

    def pair(i, j):
        pairs[i] = j
        taken.add(j)

    # ####################
    # Named by a conversion marker, either way round
    # ####################
    a_ids = {r.id: i for i, r in enumerate(a) if r.id}
    b_ids = {r.id: j for j, r in enumerate(b) if r.id}
    for j, r in enumerate(b):
        for vcs, number in r.origins:
            i = a_ids.get(number) if vcs == old["vcs"] else None
            if i is not None and i not in pairs and j not in taken:
                pair(i, j)
    for i, r in enumerate(a):
        for vcs, number in r.origins:
            j = b_ids.get(number) if vcs == new["vcs"] else None
            if j is not None and i not in pairs and j not in taken:
                pair(i, j)
    marked = len(pairs)

    # ####################
    # The same message, within SAME_CHANGE_DAYS, or in the same year where a date is only the year
    # ####################
    # Not messages that many changes have ("fix", "wip"): two teams' histories would share those.
    a_count, b_count = Counter(r.key for r in a), Counter(r.key for r in b)
    common = {k for count, n in ((a_count, len(a)), (b_count, len(b))) for k, c in count.items()
              if c > max(COMMON_MESSAGE_TIMES, COMMON_MESSAGE_SHARE * n)}
    by_day, by_year = defaultdict(list), defaultdict(list)
    for j, r in enumerate(b):
        if r.key and r.date and j not in taken and r.key not in common:
            n = day_number(r.date)
            if n is not None:
                by_day[r.key, n].append(j)
            by_year[r.key, r.date[:4], n is None].append(j)
    for i, r in enumerate(a):
        if i in pairs or not r.key or not r.date or r.key in common:
            continue
        n = day_number(r.date)
        if n is not None:
            places = [by_day.get((r.key, n + d)) for d in sorted(range(-SAME_CHANGE_DAYS, SAME_CHANGE_DAYS + 1), key=abs)]
            places.append(by_year.get((r.key, r.date[:4], True)))
        else:
            places = [by_year.get((r.key, r.date[:4], True)), by_year.get((r.key, r.date[:4], False))]
        for bucket in places:
            while bucket and bucket[-1] in taken:
                bucket.pop()
            if bucket:
                pair(i, bucket.pop())
                break

    # ####################
    # The same long message, once in each history, whatever the dates
    # ####################
    b_once = {r.key: j for j, r in enumerate(b) if len(r.key) >= DISTINCT_MESSAGE and b_count[r.key] == 1}
    for i, r in enumerate(a):
        j = b_once.get(r.key) if a_count[r.key] == 1 else None
        if j is not None and i not in pairs and j not in taken:
            pair(i, j)
    return pairs, marked


def how_related(old, new, pairs):
    """How two histories of one folder fit together, old's starting first: {"kind", "counted":
    old's changes (indexes) that are counted in new's, "during": old's changes while new was in
    use, "shared": the share of old's days on which new has changes too, "redated": whether new
    dated the changes converted from old when the conversion ran}. Kinds: "converted" (new holds
    old's history), "one after the other", "overlapping" (both in use for a while, for the same
    work) and "side by side" (both in use, for different work)."""
    a, b = old["records"], new["records"]
    lo, hi = date_range(new["dates"][0])[0], date_range(new["dates"][-1])[1]
    during = {i for i, r in enumerate(a) if r.date and date_range(r.date)[1] >= lo and date_range(r.date)[0] <= hi}
    old_days = {d for d in old["dates"] if len(d) == 10}
    shared = len(old_days & set(new["dates"])) / len(old_days) if old_days else 0.0
    starts = day_number(old["dates"][0]), day_number(new["dates"][0])
    starts_together = None not in starts and abs(starts[0] - starts[1]) <= 31
    offsets = sorted(abs(day_number(a[i].date) - day_number(b[j].date)) for i, j in pairs.items()
                     if day_number(a[i].date) is not None and day_number(b[j].date) is not None)
    redated = len(offsets) >= 3 and offsets[len(offsets) // 2] > SAME_CHANGE_DAYS
    matched = set(pairs)
    out = {"during": during, "shared": shared, "redated": redated}
    # Dates alone only say something where there are too few messages to go by.
    with_messages = all(sum(1 for r in h["records"] if r.key) >= len(h["records"]) / 2 for h in (old, new))
    if len(pairs) >= CONVERTED_SHARE * len(a) or (not with_messages and starts_together and shared >= CONVERTED_SHARE):
        return dict(out, kind="converted", counted=set(range(len(a))) if redated else matched | during)
    if date_range(old["dates"][-1])[1] <= lo:
        return dict(out, kind="one after the other", counted=matched)
    if not with_messages or len(matched & during) >= SAME_WORK_SHARE * len(during):
        return dict(out, kind="overlapping", counted=matched | during)
    return dict(out, kind="side by side", counted=matched)


def relation_text(old, new, pairs, marked, rel):
    """The report's sentence on how old's history fits with new's (see how_related)."""
    o, n, ou, nu = short_name(old["vcs"]), short_name(new["vcs"]), change_unit(old), change_unit(new)
    during, n_old = rel["during"], len(old["records"])
    both_to = min(old["dates"][-1], new["dates"][-1])
    new_during = sum(1 for r in new["records"] if r.date and date_range(r.date)[0] <= date_range(both_to)[1])
    alike = len(set(pairs) & during)
    if rel["kind"] == "converted":
        if len(pairs) >= CONVERTED_SHARE * n_old:
            how = ", ".join(part for part in (f"{marked:,} by the conversion tool's markers" if marked else "",
                                              f"{len(pairs) - marked:,} by their messages" if len(pairs) > marked else "")
                            if part)
            why = f"{len(pairs):,} of its {n_old:,} {ou} are in {n} too ({how})"
        else:
            why = f"it has {nu} on {100 * rel['shared']:.0f}% of the days with {o} {ou}"
        text = f"{n} already holds the {o} history: {why}, so the history was converted into {n}."
        rest = n_old - len(rel["counted"])
        text += (f" The {n} numbers are the whole history; don't add the {o} {ou} to them." if not rest else
                 f" {rest:,} of the {o} {ou} are from before or after {n}'s, and aren't in it, so they're added.")
        if rel["redated"]:
            text += f" ({n} dates the converted {ou} when the conversion ran, not when they were made.)"
    elif rel["kind"] == "one after the other":
        text = f"One after the other: {o} until {old['dates'][-1]}, then {n} from {new['dates'][0]}."
        if pairs:
            text += f" {len(pairs):,} of the {o} {ou} are in {n} too, and counted once."
    elif rel["kind"] == "overlapping":
        text = (f"Both were in use from {new['dates'][0]} to {both_to}: {o} has {len(during):,} {ou} then, {n}"
                f" {new_during:,} {nu}.")
        text += (f" {alike:,} of them have the same message in both, so the same work went into both: that time is"
                 f" counted once, from {n}." if alike else
                 f" The same work may be in both, so that time is counted once, from {n}.")
    else:
        text = (f"Both were in use from {new['dates'][0]} to {both_to}, for different work: {o}'s {len(during):,}"
                f" {ou} then have messages unlike {n}'s {new_during:,} {nu}, so both are counted"
                + (f" ({len(pairs):,} that are in both, once)." if pairs else "."))
    return text


def across_systems(histories):
    """(report lines, (changes, first, last, how)) for one folder's histories in more than one
    system (or more than one history of a system), each change counted once; ([], None) for fewer
    than two. Marks each history: "counted_elsewhere" (its changes counted in a newer one's),
    "standard_duplicates" (how many of them forms would count) and "held_by" (the system whose
    history holds all of it)."""
    import textwrap
    hs = [h for h in histories if h.get("dates")]
    if len(hs) < 2:
        return [], None
    # Oldest first. Starting the same day, the older system's history was converted into the newer
    # one's, and Git's is taken as the newest: a mirror of it (Plastic's GitSync ...) is counted in Git.
    hs.sort(key=lambda h: (date_range(h["dates"][0])[0], h["vcs"] == "Git", SYSTEM_RELEASED.get(h["vcs"], ("9999",))[0]))
    names = [short_name(h["vcs"]) for h in hs]
    width = max(len(name) for name in names) + 1
    out = [f"  {name + ':':<{width}} {len(h['records']):,} {change_unit(h)}, {h['dates'][0]} to {h['dates'][-1]}"
           for name, h in zip(names, hs)]

    # ####################
    # Each pair, older first
    # ####################
    # Each older history is described with the first newer one that holds its work, or else the next one.
    counted_elsewhere = [set() for _ in hs]
    holders = [None] * len(hs)
    kinds = {}
    for x, old in enumerate(hs):
        texts = []
        for y in range(x + 1, len(hs)):
            new = hs[y]
            pairs, marked = same_changes(old, new)
            rel = how_related(old, new, pairs)
            kinds[x, y] = rel["kind"]
            counted_elsewhere[x] |= rel["counted"]
            texts.append(relation_text(old, new, pairs, marked, rel))
            if rel["kind"] in ("converted", "overlapping") and rel["counted"] and holders[x] is None:
                holders[x] = names[y]
                texts = [texts[-1]]
        for text in texts[:1]:
            out += textwrap.wrap(text, 104, initial_indent="  ", subsequent_indent="  ")

    # ####################
    # All together
    # ####################
    total = sum(len(h["records"]) - len(c) for h, c in zip(hs, counted_elsewhere))
    first, last = min(h["dates"][0] for h in hs), max(h["dates"][-1] for h in hs)
    out.append(f"  Together{', without counting it twice' if any(counted_elsewhere) else ''}: {total:,} changes from"
               f" {first} to {last}.")
    joins = {"converted": ", converted into {}", "one after the other": ", then {}", "overlapping": " and {}, overlapping",
             "side by side": " and {}, side by side"}
    how = names[0] + "".join(joins[kinds[y - 1, y]].format(names[y]) for y in range(1, len(hs)))
    for h, c, holder in zip(hs, counted_elsewhere, holders):
        h["counted_elsewhere"] = c
        h["standard_duplicates"] = sum(1 for i in c if h["records"][i].standard)
        if len(c) == len(h["records"]):
            h["held_by"] = holder or "a newer system"
            h["standard_duplicates"] = h.get("standard_commits") or 0
    title = ", ".join(names[:-1]) + " and " + names[-1] + " together:"
    return ["", title] + out, (total, first, last, how)


def engine_report(engine):
    """The report section for a custom-built engine that lives outside the scanned folder."""
    v = read_json(find_path(engine, "Engine", "Build", "Build.version"))
    version = "{}.{}.{}".format(v.get("MajorVersion", "?"), v.get("MinorVersion", "?"), v.get("PatchVersion", "?"))
    vcs, histories = version_control(engine)
    out = ["", f"Custom Unreal Engine {version} that this project is built with (found on this computer):",
           f"  Version control: {', '.join(vcs) or 'none found'}"]
    for h in histories:
        out += [f"  History ({h['vcs']}):"] + history_lines(h, "  ")
    if not histories:
        out.append("  No version-control history, so the studio's engine changes can't be told apart from Epic's code.")
    return out


# #######################################
# Visual SourceSafe
# #######################################

# Visual SourceSafe. Microsoft stopped selling it in 2005 and its command line (ss.exe) is rarely
# installed any more, so the database is read directly: a folder with srcsafe.ini and a data
# folder, holding one record file per file and project. Every revision of every file is a record
# in it (the layout is the one vss2git, vss2svn and py-vss read). SourceSafe has no commits, so
# revisions are grouped into check-ins the way vss2git groups them: by the same person, close
# together in time. Studios that moved to Git usually either converted this history into Git
# or started Git from a snapshot and kept the SourceSafe database on a server.

# ##############################
# Reading a database
# ##############################
VSS_SIGNATURE = b"SourceSafe@Microsoft"
VSS_RECORD_FILE = re.compile(r"^[a-z]{8}$", re.I)   # data/a/aaaaaaaa; the file contents are aaaaaaaa.a/.b
VSS_REVISION = struct.Struct("<IHHI32s32sIIHH")
VSS_LABEL = 0
# Actions that are a change of their own. Left out: labels (counted separately), "added" in a
# project (the same event as "created" in the file's own record), and archive/restore.
VSS_CHANGES = {1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17}
VSS_SAME_CHECKIN, VSS_SAME_COMMENT = 30, 600   # seconds between revisions (vss2git's defaults)


def vss_crc(data):
    """The 16-bit check value of a SourceSafe record: a CRC-32 that starts from 0, folded in half."""
    import zlib
    crc = zlib.crc32(data, 0xFFFFFFFF) ^ 0xFFFFFFFF   # zlib's CRC-32 starts from (and ends with) all ones
    return (crc ^ (crc >> 16)) & 0xFFFF


def vss_string(raw):
    return raw.split(b"\0", 1)[0].decode("cp1252", "replace").strip()


def is_vss_data_folder(path):
    """A SourceSafe data folder: it holds the root project's record, a/aaaaaaaa."""
    try:
        with open(os.path.join(path, "a", "aaaaaaaa"), "rb") as f:
            return f.read(len(VSS_SIGNATURE)) == VSS_SIGNATURE
    except OSError:
        return False


def is_vss_database(path):
    """A SourceSafe database (with srcsafe.ini), a copy of one without it, or just its data folder."""
    return (os.path.isfile(os.path.join(path, "srcsafe.ini")) or is_vss_data_folder(os.path.join(path, "data"))
            or is_vss_data_folder(path))


def vss_data_path(db):
    if not os.path.isfile(os.path.join(db, "srcsafe.ini")):   # a copy without it, or the data folder itself
        return os.path.join(db, "data") if is_vss_data_folder(os.path.join(db, "data")) else db
    data = "data"
    try:
        with open(os.path.join(db, "srcsafe.ini"), encoding="latin-1") as f:
            for line in f:
                m = re.match(r"\s*Data_Path\s*=\s*(.+?)\s*$", line, re.I)
                if m:
                    data = m.group(1)
    except OSError:
        pass
    # A srcsafe.ini can name a data folder on any computer (\\server\share\data): that isn't opened
    # without --network-sourcesafe, like the databases project files name there (see
    # SourceSafe.histories); its own one is.
    return os.path.join(db, "data" if is_network_path(data) and not NETWORK_SOURCESAFE else data)


def vss_item_revisions(buf):
    """[(time, user, comment, action)] from one record file, or None if it isn't one. Damaged
    records (wrong check value) are left out and counted in the last element's place."""
    if not buf.startswith(VSS_SIGNATURE) or len(buf) < 0x34 + 8:
        return None
    revisions, damaged = [], 0
    end = len(buf)
    length, sig = struct.unpack_from("<I2s", buf, 0x34)
    if sig == b"DH" and length >= 66 and len(buf) >= 0x34 + 8 + 60:
        eof = struct.unpack_from("<i", buf, 0x34 + 8 + 2 + 2 + 40 + 2 + 2 + 8)[0]
        if 0x34 < eof <= len(buf):
            end = eof
    pos = 0x34
    while pos + 8 <= end:
        length, sig, crc = struct.unpack_from("<I2sH", buf, pos)
        body = buf[pos + 8:pos + 8 + length]
        if len(body) < length:
            break
        if sig == b"EL" and length >= VSS_REVISION.size:
            if vss_crc(body) != crc:
                damaged += 1
            else:
                _, action, _, when, user, _, comment_at, _, comment_len, _ = VSS_REVISION.unpack_from(body)
                comment = b""
                if comment_len and 0 < comment_at <= len(buf) - 8:
                    c_len, c_sig = struct.unpack_from("<I2s", buf, comment_at)
                    if c_sig == b"MC":
                        comment = buf[comment_at + 8:comment_at + 8 + min(c_len, comment_len)].split(b"\0", 1)[0]
                revisions.append((when, vss_string(user), comment.strip(), action))
        pos += 8 + length
    return revisions, damaged


def read_sourcesafe(db):
    """The history in a SourceSafe database (the folder with srcsafe.ini), or None."""

    # ####################
    # Every revision in the database
    # ####################
    data = vss_data_path(db)
    revisions, items, damaged, unreadable = [], 0, 0, 0
    for dirpath, _, filenames in os.walk(long_path(data)):
        for name in filenames:
            if not VSS_RECORD_FILE.match(name):
                continue
            progress(f"Reading the SourceSafe database: {items:,} files and projects ...")
            try:
                with open(os.path.join(dirpath, name), "rb") as f:
                    found = vss_item_revisions(f.read())
            except OSError:
                unreadable += 1
                continue
            if found is not None:
                items += 1
                revisions += found[0]
                damaged += found[1]
    progress()
    if not revisions:
        return None

    # ####################
    # Grouped into check-ins
    # ####################
    labels = sum(1 for r in revisions if r[3] == VSS_LABEL)
    changes = sorted((r for r in revisions if r[3] in VSS_CHANGES), key=lambda r: (r[1].lower(), r[0]))
    checkins, records, last = [], [], None
    for when, user, comment, _ in changes:
        if last and user.lower() == last[1].lower() and (
                when - last[0] <= VSS_SAME_CHECKIN or (comment and comment == last[2] and when - last[0] <= VSS_SAME_COMMENT)):
            last = (when, user, comment)
            if comment and not records[-1].key:   # the check-in's comment, for matching it in other systems
                records[-1] = records[-1]._replace(key=message_key(comment.decode("cp1252", "replace")))
            continue
        last = (when, user, comment)
        checkins.append((datetime.fromtimestamp(when, timezone.utc).strftime("%Y-%m-%d"), user or "(no name)"))
        records.append(Change(checkins[-1][0], None, message_key(comment.decode("cp1252", "replace")), (), None))
    notes = []
    if damaged or unreadable:
        notes.append(f"{plural(damaged + unreadable, 'damaged or unreadable record')} in the database left out.")
    h = history("Visual SourceSafe", "check-ins (revisions grouped by person and time)", checkins, notes=notes,
                records=records)
    h["rows"][1:1] = [("  file revisions in them", len(changes))]
    h["rows"] += [("labels", labels), ("files and projects in the database", items)]
    return h


# ##############################
# Finding databases during the scan
# ##############################
VSS_BINDINGS = {"vssver.scc", "vssver2.scc", "mssccprj.scc"}
# Where project files record the SourceSafe database ("SccAuxPath", "SCC_Aux_Path").
VSS_AUX_PATH = re.compile(rb"Scc_?Aux_?Path\d*\"?\s*[=>]\s*\"?([^\"\r\n<]+)", re.I)
VSS_AUX_FILES = {".sln", ".vcproj", ".vcxproj", ".csproj", ".vbproj", ".scc"}


class SourceSafe:
    """What the scan finds of SourceSafe: databases, folders bound to one (they hold vssver.scc),
    and where project files say the database was."""

    def __init__(self, extra_databases=()):
        self.databases = []
        self.bound_folders = 0
        self.archives = 0    # SourceSafe archive files (.ssa), which only SourceSafe itself can restore
        self.recorded = []   # database locations named in project files
        self.on_network = []  # those on another computer: not opened (see histories)
        # --sourcesafe and SSDIR are the user's own settings, so they may name a network share, but
        # with --offline it isn't opened (main() refuses --sourcesafe naming one).
        ssdir = os.environ.get("SSDIR", "")
        if OFFLINE and is_network_path(ssdir):
            left_out_offline("the SourceSafe database the SSDIR setting names, on a network share")
            ssdir = ""
        for db in list(extra_databases) + [ssdir]:
            self.add_database(db)

    # ####################
    # Databases
    # ####################

    def add_database(self, db):
        db = (db or "").strip().strip('"')
        if db.lower().endswith("srcsafe.ini"):
            db = os.path.dirname(db)
        if db and is_vss_database(db):
            key = os.path.normcase(os.path.abspath(db))
            if key not in {os.path.normcase(os.path.abspath(d)) for d in self.databases}:
                self.databases.append(db)
            return True
        return False

    # ####################
    # During the walk
    # ####################

    def visit(self, dirpath, filenames):
        """Notes what this folder shows. True if it's a database, whose files aren't code."""
        lower = {f.lower() for f in filenames}
        if ("srcsafe.ini" in lower and os.path.isdir(os.path.join(dirpath, "data"))) or \
                ("um.dat" in lower and is_vss_data_folder(dirpath)) or is_vss_data_folder(os.path.join(dirpath, "data")):
            self.add_database(short_path(dirpath))
            return True
        self.archives += sum(1 for f in lower if f.endswith(".ssa"))
        if lower & {"vssver.scc", "vssver2.scc"}:
            self.bound_folders += 1
        for name in filenames:
            if os.path.splitext(name)[1].lower() in VSS_AUX_FILES:
                try:
                    with open(os.path.join(dirpath, name), "rb") as f:
                        head = f.read(1 << 20)
                except OSError:
                    continue
                for m in VSS_AUX_PATH.finditer(head):
                    where = m.group(1).decode("latin-1").strip()
                    if re.match(r"^(\\\\|[a-z]:\\|/)", where, re.I) and where not in self.recorded:
                        self.recorded.append(where)
        return False

    def histories(self):
        """[(database, history)] of the databases found, including ones the project files name on
        this computer. Ones they name on another computer aren't opened unless the user says so
        (--network-sourcesafe): the project files could name any server."""
        for where in self.recorded:
            if is_network_path(where) and not NETWORK_SOURCESAFE:
                self.on_network.append(where)
            else:
                self.add_database(where)
        return [(db, h) for db, h in ((db, read_sourcesafe(db)) for db in self.databases[:5]) if h]


# ##############################
# SourceSafe and Git together
# ##############################
GIT_RELEASED = SYSTEM_RELEASED["Git"][0]   # Git's first release: a commit dated before it was imported
VSS_IN_MESSAGE = re.compile(r"source\s?safe|\bvss\b|vss2git|vssmigrate", re.I)


def imported_git_history(root, h):
    """What a Git history shows of an earlier system: commits dated before Git existed (converted
    history), messages that name SourceSafe, and a first commit that brings in the whole code at once."""
    pre_git = [d for d in h["dates"] if d < GIT_RELEASED]
    out = {"pre_git": pre_git, "vss_messages": h.get("vss_messages", 0), "bulk_start": None}
    roots = (run(["git", "rev-list", "--max-parents=0", "HEAD"], root, 120) or "").split()[:5]
    for sha in roots:
        stat = run(["git", "show", *GIT_NO_PROGRAMS, "--format=%ad", "--date=short", "--shortstat", sha], root, 300) or ""
        files = re.search(r"(\d+) files? changed", stat)
        if files and int(files.group(1)) >= 300:
            out["bulk_start"] = (stat.split("\n", 1)[0].strip(), int(files.group(1)))
    return out


# ##############################
# Report section
# ##############################

def sourcesafe_lines(root, vss, git_h, histories, alerts):
    """The report's SourceSafe part: each database's history (added to histories, to be fitted
    together with the others: see across_systems), or, when the code was in SourceSafe but the
    database isn't here, how to include it."""

    # ####################
    # The databases found
    # ####################
    out = []
    found = vss.histories()
    for where in vss.recorded:   # on screen only: a server's name isn't for the report
        if where in vss.on_network:
            print(f"SourceSafe database named in the project files (shown here only, not saved in the report): {where}"
                  f" (on a network share, so not opened; to include it, run this again with --network-sourcesafe,"
                  f" or with --sourcesafe \"{where}\")")
            continue
        reachable = os.path.isfile(os.path.join(where, "srcsafe.ini"))
        print(f"SourceSafe database named in the project files (shown here only, not saved in the report): {where}"
              + ("" if reachable else " (not reachable from this computer)"))
    for _, h in found:
        out += ["", "Version control history (Visual SourceSafe database):"] + history_lines(h)
        histories.append(h)
    imported = imported_git_history(root, git_h) if git_h else None

    # ####################
    # Signs of history that isn't here
    # ####################
    if imported and imported["bulk_start"] and imported["bulk_start"][0] >= GIT_RELEASED:
        day, files = imported["bulk_start"]
        out += ["", f"NOTE: Git's history starts on {day} with one commit of {files:,} files: the code was copied in from",
                "      somewhere else, so its history before that day isn't in Git"
                + (" (see the SourceSafe history above)." if found else ".")]
    if vss.archives and not found:
        out += ["", f"NOTE: Found {plural(vss.archives, 'SourceSafe archive file')} (.ssa). This script can't read SourceSafe",
                "      archives. SourceSafe Administrator can restore one into a database (Archive > Restore Projects);",
                "      run this script on that database with --sourcesafe."]
        alerts.append("SourceSafe archive not read")

    # ####################
    # Signs that the code was in SourceSafe
    # ####################
    evidence = []
    if vss.bound_folders:
        evidence.append(f"{plural(vss.bound_folders, 'folder')} still hold its binding files (vssver.scc)")
    if vss.recorded:
        evidence.append("project files name its database")
    if imported and imported["vss_messages"]:
        evidence.append(f"{plural(imported['vss_messages'], 'commit message')} mention it")
    if (evidence or vss.databases) and not found:
        if vss.databases:
            out += ["", "NOTE: Found a Visual SourceSafe database, but couldn't read any history from it. Please mention",
                    "      this when you send the report."]
        else:
            out += ["", "NOTE: This code was kept in Visual SourceSafe:", *[f"      - {e}" for e in evidence],
                    "      The SourceSafe database isn't here, so that history isn't counted. If it still exists (a",
                    "      folder holding srcsafe.ini and a data folder), run this script again with --sourcesafe",
                    "      \"<that folder>\" added. SourceSafe has no server program, so a copy from a backup or an old disk",
                    "      works too, even of the data folder alone. The script only reads it."]
            if imported and imported["pre_git"]:
                out.append(f"      Git does hold {plural(len(imported['pre_git']), 'commit')} dated before 2005, so part of"
                           " it may already have been converted into Git.")
        alerts.append("SourceSafe history not included")
    if vss.on_network:
        out += ["", "NOTE: The project files name a SourceSafe database on a network share. This script doesn't open",
                "      network locations by itself, so it wasn't read. To include its history, run this again with",
                "      --network-sourcesafe added, or with --sourcesafe \"<that network folder>\" (the folder was shown",
                "      on screen, not in this report)."]
    return out


# #######################################
# Databases
# #######################################

# Databases: Microsoft Access and SQL Server. Much of such a system's code lives inside database
# files rather than in source files: Access forms, reports, queries, macros and VBA modules, and
# SQL Server stored procedures, views, functions and triggers.

# ##############################
# Kinds of database file
# ##############################
ACCESS_EXTS = {".mdb", ".accdb", ".accda", ".accde", ".mde", ".mda", ".adp", ".ade"}
SQL_SERVER_FILES = {".mdf": "database files", ".ndf": "database files", ".ldf": "transaction logs",
                    ".bak": "backups", ".trn": "transaction log backups"}
DAC_EXTS = {".dacpac", ".bacpac"}
VB_EXTS = {".bas", ".cls", ".frm", ".ctl", ".dsr", ".pag", ".dob"}
# Access objects exported to text (SaveAsText, or the msaccess-vcs add-in), by their first lines.
ACCESS_EXPORT_EXTS = {".bas", ".txt", ".form", ".report", ".macro", ".qry", ".mac", ".frm", ".rpt"}
DATA_FILE_EXTS = {".csv", ".tsv", ".xls", ".xlsx", ".xlsm", ".ods", ".parquet", ".avro", ".orc", ".feather",
                  ".jsonl", ".ndjson", ".sqlite", ".sqlite3", ".db", ".db3", ".sdf", ".dbf", ".fdb", ".gdb", ".dmp",
                  ".dump", ".bcp"}
DATA_FILE_MIN = 100_000   # bytes: smaller spreadsheets and CSVs are usually settings or test fixtures


# ##############################
# SQL Server
# ##############################

# ####################
# Kinds of object
# ####################
SQL_OBJECT_KINDS = {"proc": "stored procedures", "procedure": "stored procedures", "function": "functions",
                    "view": "views", "trigger": "triggers", "table": "tables", "type": "types", "synonym": "synonyms",
                    "sequence": "sequences", "schema": "schemas"}
DAC_TYPES = {"SqlProcedure": "stored procedures", "SqlScalarFunction": "functions",
             "SqlInlineTableValuedFunction": "functions", "SqlMultiStatementTableValuedFunction": "functions",
             "SqlTableValuedFunction": "functions", "SqlView": "views", "SqlDmlTrigger": "triggers",
             "SqlDatabaseDdlTrigger": "triggers", "SqlServerDdlTrigger": "triggers", "SqlTable": "tables",
             "SqlSequence": "sequences", "SqlSchema": "schemas", "SqlTableType": "types",
             "SqlUserDefinedDataType": "types", "SqlSynonym": "synonyms"}
SQL_MODULE_TYPES = {"SQL_STORED_PROCEDURE": "stored procedures", "SQL_SCALAR_FUNCTION": "functions",
                    "SQL_TABLE_VALUED_FUNCTION": "functions", "SQL_INLINE_TABLE_VALUED_FUNCTION": "functions",
                    "VIEW": "views", "SQL_TRIGGER": "triggers", "RULE": "rules", "DEFAULT_CONSTRAINT": None}
CODE_OBJECTS = ("stored procedures", "functions", "views", "triggers")


def sql_object_key(name):
    """"[dbo].[GetOrders]" -> "dbo.getorders" (schema dbo when none is given)."""
    parts = [p.strip().strip("[]\"").lower() for p in re.split(r"\s*\.\s*(?![^\[]*\])", name)]
    return ".".join(parts if len(parts) > 1 else ["dbo"] + parts)


# ####################
# SQL scripts
# ####################
SQL_OBJECT = re.compile(
    rb"^\s*(?:CREATE(?:\s+OR\s+ALTER)?|ALTER)\s+(PROC(?:EDURE)?|FUNCTION|VIEW|TRIGGER|TABLE|TYPE|SYNONYM|SEQUENCE|"
    rb"SCHEMA)\s+((?:\[[^\]\r\n]+\]|\"[^\"\r\n]+\"|[\w#@$]+)(?:\s*\.\s*(?:\[[^\]\r\n]+\]|\"[^\"\r\n]+\"|[\w#@$]+))?)",
    re.I | re.M)


def as_utf8(data):
    """A file's bytes as UTF-8 without a byte-order mark (SSMS often saves scripts as UTF-16)."""
    bom = data[:2] in (b"\xff\xfe", b"\xfe\xff")
    if bom or (len(data) >= 64 and data[1:64:2].count(0) > 24):
        try:
            return data.decode("utf-16" if bom else "utf-16-le").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return data[3:] if data[:3] == b"\xef\xbb\xbf" else data


def sql_objects(data):
    """[(kind, key)] for the objects a T-SQL script creates or alters."""
    out = []
    for kind, name in SQL_OBJECT.findall(as_utf8(data)):
        if name.lstrip(b"[\"").startswith((b"#", b"@")):
            continue   # a temporary table inside a procedure, not part of the database
        kind = SQL_OBJECT_KINDS[kind.decode("ascii", "replace").lower()]
        out.append((kind, sql_object_key(name.decode("utf-8", "replace"))))
    return out


SQL_STATEMENT_START = re.compile(rb"^\s*(CREATE|ALTER|DROP|SELECT|UPDATE|DELETE|MERGE|WITH|IF|BEGIN|END|DECLARE|SET|EXEC|"
                                 rb"EXECUTE|PRINT|USE|GO|RETURN|GRANT|DENY|REVOKE|TRUNCATE|WHILE|COMMIT|ROLLBACK|RAISERROR|"
                                 rb"THROW)\b", re.I)


def sql_data_lines(lines):
    """How many of a SQL script's non-blank lines are INSERT statements (and SET IDENTITY_INSERT
    around them): the data in the database, not its code."""
    data = 0
    inserting = last_was_data = False
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text.upper() in (b"GO", b"GO;"):
            data += last_was_data   # a batch separator between INSERTs goes with them
            continue
        before = data
        upper = text[:20].upper()
        if upper.startswith(b"INSERT") or (upper.startswith(b"SET ") and b"IDENTITY_INSERT" in text.upper()):
            inserting = not upper.startswith(b"SET ")
            data += 1
        elif inserting and not SQL_STATEMENT_START.match(text):
            data += 1   # an INSERT continued: more rows of values
        else:
            inserting = False
        last_was_data = data > before
    return data


def is_sql_data(lines):
    """A script that's mostly INSERTs: the data in a database, not its code."""
    statements = [l for l in lines if l.strip() and l.strip().upper() not in (b"GO", b"GO;")]
    return len(statements) >= 20 and sql_data_lines(statements) >= 0.6 * len(statements)


# ####################
# .dacpac and .bacpac packages
# ####################

def read_dac_package(path):
    """What a .dacpac / .bacpac (a SQL Server database's schema, packaged) defines:
    {"objects": Counter of kinds, "code": [(kind, key, body)], "scripts": [text]}."""
    import xml.etree.ElementTree as ET
    import zipfile
    found = {"objects": Counter(), "code": [], "scripts": []}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.lower() in ("predeploy.sql", "postdeploy.sql"):
                found["scripts"].append(z.read(name).decode("utf-8-sig", "replace"))
        with z.open("model.xml") as f:
            depth, top, prop = 0, None, None
            for event, elem in ET.iterparse(f, events=("start", "end")):
                tag = elem.tag.rsplit("}", 1)[-1]
                if event == "start":
                    depth += 1
                    if tag == "Element" and depth == 3:   # DataSchemaModel > Model > Element
                        kind = DAC_TYPES.get(elem.get("Type"))
                        top = (kind, sql_object_key(elem.get("Name", "?"))) if kind else None
                        if kind:
                            found["objects"][kind] += 1
                    elif tag == "Property" and depth == 4:
                        prop = elem.get("Name")
                    continue
                depth -= 1
                if tag == "Value" and top and top[0] in CODE_OBJECTS and prop in ("BodyScript", "QueryScript"):
                    found["code"].append((top[0], top[1], elem.text or ""))
                if depth == 2:
                    elem.clear()   # done with this object: free its memory
                    top = None
    return found


# ####################
# SSIS packages and SSRS reports
# ####################

def ssis_package_code(text):
    """{"sql": [statement], "scripts": [(language, code)]} in an SSIS package (.dtsx)."""
    import html
    sql = re.findall(r'SqlStatementSource="([^"]*)"', text)
    sql += re.findall(r'<(?:SQLTask:)?SqlStatementSource>([^<]*)<', text)
    sql += re.findall(r'<property\b[^>]*\bname="(?:SqlCommand|SqlCommandVariable)"[^>]*>([^<]*)</property>', text)
    scripts = []
    for name, code in re.findall(r'<ProjectItem\s+Name="([^"]+)"[^>]*>\s*<!\[CDATA\[(.*?)\]\]>', text, re.S):
        low = name.lower().replace("\\", "/")
        if low.endswith((".cs", ".vb")) and "/" not in low and not low.endswith((".designer.cs", ".designer.vb")):
            scripts.append(("C#" if low.endswith(".cs") else "VB.NET", code))   # ScriptMain: the task's own code
    return {"sql": [html.unescape(s) for s in sql if s.strip()], "scripts": scripts}


def ssrs_report_code(text):
    """{"sql": [query], "scripts": [("VB.NET", code)]} in an SSRS report (.rdl / .rdlc)."""
    import html
    return {"sql": [html.unescape(s) for s in re.findall(r"<CommandText>([^<]*)</CommandText>", text) if s.strip()],
            "scripts": [("VB.NET", html.unescape(c)) for c in re.findall(r"<Code>([^<]*)</Code>", text) if c.strip()]}


# ####################
# A running SQL Server
# ####################
# Reading the code in a running SQL Server (asked for with --sql-server), through sqlcmd.
SQLCMD_PATHS = [r"C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\*\Tools\Binn\SQLCMD.EXE",
                r"C:\Program Files\Microsoft SQL Server\*\Tools\Binn\SQLCMD.EXE", r"C:\Program Files\SqlCmd\sqlcmd.exe",
                "/opt/mssql-tools18/bin/sqlcmd", "/opt/mssql-tools/bin/sqlcmd", "/usr/local/bin/sqlcmd"]
# Each value comes between CHAR(29) and CHAR(30), so sqlcmd's column headers can't be mistaken for it.
# (The system views' text comes in different collations: each piece is put in the database's own.)
SQL_SERVER_MODULES = ("SET NOCOUNT ON; SELECT CHAR(29) + o.type_desc COLLATE DATABASE_DEFAULT + CHAR(31)"
                      " + SCHEMA_NAME(o.schema_id) COLLATE DATABASE_DEFAULT + '.' + o.name COLLATE DATABASE_DEFAULT"
                      " + CHAR(31) + REPLACE(REPLACE(m.definition COLLATE DATABASE_DEFAULT, CHAR(30), ' '), CHAR(29), ' ')"
                      " + CHAR(30) FROM sys.sql_modules m JOIN sys.objects o ON o.object_id = m.object_id"
                      " WHERE o.is_ms_shipped = 0")
SQL_SERVER_TABLES = ("SET NOCOUNT ON; SELECT CHAR(29) + CAST(COUNT(*) AS varchar(20)) + CHAR(30) FROM sys.tables"
                     " WHERE is_ms_shipped = 0")
SQL_SERVER_DATABASES = ("SET NOCOUNT ON; SELECT CHAR(29) + name COLLATE DATABASE_DEFAULT + CHAR(30) FROM sys.databases"
                        " WHERE database_id > 4 AND state = 0")


def sqlcmd_values(out):
    return re.findall(r"\x1d(.*?)\x1e", out or "", re.S)


TRUST_SERVER_CERTIFICATE = False   # --trust-server-certificate: sqlcmd's -C, for a server the user trusts
# What sqlcmd says when it can't verify the server's certificate (newer versions encrypt, and check
# the certificate, by default; a server's own self-signed one fails that check).
SQL_CERTIFICATE_ERROR = re.compile(r"certificate|SSL Provider", re.I)


def sqlcmd(server, query, database="master"):
    """(sqlcmd's output or None, whether it failed because the server's certificate couldn't be
    verified). Windows sign-in unless SQLCMDUSER / SQLCMDPASSWORD are set."""
    exe = tool_path("sqlcmd")
    if exe is None:
        import glob
        exe = next((m for p in SQLCMD_PATHS for m in sorted(glob.glob(p), reverse=True)), None)
    if exe is None:
        return None, False
    auth = [] if os.environ.get("SQLCMDUSER") else ["-E"]
    trust = ["-C"] if TRUST_SERVER_CERTIFICATE else []
    # -y 0: no width limit
    args = [exe, "-S", server, "-d", database, *auth, *trust, "-y", "0", "-f", "65001", "-b", "-Q", query]
    try:
        out = subprocess.run(args, capture_output=True, timeout=600, env=quiet_env(), stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None, False
    if out.returncode == 0:
        return out.stdout.decode("utf-8", "replace"), False
    said = (out.stdout + out.stderr).decode("utf-8", "replace")
    return None, bool(SQL_CERTIFICATE_ERROR.search(said))


CERTIFICATE_REFUSED = ("couldn't connect: the server's certificate couldn't be verified, so sqlcmd didn't trust it"
                       " (usual for a server with its own self-signed certificate). If this is a server you trust, run"
                       " this again with --trust-server-certificate added")


def read_sql_server(server, databases=()):
    """{"databases": n, "objects": Counter, "code": [(kind, db.key, definition)], "tables": n, "error"}."""
    found = {"databases": 0, "objects": Counter(), "code": [], "tables": 0}
    names = list(databases)
    if not names:
        out, certificate = sqlcmd(server, SQL_SERVER_DATABASES)
        if out is None:
            found["error"] = CERTIFICATE_REFUSED if certificate else (
                "couldn't connect (is sqlcmd installed? may this Windows account sign in? or set SQLCMDUSER and"
                " SQLCMDPASSWORD)")
            return found
        names = [n.strip() for n in sqlcmd_values(out) if n.strip()]
    for db in names:
        progress(f"Reading the code in SQL Server database {db} ...")
        out, certificate = sqlcmd(server, SQL_SERVER_MODULES, db)
        if out is None:
            if certificate:
                found["error"] = CERTIFICATE_REFUSED
            continue
        found["databases"] += 1
        for record in sqlcmd_values(out):
            fields = record.split("\x1f", 2)
            if len(fields) == 3:
                kind = SQL_MODULE_TYPES.get(fields[0].strip(), "other objects")
                if kind:
                    found["objects"][kind] += 1
                    found["code"].append((kind, f"{db.lower()}.{fields[1].strip().lower()}", fields[2]))
        tables = (sqlcmd_values(sqlcmd(server, SQL_SERVER_TABLES, db)[0]) or ["0"])[0].strip()
        found["tables"] += int(tables) if tables.isdigit() else 0
    progress()
    if found["databases"]:
        found.pop("error", None)
    elif "error" not in found:
        found["error"] = "couldn't read any database"
    return found


# ##############################
# Visual Basic and Microsoft Access
# ##############################

# ####################
# Visual Basic source
# ####################

def vb_code_lines(lines, ext):
    """A Visual Basic / VBA file's code lines: without a form's layout (VB6 .frm, .ctl ...), a class's
    header, or the "Attribute VB_..." lines the editor keeps."""
    first = next((i for i, l in enumerate(lines) if l.startswith(b"Attribute VB_")), None)
    if first is not None and ext in (".frm", ".ctl", ".dsr", ".pag", ".dob", ".cls"):
        lines = lines[first:]
    return [l for l in lines if not l.startswith(b"Attribute VB_")]


def looks_like_vb(data):
    head = data[:4000]
    return bool(re.search(rb"Attribute VB_|^\s*Option (Explicit|Compare|Base|Private)|^\s*(Public |Private )?(Sub|Function) \w+",
                          head, re.M | re.I)) and not head.lstrip().startswith((b"\\", b"%"))   # not a LaTeX class


# ####################
# Access objects exported as text
# ####################

def access_export(data):
    """What Access object a text export holds ("form", "report", "query", "macro"), or None."""
    head = data[:600].lstrip(b"\xef\xbb\xbf \r\n")
    if head.startswith(b"Version =") or head.startswith(b"VersionRequired"):
        if re.search(rb"^Begin Form\b", data[:3000], re.M):
            return "form"
        if re.search(rb"^Begin Report\b", data[:3000], re.M):
            return "report"
        if re.search(rb'^\s*Action\s*="', data[:3000], re.M) or b"Begin\r\n    Action" in data[:3000]:
            return "macro"
    if head.startswith(b'dbMemo "SQL"') or (head.startswith(b"Operation =") and b"Begin InputTables" in data[:4000]):
        return "query"
    return None


def access_export_query_sql(data):
    """The SQL of a query exported with SaveAsText: dbMemo "SQL" ="...", continued on "..." lines."""
    m = re.search(rb'dbMemo "SQL" ="((?:[^"\\]|\\.)*)"((?:\r?\n\s+"(?:[^"\\]|\\.)*")*)', data)
    if not m:
        # Saved in design form (Access's query grid): one line per table, column, join and condition.
        return "\n".join(l.decode("latin-1", "replace") for l in re.findall(rb'^    (?:Name|Expression) ="[^\r\n]*', data, re.M))
    raw = m.group(1) + b"".join(re.findall(rb'"((?:[^"\\]|\\.)*)"', m.group(2)))
    text = re.sub(rb"\\([0-7]{3})", lambda o: bytes([int(o.group(1), 8)]), raw).replace(b'\\"', b'"')
    return text.decode("latin-1", "replace")


# ####################
# Access database files
# ####################
# Access's own object types, in its MSysObjects table.
ACCESS_OBJECT_TYPES = {-32768: "forms", -32764: "reports", -32766: "macros", -32761: "modules", 5: "queries",
                       1: "tables", 4: "tables linked over ODBC (e.g. to SQL Server)", 6: "tables linked to other files"}
ACCESS_SQL_CLAUSE = re.compile(r"\b(FROM|WHERE|GROUP BY|HAVING|ORDER BY|UNION|PIVOT|WITH OWNERACCESS)\b", re.I)


def access_sql_lines(sql):
    """Lines of an Access query's SQL as Access shows it: one per clause. (mdbtools gives it on one line.)"""
    if "\n" in sql.strip():
        return count_text_lines(sql)
    outside_quotes = re.sub(r"'[^']*'|\"[^\"]*\"|\[[^\]]*\]", "", sql)
    return (1 + len(ACCESS_SQL_CLAUSE.findall(outside_quotes))) if sql.strip() else 0


def access_format(path):
    """("Access 2007 or later (.accdb)", compiled?) from an Access file's first bytes, or (None, None)."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
            f.seek(0, 2)
            size = f.tell()
    except OSError:
        return None, None
    ext = os.path.splitext(path)[1].lower()
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "Access Data Project (a front end for SQL Server)", ext == ".ade"
    if head[4:19] == b"Standard Jet DB":
        fmt = {0: "Access 97 or earlier (Jet 3)", 1: "Access 2000-2003 (Jet 4)"}.get(head[0x14], "Access (Jet)")
    elif head[4:19] == b"Standard ACE DB":
        fmt = "Access 2007 or later (ACE)"
    else:
        return None, None
    compiled = ext in (".mde", ".accde", ".ade")
    if not compiled and size < 512 * 1024 * 1024:   # an .accde renamed .accdb still says so in its properties
        try:
            with open(path, "rb") as f:
                compiled = b"\x06\x00M\x00D\x00E\x00" in f.read()
        except OSError:
            pass
    return fmt, compiled


# Reading an Access database: on Windows, through Microsoft Access itself (everything, VBA
# included); elsewhere through mdbtools, if installed (everything but the VBA). Always on a
# temporary copy, with Access's macros and code switched off, so nothing in the file runs and
# the original is never touched. If Access won't confirm that they're off, the database isn't
# opened at all.
ACCESS_POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$out = @{}
try { $app = New-Object -ComObject Access.Application } catch { '{"error":"Microsoft Access is not installed"}'; exit }
$secure = $false
try {
  $app.Visible = $false
  try { $app.AutomationSecurity = 3; $secure = ($app.AutomationSecurity -eq 3) } catch {}
  if (-not $secure) { $out.macros_on = $true; throw 'Access could not switch off its macros' }
  $app.OpenCurrentDatabase($args[0], $false)
  $p = $app.CurrentProject
  $out.forms = $p.AllForms.Count; $out.reports = $p.AllReports.Count
  $out.macros = $p.AllMacros.Count; $out.modules = $p.AllModules.Count
  $db = $app.CurrentDb()
  $out.queries = @(foreach ($q in $db.QueryDefs) { @{name = $q.Name; sql = $q.SQL} })
  $tables = @(foreach ($t in $db.TableDefs) { if (-not ($t.Name.StartsWith('MSys') -or $t.Name.StartsWith('~'))) { $t.Connect } })
  $out.tables = $tables.Count
  $out.odbc = @($tables | Where-Object { $_ -like 'ODBC;*' }).Count
  try {
    $out.vba = @(foreach ($c in $app.VBE.ActiveVBProject.VBComponents) {
      $n = $c.CodeModule.CountOfLines
      if ($n -gt 0) { @{type = $c.Type; code = $c.CodeModule.Lines(1, $n)} } })
  } catch { $out.vba_error = $_.Exception.Message }
} catch { $out.error = $_.Exception.Message }
finally {
  if ($secure) { try { $app.CloseCurrentDatabase() } catch {} }
  try { $app.Quit() } catch {}
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
}
$out | ConvertTo-Json -Depth 5 -Compress
"""


def read_access_database(path):
    """{"how", "forms", "reports", "macros", "modules", "tables", "odbc", "queries": [(name, sql)],
    "vba": [code], "error"} for an Access database, read as fully as this computer allows."""
    found = {"how": None, "queries": [], "vba": []}
    if os.name == "nt" and OFFLINE:
        # A database opened in Access can connect to the tables it links to (on a server, or in another
        # database on a network share), by its startup form, say.
        left_out_offline("Access databases' forms, reports and VBA: Microsoft Access, which reads them, could connect to"
                         " the tables a database links to on other computers")
        found["offline"] = True
    elif os.name == "nt":
        # Access may write to a database it opens, so it gets a copy, deleted straight after.
        work = temp_folder("access")
        try:
            copy = os.path.join(work, os.path.basename(path))
            shutil.copyfile(path, copy)
            found.update(read_access_with_access(copy, work))
        except OSError as e:
            found["error"] = scrub(e)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    if found["how"] is None and tool_path("mdb-tables"):
        found.update(read_access_with_mdbtools(path))   # mdbtools only reads: no copy needed
    return found


def read_access_with_access(copy, work):
    script = os.path.join(work, "read_access.ps1")
    with open(script, "w", encoding="utf-8-sig") as f:
        f.write(ACCESS_POWERSHELL)
    out = run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script, copy],
              work, 600)
    try:
        got = json.loads(out or "")
    except ValueError:
        return {}
    if isinstance(got, dict) and got.get("macros_on"):
        return {"macros_on": True}
    if not isinstance(got, dict) or got.get("error") and "forms" not in got:
        return {"error": scrub(got["error"]) if isinstance(got, dict) and got.get("error") else None}
    as_list = lambda v: v if isinstance(v, list) else ([v] if v else [])   # ConvertTo-Json unwraps 1-item lists
    return {"how": "Microsoft Access", "forms": got.get("forms", 0), "reports": got.get("reports", 0),
            "macros": got.get("macros", 0), "modules": got.get("modules", 0), "tables": got.get("tables", 0),
            "odbc": got.get("odbc", 0),
            "queries": [(q.get("name", ""), q.get("sql") or "") for q in as_list(got.get("queries")) if isinstance(q, dict)],
            "vba": [c.get("code") or "" for c in as_list(got.get("vba")) if isinstance(c, dict)],
            "vba_error": scrub(got["vba_error"]) if got.get("vba_error") else None}


def read_access_with_mdbtools(path):
    """The queries and the list of objects (MSysObjects, Access's catalog). Never a table's rows."""
    names = run(["mdb-queries", "-L", "-1", path], os.path.dirname(path), 120)
    if names is None:
        return {}
    queries = []
    for name in [n for n in names.splitlines() if n.strip()]:
        queries.append((name, run(["mdb-queries", path, name], os.path.dirname(path), 60) or ""))
    counts = Counter()
    objects = run(["mdb-export", path, "MSysObjects"], os.path.dirname(path), 120) or ""
    import csv
    import io
    for row in csv.DictReader(io.StringIO(objects.replace("\0", ""))):
        try:
            kind = ACCESS_OBJECT_TYPES.get(int(row.get("Type") or 0))
        except ValueError:
            continue
        name = row.get("Name") or ""
        if kind and not name.startswith(("MSys", "~", "f_", "USys")):
            counts[kind] += 1
    return {"how": "mdbtools", "forms": counts["forms"], "reports": counts["reports"], "macros": counts["macros"],
            "modules": counts["modules"], "tables": counts["tables"] + counts["tables linked to other files"],
            "odbc": counts["tables linked over ODBC (e.g. to SQL Server)"], "queries": queries, "vba": []}


# ##############################
# During the walk
# ##############################

def database_code_facts(path, ext, data, lines):
    """For Visual Basic, Access objects exported as text, and SQL scripts: their real code lines
    ("lines"), "language", "access_object" (form, report, query, macro), "sql_objects" and
    whether a script is really data ("data")."""
    found = {}
    if ext in ACCESS_EXPORT_EXTS:
        kind = access_export(data)
        if kind:
            found["access_object"] = kind
            found["data"] = False   # a form's layout holds hex blobs (printer settings ...): not pasted-in data
            if kind in ("form", "report"):
                marker = b"CodeBehindForm" if kind == "form" else b"CodeBehindReport"
                code = data.split(marker, 1)[1] if marker in data else b""
                found["lines"] = len([l for l in text_lines(code) if not l.startswith(b"Attribute VB_")])
                found["language"] = "VBA (in Access forms and reports)"
            elif kind == "query":
                exported_sql = os.path.splitext(path)[0] + ".sql"   # the vcs add-in saves the SQL beside it
                found["lines"] = 0 if os.path.exists(exported_sql) else count_text_lines(access_export_query_sql(data))
                found["language"] = "SQL (in Access queries)"
            else:
                found["lines"] = 0
                found["language"] = None
            return found
    if ext in VB_EXTS:
        if not looks_like_vb(data):
            return {"lines": 0, "language": None}
        found["lines"] = len(vb_code_lines(lines, ext))
        found["language"] = ("VBA (Access)" if b"Option Compare Database" in data else
                             "Visual Basic 6" if re.search(rb"^Begin VB\.", data[:2000], re.M) else None)
    if ext in (".sql", ".tsql"):
        found["sql_objects"] = sql_objects(data)
        inserts = sql_data_lines(text_lines(data))
        if inserts:
            found["data_lines"] = inserts
            found["lines"] = len(lines) - inserts
    return found


SQL_SERVER_BACKUP_EXTS = {".bak", ".trn"}


def is_sql_server_backup(path):
    """Is this .bak / .trn file a SQL Server backup? Those are in Microsoft Tape Format, which
    begins with a TAPE block; many other programs name their backup copies .bak."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"TAPE"
    except OSError:
        return False


def database_file(path, ext, name, category, st, dbcode, dac_packages, lines_by, assets):
    """Counts what's in a database file: an Access database, a SQL Server database file or backup,
    a .dacpac / .bacpac package, or an SSIS package / SSRS report."""
    mine = category in ("own", "test")
    c = "own" if category == "test" else category
    if ext in ACCESS_EXTS:
        fmt, compiled = access_format(path)
        assets["Access databases"] += 1
        if not fmt or not mine:
            return
        dbcode.data["Access databases (their tables are in the same file as the code)"] += 1
        dbcode.data_bytes["Access databases (their tables are in the same file as the code)"] += st.st_size
        progress(f"Reading the Access database {name} ...")
        got = read_access_database(path)
        progress()
        got["category"] = c
        dbcode.access.append((fmt, compiled, got))   # its code is counted after the walk: see count_access_code
    elif ext in SQL_SERVER_FILES:
        if ext in SQL_SERVER_BACKUP_EXTS and not is_sql_server_backup(path):
            return   # some other program's backup copy (an editor's, a game engine's ...), not a database
        if mine:
            dbcode.server_files[SQL_SERVER_FILES[ext]] += 1
            dbcode.server_bytes += st.st_size
            dbcode.data["SQL Server databases and backups (.mdf, .bak ...)"] += 1
            dbcode.data_bytes["SQL Server databases and backups (.mdf, .bak ...)"] += st.st_size
    elif ext in DAC_EXTS:
        try:
            got = read_dac_package(path)
        except Exception:   # not a package after all, or a damaged one
            return
        if mine:
            dbcode.dac.update(got["objects"])
            dac_packages.append((c, got))
            if ext == ".bacpac":   # the schema and every table's rows; only the schema was read
                dbcode.data[".bacpac exports (they hold every table's rows too)"] += 1
                dbcode.data_bytes[".bacpac exports (they hold every table's rows too)"] += st.st_size
    else:   # SSIS packages (.dtsx, or a whole project in an .ispac) and SSRS reports
        texts = []
        if ext == ".ispac":
            import zipfile
            try:
                with zipfile.ZipFile(path) as z:
                    texts = [z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.lower().endswith(".dtsx")]
            except Exception:
                return
        else:
            try:
                with open(path, "rb") as f:
                    texts = [f.read().decode("utf-8", "replace")]
            except OSError:
                return
        for text in texts:
            ssis = ext in (".dtsx", ".ispac")
            got = ssis_package_code(text) if ssis else ssrs_report_code(text)
            where = "SSIS packages" if ssis else "SSRS reports"
            if mine:
                counts = dbcode.ssis if ssis else dbcode.ssrs
                counts["packages" if ssis else "reports"] += 1
                counts["SQL statements" if ssis else "queries"] += len(got["sql"])
                counts["script tasks" if ssis else "code blocks"] += len(got["scripts"])
            for sql in got["sql"]:
                lines_by[c][f"SQL (in {where})"][0] += 1
                lines_by[c][f"SQL (in {where})"][1] += count_text_lines(sql)
            for language, code in got["scripts"]:
                label = f"{language} (in SSIS script tasks)" if ssis else f"{language} (in SSRS reports)"
                lines_by[c][label][0] += 1
                lines_by[c][label][1] += count_text_lines(code)


def count_access_code(dbcode, lines_by):
    """The code inside Access databases, unless the project also holds the same database exported
    as text (then that's what was counted, line by line, and the binary would count it twice)."""
    exported_forms = dbcode.access_exports.get("forms", 0) + dbcode.access_exports.get("reports", 0)
    for _, _, got in dbcode.access:
        objects = got.get("forms", 0) + got.get("reports", 0)
        if exported_forms and objects and exported_forms >= objects / 2:
            got["exported"] = True
            continue
        c = got.get("category", "own")
        for qname, sql in got.get("queries", []):
            lang = "SQL (in Access forms and reports)" if qname.startswith("~") else "SQL (in Access queries)"
            lines_by[c][lang][0] += 1
            lines_by[c][lang][1] += access_sql_lines(sql)
        for code in got.get("vba", []):
            lines_by[c]["VBA (in Access databases)"][0] += 1
            lines_by[c]["VBA (in Access databases)"][1] += count_text_lines(code)


# ##############################
# Collecting and reporting
# ##############################

class DatabaseCode:
    """Collects, during the walk, what the project's databases hold."""

    def __init__(self):
        self.data = Counter()           # files holding data rather than code, by kind
        self.data_bytes = Counter()
        self.access = []                # (format, compiled?, contents from read_access_database)
        self.access_exports = Counter()  # Access objects exported as text: "forms", "reports" ...
        self.sql_files = Counter()      # objects defined in .sql scripts, by kind
        self.sql_keys = set()           # their names, so the same object isn't counted twice
        self.sql_defined = set()        # (kind, name) already counted
        self.dac = Counter()            # objects in .dacpac / .bacpac packages
        self.ssis = Counter()           # "packages", "SQL statements", "script tasks"
        self.ssrs = Counter()           # "reports", "queries", "code blocks"
        self.server_files = Counter()   # SQL Server database files and backups, by kind
        self.server_bytes = 0
        self.live = None                # what --sql-server found

    # ####################
    # The report
    # ####################

    def report(self):
        # ####################
        # Access
        # ####################
        out = []
        for fmt, compiled, got in self.access:
            numbers = dict(got, queries=sum(1 for name, _ in got.get("queries", []) if not name.startswith("~")))
            parts = [counted(numbers[k], k) for k in ("forms", "reports", "queries", "macros", "modules", "tables")
                     if numbers.get(k)]
            line = f"  Microsoft Access, {fmt}" + (" (compiled: its VBA source has been removed)" if compiled else "")
            out.append(line + (": " + ", ".join(parts) if parts else ""))
            if got.get("odbc"):
                out.append(f"    {got['odbc']:,} of its tables are linked over ODBC, e.g. to SQL Server: the data lives there")
            if got.get("exported"):
                out.append("    (its code is counted from the copy exported as text, below, so not twice)")
            if got.get("how") == "mdbtools":
                out.append("    (read with mdbtools: VBA can only be read by Microsoft Access, on Windows)")
            elif got.get("macros_on"):
                out.append("    (not opened: Microsoft Access couldn't switch off the database's macros and code, so it"
                           " wasn't opened, to be safe)")
            elif got.get("offline"):
                out.append("    (not opened with Microsoft Access, because of --offline: opening it could connect to the"
                           " tables it links to on other computers)")
            elif got.get("how") is None:
                out.append("    (not opened: run this on Windows with Microsoft Access installed to count its forms,"
                           " reports, queries and VBA)")
            elif got.get("vba_error"):
                out.append(f"    (its VBA couldn't be read: {got['vba_error']})")
        if self.access_exports:
            kinds = ("forms", "reports", "queries", "macros")
            out.append("  Access objects exported as text: " + ", ".join(counted(self.access_exports[k], k) for k in kinds
                                                                          if self.access_exports.get(k)))
            if self.access_exports.get("queries"):
                out.append("    (queries saved in Access's design form count one line per table, column, join and condition)")

        # ####################
        # SQL Server
        # ####################
        for label, counts in (("SQL Server objects defined in .sql files", self.sql_files),
                              ("In .dacpac / .bacpac packages", self.dac)):
            if counts:
                out.append(f"  {label}: " + ", ".join(counted(n, k) for k, n in counts.most_common()))
        if self.live:
            if self.live.get("error"):
                out.append(f"  SQL Server (--sql-server): {self.live['error']}")
            else:
                out.append(f"  In the running SQL Server ({plural(self.live['databases'], 'database')}): "
                           + ", ".join(counted(n, k) for k, n in self.live["objects"].most_common())
                           + (", " + counted(self.live["tables"], "tables") if self.live.get("tables") else ""))

        # ####################
        # SSIS and SSRS
        # ####################
        if self.ssis:
            out.append("  SSIS (Integration Services): " + ", ".join(counted(n, k) for k, n in self.ssis.items()))
        if self.ssrs:
            out.append("  SSRS (Reporting Services): " + ", ".join(counted(n, k) for k, n in self.ssrs.items()))

        # ####################
        # Heading, and what couldn't be read
        # ####################
        if out:
            out.insert(0, "Databases (their code is counted above, as the languages marked \"in ...\"; only code and the"
                          " list of objects were read, never the rows in a table):")
            out.insert(0, "")
        if self.server_files:
            out += ["", "NOTE: SQL Server " + ", ".join(f"{k} ({n:,})" for k, n in self.server_files.items())
                    + f", {self.server_bytes / 1e9:.1f} GB: the code inside them (stored procedures, views,",
                    "      functions, triggers) can't be read from the files. Run this again with --sql-server <server>",
                    "      on a computer that can reach the server, or export just the code (see below)."]
        out += self.data_report()
        return out

    def data_report(self):
        """The files that hold data (perhaps customers' data) rather than code: what's for sale is the
        code, so these should stay out of what's shared, and how to share the code without them."""
        if not self.data:
            return []
        out = ["", "Files holding data (perhaps customers' data): keep these out of what's shared with a buyer;"
                   " the code is what's for sale:"]
        out += [f"  {kind:<62} {plural(n, 'file'):>11}  {self.data_bytes[kind] / 1e6:>10,.1f} MB"
                for kind, n in self.data.most_common()]
        out.append("  To share the code without the data:")
        if any("SQL Server" in k or ".bacpac" in k or "INSERT" in k for k in self.data):
            out += ["    SQL Server: in SQL Server Management Studio, the database > Tasks > Generate Scripts, with",
                    "      \"Types of data to script\" left on \"Schema only\"; or Extract Data-tier Application, which",
                    "      makes a .dacpac (code and table definitions only; a .bacpac would hold the rows too)."]
        if any("Access" in k for k in self.data):
            out += ["    Access: export its forms, reports, queries, macros and modules as text (e.g. with the free",
                    "      msaccess-vcs add-in), or share a copy with the tables emptied, or only the front end of a",
                    "      split database (the back end holds the data)."]
        if any("Data files" in k for k in self.data):
            out += ["    Data files: leave them out, or swap in made-up sample data."]
        return out


# #######################################
# Dependencies
# #######################################

# What the code needs that isn't in the folder: headers it includes that aren't here, libraries
# its build files point to elsewhere, and the packages its package lists name. A project built
# on a studio's own engine kept in another place (or lost) shows up here.

# ##############################
# Known headers and libraries
# ##############################
# Headers that come with the compiler or the operating system, never part of a codebase.
SYSTEM_HEADERS = set("""
algorithm any array atomic barrier bit bitset cassert ccomplex cctype cerrno cfenv cfloat charconv chrono cinttypes
ciso646 climits clocale cmath codecvt compare complex concepts condition_variable coroutine csetjmp csignal cstdalign
cstdarg cstdbool cstddef cstdint cstdio cstdlib cstring ctgmath ctime cuchar cwchar cwctype deque exception execution
expected filesystem format forward_list fstream functional future generator initializer_list iomanip ios iosfwd
iostream istream iterator latch limits list locale map mdspan memory memory_resource mutex new numbers numeric optional
ostream print queue random ranges ratio regex scoped_allocator semaphore set shared_mutex source_location span
spanstream sstream stack stacktrace stdexcept stop_token streambuf string string_view strstream syncstream system_error
thread tuple type_traits typeindex typeinfo unordered_map unordered_set utility valarray variant vector version
hash_map hash_set ext
assert.h complex.h ctype.h errno.h fenv.h float.h inttypes.h iso646.h limits.h locale.h math.h setjmp.h signal.h
stdalign.h stdarg.h stdatomic.h stdbool.h stddef.h stdint.h stdio.h stdlib.h stdnoreturn.h string.h tgmath.h
threads.h time.h uchar.h wchar.h wctype.h malloc.h memory.h alloca.h search.h
unistd.h pthread.h dirent.h fcntl.h dlfcn.h netdb.h poll.h sched.h semaphore.h termios.h syslog.h pwd.h grp.h
strings.h libgen.h glob.h fnmatch.h getopt.h execinfo.h utime.h ucontext.h spawn.h iconv.h langinfo.h nl_types.h
regex.h wordexp.h ifaddrs.h err.h endian.h byteswap.h features.h elf.h link.h cpuid.h
sys netinet arpa net mach mach-o linux asm libkern machine os dispatch xpc objc
windows.h winsock.h winsock2.h ws2tcpip.h ws2def.h windowsx.h winbase.h winuser.h windef.h winnt.h winerror.h
wtypes.h tchar.h shlobj.h shellapi.h shlwapi.h objbase.h ole2.h oleauto.h olectl.h comdef.h comutil.h commctrl.h
commdlg.h mmsystem.h mmreg.h msacm.h process.h io.h direct.h conio.h crtdbg.h share.h fcntl.h excpt.h
wininet.h winhttp.h iphlpapi.h psapi.h tlhelp32.h dbghelp.h imagehlp.h winreg.h winver.h richedit.h uxtheme.h
dwmapi.h setupapi.h devguid.h hidsdi.h hidusage.h ntsecapi.h sddl.h aclapi.h lmcons.h wincrypt.h bcrypt.h
ncrypt.h userenv.h wtsapi32.h powrprof.h versionhelpers.h sdkddkver.h targetver.h strsafe.h intsafe.h
atlbase.h atlstr.h atlcom.h atlwin.h atlconv.h atltypes.h atlimage.h comip.h exdisp.h mshtml.h ocidl.h
d3d9.h d3d9types.h d3d10.h d3d10_1.h d3d11.h d3d11_1.h d3d12.h dxgi.h dxgi1_2.h dxgi1_4.h dxgi1_6.h d3dcompiler.h
d3dcommon.h dinput.h xinput.h dsound.h xaudio2.h x3daudio.h xapofx.h mfapi.h mfidl.h mfreadwrite.h dwrite.h d2d1.h
wincodec.h wrl dbt.h ks.h ksmedia.h mmdeviceapi.h audioclient.h endpointvolume.h functiondiscoverykeys_devpkey.h
intrin.h xmmintrin.h emmintrin.h pmmintrin.h tmmintrin.h smmintrin.h nmmintrin.h immintrin.h ammintrin.h
arm_neon.h float.h ppl.h concrt.h
foundation uikit appkit cocoa corefoundation coregraphics coreaudio coremidi coreservices coretext coreimage
corevideo coremotion corelocation quartzcore metal metalkit opengl opengles audiotoolbox audiounit avfoundation
gamekit gamecontroller storekit carbon iokit security systemconfiguration accelerate webkit mediaplayer
gl khr egl gles gles2 gles3
""".split())
# The usual first folder of a library's headers, or the start of its header names, and its name.
INCLUDE_LIBRARIES = [
    (r"boost", "Boost"), (r"ogre|ogre\w+", "Ogre"), (r"bt[A-Z]\w*\.h|bullet\w*|LinearMath|BulletCollision|BulletDynamics",
                                                     "Bullet Physics"),
    (r"Px\w*\.h|physx|PxPhysicsAPI\.h", "PhysX"), (r"SFML", "SFML"), (r"SDL\w*", "SDL"), (r"glm", "GLM"),
    (r"imgui\w*", "Dear ImGui"), (r"lua(conf|lib)?\.h|lauxlib\.h|lualib\.h|lua\.hpp|luajit\w*", "Lua"),
    (r"fmod\w*", "FMOD"), (r"AK", "Wwise"), (r"steam|steam_api\w*\.h|isteam\w+\.h", "Steamworks"),
    (r"openssl", "OpenSSL"), (r"curl", "curl"), (r"google", "Google libraries (protobuf, breakpad ...)"),
    (r"gtest|gmock", "GoogleTest"), (r"Eigen", "Eigen"), (r"rapidjson", "RapidJSON"), (r"nlohmann|json\.hpp", "nlohmann/json"),
    (r"fmt", "fmt"), (r"spdlog", "spdlog"), (r"Poco", "POCO"), (r"Qt\w*|Q[A-Z]\w+", "Qt"), (r"cocos2d|cocos", "cocos2d-x"),
    (r"MyGUI\w*", "MyGUI"), (r"CEGUI\w*", "CEGUI"), (r"OIS\w*", "OIS"), (r"RakNet|Rak[A-Z]\w*\.h", "RakNet"),
    (r"enet", "ENet"), (r"zlib\.h|zconf\.h", "zlib"), (r"png\.h|pngconf\.h", "libpng"), (r"jpeglib\.h|jconfig\.h", "libjpeg"),
    (r"ft2build\.h|freetype", "FreeType"), (r"vorbis|ogg", "Ogg Vorbis"), (r"AL", "OpenAL"), (r"Python\.h|python\d*", "Python"),
    (r"squirrel\.h|sqstd\w*\.h", "Squirrel"), (r"angelscript\.h", "AngelScript"), (r"tinyxml\w*\.h", "TinyXML"),
    (r"pugixml\.hpp|pugiconfig\.hpp", "pugixml"), (r"stb_\w+\.h", "stb"), (r"GL/glew\.h|glew\.h|GL/glut\.h|GL/freeglut\w*",
                                                                          "GLEW / GLUT"),
    (r"GLFW", "GLFW"), (r"vulkan", "Vulkan SDK"), (r"d3dx\w*\.h|dxerr\w*\.h", "DirectX SDK (legacy)"),
    (r"speex", "Speex"), (r"miniupnpc\w*", "miniupnpc"), (r"otlv4\.h", "OTL"), (r"cryptopp|crypto\+\+", "Crypto++"),
    (r"client/windows|breakpad", "Breakpad"), (r"mono", "Mono"), (r"recast\w*|detour\w*|Recast\w*\.h|Detour\w*\.h",
                                                                   "Recast & Detour"),
    (r"assimp", "Assimp"), (r"fbxsdk\w*", "FBX SDK"), (r"sqlite3\.h", "SQLite"), (r"opus", "Opus"), (r"theora", "Theora"),
    (r"openvr\w*\.h", "OpenVR"), (r"OVR\w*\.h|LibOVR", "Oculus SDK"), (r"havok|Common/Base", "Havok"),
    (r"Scaleform|GFx\w*\.h", "Scaleform"), (r"bink\w*\.h", "Bink"), (r"tbb", "TBB"), (r"lz4\w*\.h", "LZ4"),
    (r"zstd\.h", "zstd"), (r"yaml-cpp", "yaml-cpp"), (r"json/json\.h|jsoncpp", "JsonCpp"), (r"asio", "Asio"),
    (r"websocketpp", "WebSocket++"), (r"uv\.h", "libuv"), (r"bgfx|bx|bimg", "bgfx"), (r"cuda\w*\.h", "CUDA"),
    (r"opencv\d*", "OpenCV"), (r"nvapi\.h", "NVAPI"), (r"discord\w*\.h", "Discord SDK"), (r"EOS\w*|eos_\w+\.h", "Epic Online Services"),
]
INCLUDE_LIBRARIES = [(re.compile(rf"^(?:{pattern})$", re.I), name) for pattern, name in INCLUDE_LIBRARIES]
# Other libraries, by the name of the folder they usually come in.
KNOWN_LIBRARY_NAMES = {
    "ogre", "ogre3d", "bullet", "boost", "physx", "sfml", "speex", "steamworks", "steam", "zlib", "crypto++", "cryptopp",
    "google-breakpad", "breakpad", "crashpad", "crashrpt", "miniupnpc", "mygui", "otl", "python", "lua", "luajit",
    "sdl", "sdl2", "sdl3", "glfw", "glew", "glut", "freeglut", "opengl", "directx", "dxsdk", "directx sdk", "fmod",
    "fmodstudio", "wwise", "openal", "openal-soft", "ogg", "vorbis", "libogg", "libvorbis", "theora", "libtheora",
    "freetype", "libpng", "png", "jpeg", "libjpeg", "libjpeg-turbo", "curl", "libcurl", "openssl", "raknet", "enet",
    "cegui", "ois", "imgui", "havok", "scaleform", "bink", "speedtree", "umbra", "simplygon", "recast", "detour",
    "recastnavigation", "assimp", "fbx", "fbxsdk", "fbx sdk", "qt", "wxwidgets", "tinyxml", "tinyxml2", "rapidjson",
    "protobuf", "gtest", "googletest", "mono", "vulkan", "vulkansdk", "angelscript", "squirrel", "pugixml", "eigen",
    "glm", "opus", "sqlite", "sqlite3", "nvtt", "pthreads", "pthreads-win32", "icu", "harfbuzz", "libxml2", "expat",
    "jsoncpp", "yaml-cpp", "poco", "asio", "websocketpp", "libuv", "bgfx", "stb", "portaudio", "rtaudio", "oculus",
    "libovr", "ovr", "openvr", "lz4", "zstd", "xz", "lzma", "7zip", "libzip", "minizip", "bzip2", "flac", "mpg123",
    "libvpx", "ffmpeg", "pcre", "re2", "tbb", "cuda", "opencv", "nvapi", "ags", "granny", "miles", "oodle",
    "directxtk", "directxtex", "directxmath", "dxut", "effects11", "fx11", "discord", "discord_game_sdk", "eos",
    "gameanalytics", "firebase", "facebook", "galaxy", "gog galaxy", "spine", "spine-cpp", "box2d", "chipmunk",
    "cocos2d", "cocos2d-x", "sfml", "allegro", "irrlicht", "horde3d", "openscenegraph", "osg", "torque", "nvidia",
    "hydra", "cg", "nvidia cg", "glsl", "angle", "libsndfile", "libmad", "libsamplerate", "cpprest", "cpprestsdk",
    "grpc", "protobuf", "thrift", "msgpack", "flatbuffers", "cereal", "nanovg", "libwebsockets", "uwebsockets",
    "mbedtls", "libsodium", "wolfssl", "nghttp2", "c-ares", "cares", "libevent", "libev",
    "unreal engine", "godot", "source sdk", "cryengine",
} | KNOWN_LIBRARY_DIRS


# ##############################
# Naming a dependency
# ##############################
# Path components that say where a library is, not which one.
PATH_NOISE = {
    "", ".", "..", "include", "includes", "inc", "lib", "libs", "library", "libraries", "src", "source", "sources",
    "public", "build", "bin", "release", "debug", "x64", "x86", "win32", "win64", "arm64", "output", "stage",
    "dependencies", "dependency", "deps", "dep", "external", "externals", "extern", "thirdparty", "third_party",
    "third-party", "vendor", "vendors", "sdk", "sdks", "redistributable_bin", "msvc", "vc", "platforms", "components",
    "plugins", "**", "*", "usr", "local", "opt", "program files", "program files (x86)", "lib64", "common", "code",
    "dev", "projects", "c:", "d:", "e:", "f:", "packages", "native", "windows", "linux", "mac", "macos", "android",
    "ios", "main", "core", "api", "headers", "header", "frameworks", "framework",
}
PERSONAL_FOLDERS = {"users", "home", "documents", "desktop", "downloads", "my documents", "onedrive", "dropbox",
                    "google drive", "icloud drive"}
VERSIONED_NAME = re.compile(r"^(.+?)[ _-]v?(\d+(?:[._]\d+)*[a-z]{0,3}\d*)$", re.I)


def dependency_name(path):
    """The library a path outside the project points to, e.g. ".../boost_1_55_0/stage/lib" ->
    "boost 1.55.0". None if the path says nothing (or only someone's personal folders)."""
    variables = re.findall(r"\$\((\w+)\)|\$\{(\w+)\}|%(\w+)%", path)
    on_share = path.strip().startswith(("\\\\", "//"))
    path = re.sub(r"\$\([^)]*\)|\$\{[^}]*\}|%[^%]+%|\$\w+", "", path).replace("\\", "/")
    parts = [p for p in path.split("/") if p.strip()]
    if on_share:   # \\server\share\...: a computer's name isn't for the report
        parts = parts[2:]
    if not any(p.strip().lower() not in PATH_NOISE for p in parts):
        # Only a variable: its name may say which library, e.g. $(DXSDK_DIR) or %BOOST_ROOT%.
        for var in (v for group in variables for v in group if v):
            name = re.sub(r"_(DIR|ROOT|PATH|HOME|INCLUDE|INC|LIB|LIBS)$", "", var, flags=re.I)
            if name and name.upper() not in ("SOLUTION", "PROJECT", "OUT", "INT", "CONFIGURATION", "PLATFORM",
                                             "TARGET", "OUTPUT", "INTERMEDIATE", "USERPROFILE", "HOME", "CMAKE_CURRENT_SOURCE",
                                             "CMAKE_SOURCE", "CMAKE_BINARY", "PROJECT_SOURCE", "CMAKE_CURRENT_LIST",
                                             "VCINSTALL", "WINDOWSSDK", "UNIVERSALCRT", "NETFXKIT", "VC", "SOLUTIONDIR",
                                             "PROJECTDIR"):
                return name
        return None
    skip_next = False
    for part in parts:
        low = part.strip().lower()
        if skip_next:
            skip_next = False
            continue
        if low in PERSONAL_FOLDERS:
            skip_next = low in ("users", "home")   # the next one is a person's name
            continue
        if low.startswith(("dropbox", "onedrive")) or low in PATH_NOISE or re.fullmatch(r"vs\d{4}|v\d{3}|[a-z]:", low):
            continue
        m = VERSIONED_NAME.match(part.strip())
        if m and not m.group(1).isdigit():
            return f"{m.group(1)} {m.group(2).replace('_', '.')}"
        return part.strip()
    return None


def dependency_key(name):
    """Groups "boost 1.55.0", "Boost" and "boost_1_55_0/stage" together."""
    base = re.split(r"[ _-]v?\d", name, maxsplit=1)[0]
    key = re.sub(r"[^a-z0-9+]", "", base.lower())
    return (re.sub(r"(?<=[a-z+])\d+$", "", key) or key) or name.lower()   # "Python27" -> "python"


def is_known_library(name):
    key = dependency_key(name)
    return key in {re.sub(r"[^a-z0-9+]", "", n) for n in KNOWN_LIBRARY_NAMES} or \
        any(rx.match(name) or rx.match(key) for rx, _ in INCLUDE_LIBRARIES)


# ##############################
# Build files and package lists
# ##############################
BUILD_FILE = re.compile(r"^(premake\d?\.lua|.*\.premake\.lua|cmakelists\.txt|.*\.cmake|.*\.vcxproj|.*\.vcproj|"
                        r"makefile|gnumakefile|.*\.mk|sconstruct|sconscript|meson\.build|project\.pbxproj|.*\.props)$",
                        re.I)


def build_file_paths(path, name):
    """[(path, kind)] that a build file uses: include and library folders ("dir"), and packages
    found by name ("package": CMake's find_package, pkg-config ...)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read(2_000_000)
    except OSError:
        return []
    low = name.lower()
    found = []
    quoted = r"\"([^\"\n]+)\"|'([^'\n]+)'"
    if low.endswith(".lua"):   # premake: includedirs { "a", "b" }, libdirs { ... }
        for block in re.findall(r"(?:sys|external)?(?:includedirs|libdirs)\s*\{([^}]*)\}", text):
            found += [(a or b, "dir") for a, b in re.findall(quoted, block)]
    elif low == "cmakelists.txt" or low.endswith(".cmake"):
        found += [(m, "package") for m in re.findall(r"find_package\s*\(\s*([A-Za-z0-9_+.-]+)", text, re.I)]
        found += [(m, "package") for m in re.findall(r"(?:FetchContent_Declare|ExternalProject_Add)\s*\(\s*([A-Za-z0-9_+.-]+)",
                                                     text, re.I)]
        for block in re.findall(r"(?:include_directories|target_include_directories|link_directories)\s*\(([^)]*)\)",
                                text, re.I):
            found += [(p, "dir") for p in re.split(r"\s+", block.replace('"', " "))
                      if p and p.upper() not in ("PUBLIC", "PRIVATE", "INTERFACE", "SYSTEM", "BEFORE", "AFTER")]
    elif low.endswith((".vcxproj", ".vcproj", ".props")):
        for value in re.findall(r"(?:AdditionalIncludeDirectories|AdditionalLibraryDirectories|IncludePath|LibraryPath)"
                                r"(?:=\"|>)([^\"<]+)", text):
            found += [(p, "dir") for p in value.split(";") if p and not p.startswith("%(")]
    elif low.endswith("pbxproj"):
        for block in re.findall(r"(?:HEADER_SEARCH_PATHS|LIBRARY_SEARCH_PATHS|FRAMEWORK_SEARCH_PATHS)\s*=\s*\(?([^;]*)",
                                text):
            found += [(a or b, "dir") for a, b in re.findall(quoted, block)]
    elif low == "meson.build":
        found += [(m, "package") for m in re.findall(r"dependency\s*\(\s*['\"]([^'\"]+)['\"]", text)]
    else:   # Makefiles and SCons: -I/-L flags, pkg-config packages
        found += [(m, "dir") for m in re.findall(r"(?:^|\s)-[IL]\s*([^\s\"'$()]+)", text, re.M)]
        found += [(m, "package") for m in re.findall(r"pkg-config\s+--(?:cflags|libs)(?:\s+--\w+)*\s+([A-Za-z0-9_.+-]+)",
                                                     text)]
    return found


MANIFEST_FILE = re.compile(r"^(package\.json|vcpkg\.json|requirements[\w.-]*\.txt|pyproject\.toml|cargo\.toml|"
                           r".*\.(csproj|fsproj|vbproj|uproject)|packages\.config|conanfile\.txt|go\.mod|"
                           r"build\.gradle(\.kts)?|pom\.xml)$", re.I)


def manifest_dependencies(path, name):
    """[(ecosystem, package)] named in a package list (npm, pip, Cargo, NuGet, vcpkg, Conan, Unity,
    Unreal ...)."""
    low = name.lower()
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            text = f.read(2_000_000)
    except OSError:
        return []
    out = []
    try:
        if low == "package.json":
            j = json.loads(text)
            out += [("npm", n) for key in ("dependencies", "devDependencies") for n in (j.get(key) or {})]
        elif low == "manifest.json" and os.path.basename(os.path.dirname(path)).lower() == "packages":
            out += [("Unity package", n) for n in (json.loads(text).get("dependencies") or {})]
        elif low.endswith(".uproject") or low.endswith(".uplugin"):
            for p in json.loads(text).get("Plugins") or []:
                if p.get("Enabled", True) and (p.get("MarketplaceURL") or p.get("FabURL")):
                    out.append(("Unreal Marketplace plugin", p.get("Name", "?")))
        elif low == "vcpkg.json":
            out += [("vcpkg", d if isinstance(d, str) else d.get("name", "?")) for d in json.loads(text).get("dependencies") or []]
        elif re.fullmatch(r"requirements[\w.-]*\.txt", low):
            out += [("Python (pip)", m) for m in re.findall(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", text, re.M)]
        elif low == "pyproject.toml":
            block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.M | re.S)
            out += [("Python (pip)", m) for m in re.findall(r"[\"']([A-Za-z0-9][A-Za-z0-9._-]*)", block.group(1))] if block else []
        elif low == "cargo.toml":
            block = re.search(r"^\[dependencies\](.*?)(?=^\[|\Z)", text, re.M | re.S)
            out += [("Rust (Cargo)", m) for m in re.findall(r"^([A-Za-z0-9_-]+)\s*=", block.group(1), re.M)] if block else []
        elif low.endswith((".csproj", ".fsproj", ".vbproj")):
            out += [("NuGet", m) for m in re.findall(r"<PackageReference\s+Include=\"([^\"]+)\"", text)]
        elif low == "packages.config":
            out += [("NuGet", m) for m in re.findall(r"<package\s+id=\"([^\"]+)\"", text)]
        elif low == "conanfile.txt":
            block = re.search(r"^\[requires\](.*?)(?=^\[|\Z)", text, re.M | re.S)
            out += [("Conan", m.split("/")[0]) for m in re.findall(r"^\s*(\S+/\S+)", block.group(1), re.M)] if block else []
        elif low == "go.mod":
            out += [("Go", m) for m in re.findall(r"^\s*(?:require\s+)?([a-z0-9.-]+\.[a-z]+/\S+)\s+v\d", text, re.M)]
        elif low in ("build.gradle", "build.gradle.kts"):
            out += [("Java (Gradle)", m) for m in re.findall(r"(?:implementation|api|compile)\s*\(?\s*['\"]([^:'\"]+:[^:'\"]+)",
                                                             text)]
        elif low == "pom.xml":
            out += [("Java (Maven)", m) for m in re.findall(r"<artifactId>([^<]+)</artifactId>", text)[1:]]
    except (ValueError, AttributeError):
        pass
    return out


# ##############################
# Collecting and reporting
# ##############################

class Dependencies:
    """Collects, while the folder is walked, what the code needs from outside it."""

    def __init__(self, root):
        self.root = root
        self.files = defaultdict(list)    # basename (lowercase) -> [path relative to root, lowercase, "/"]
        self.includes = Counter()         # "#include" path -> how many times (own code only)
        self.engine_includes = {}         # "#include" path -> engine, for code in an engine's project
        self.build = defaultdict(set)     # library name -> {"build file", "include"}
        self.packages = defaultdict(set)  # ecosystem -> {package}

    # ####################
    # During the walk
    # ####################

    def saw_file(self, rel_path):
        rel = rel_path.replace(os.sep, "/").lower()
        self.files[rel.rsplit("/", 1)[-1]].append(rel)

    def saw_build_file(self, path, name):
        here = os.path.dirname(path)
        for value, kind in build_file_paths(path, name):
            if kind == "package":
                self.build[value].add("build file")
                continue
            clean = re.sub(r"\$\([^)]*\)|\$\{[^}]*\}|%[^%]+%", "", value).strip()
            local = os.path.normpath(os.path.join(here, clean)) if clean and not os.path.isabs(clean) else None
            # Only paths inside the project are looked for: a build file can name any folder, even
            # one on another computer.
            if clean in ("", ".", "./") or (local and is_within(local, self.root) and os.path.exists(local)):
                continue   # inside the project
            dep = dependency_name(value)
            if dep:
                self.build[dep].add("build file")

    def saw_manifest(self, path, name):
        for ecosystem, package in manifest_dependencies(path, name):
            self.packages[ecosystem].add(package)

    # ####################
    # Headers that aren't here
    # ####################

    def resolves(self, include):
        inc = re.sub(r"^(\.\./|\./)+", "", include.replace("\\", "/")).lower()
        candidates = self.files.get(inc.rsplit("/", 1)[-1], [])
        return any(c == inc or c.endswith("/" + inc) for c in candidates)

    def missing_includes(self):
        """{library or folder: #includes} for headers included but not in the folder."""
        groups = Counter()
        for include, n in self.includes.items():
            if include in self.engine_includes and not self.resolves(include):
                groups[self.engine_includes[include]] += n   # the engine's own headers, never in the project
                continue
            parts = [p for p in include.replace("\\", "/").split("/") if p not in ("", ".", "..")]
            if not parts or parts[0].lower() in SYSTEM_HEADERS or include.lower() in SYSTEM_HEADERS:
                continue
            if self.resolves(include):
                continue
            first = parts[0] if len(parts) > 1 else parts[-1]
            name = next((lib for rx, lib in INCLUDE_LIBRARIES if rx.match(first) or rx.match(include)), None)
            groups[name or (first if len(parts) > 1 else "(headers in no folder)")] += n
        return groups

    # ####################
    # The report
    # ####################

    def report(self):
        out = []
        missing = self.missing_includes()
        stray = missing.pop("(headers in no folder)", 0)
        named = {}   # key -> display name, for libraries the build files name
        for name in self.build:
            named.setdefault(dependency_key(name), name)

        # ####################
        # Libraries and folders the code needs
        # ####################
        # Headers from a library's folder that's known (or that the build files name) go with it.
        include_libs, include_folders = Counter(), Counter()
        for name, n in missing.items():
            key = dependency_key(name)
            if key in named:
                continue
            (include_libs if is_known_library(name) else include_folders)[name] += n
        unknown = sorted((n for n in named.values() if not is_known_library(n)), key=str.lower)
        known = sorted({n for n in named.values() if is_known_library(n)} | set(include_libs), key=str.lower)
        if unknown or include_folders or known or stray:
            out += ["", "Code this project needs that isn't in this folder (from its build files and #includes):"]
            if unknown:
                out.append("  Named in the build files, and not libraries this script knows: perhaps the studio's own"
                           " (an engine, shared code), so ask for these:")
                out.append("    " + ", ".join(unknown[:20]) + (" ..." if len(unknown) > 20 else ""))
            if include_folders:
                total = sum(include_folders.values())
                out.append(f"  Headers included from folders that aren't here ({plural(total, '#include')}), probably"
                           + (" part of the above:" if unknown else " the studio's own code kept elsewhere:"))
                out.append("    " + ", ".join(sorted(include_folders, key=str.lower)[:25])
                           + (" ..." if len(include_folders) > 25 else ""))
            if known:
                out.append(f"  Known libraries ({len(known)}): " + ", ".join(known[:40]) + (" ..." if len(known) > 40 else ""))
            if stray:
                out.append(f"  (and {plural(stray, '#include')} of other headers that aren't here)")

        # ####################
        # Package lists
        # ####################
        if self.packages:
            out += ["", "Packages the project lists as dependencies:"]
            for ecosystem, names in sorted(self.packages.items()):
                names = sorted(names, key=str.lower)
                shown = ", ".join(names[:12]) + (f", and {len(names) - 12} more" if len(names) > 12 else "")
                out.append(f"  {ecosystem} ({len(names)}): {shown}")
        return out

    def unknown_libraries(self):
        """Named in the build files first, then folders of headers that aren't here."""
        named = sorted({n for n in self.build if not is_known_library(n)}, key=str.lower)
        keys = {dependency_key(n) for n in self.build}
        folders = sorted((n for n in self.missing_includes() if n != "(headers in no folder)"
                          and not is_known_library(n) and dependency_key(n) not in keys), key=str.lower)
        return named + folders


# #######################################
# Test coverage
# #######################################

# How much of the code the project's tests run, from the coverage reports they already wrote:
# read, never made. Making one means running the project's tests, and this script runs nothing of
# the project's. A report is found by its name or folder, then recognised by what's in it.

# ##############################
# Where reports are
# ##############################
COVERAGE_WORD = re.compile(r"cov|jacoco|clover|cobertura|kover|emma|tarpaulin|resultset|last_run|nyc_output", re.I)
# Build output the walk skips, where tests also write their reports (coverage/, htmlcov/,
# target/site/jacoco, build/reports/jacoco ...): looked through too, but only so deep and so far.
COVERAGE_OUTPUT_DIRS = {"coverage", "htmlcov", "build", "target", "out"}
COVERAGE_SEARCH_DEPTH = 6
COVERAGE_SEARCH_ENTRIES = 20_000      # files and folders looked at in each such folder, at most
COVERAGE_MAX_READ = 256 * 1024 * 1024   # bytes: a larger JSON or text report is listed, not read
# A report's own subfolders (its HTML pages): the report belongs to the folder above.
COVERAGE_SUBFOLDERS = {"html", "htmlcov", "lcov-report", "html-report", "htmlreport", "coverage-html"}
GO_PROFILE_EXTS = {".out", ".txt", ".cov", ".cover", ".coverprofile", ".profile"}
JULIA_COVERAGE = re.compile(r"\.jl(\.\d+)?\.cov$")

# ####################
# Data that only the project's own tools can read
# ####################
# Raw coverage data, from which those tools make a report; with the command that makes one.
RAW_COVERAGE = {
    "coverage.py data (.coverage)": "coverage xml",
    "JaCoCo data (.exec)": "gradle jacocoTestReport, or mvn jacoco:report",
    "gcov data (.gcda)": "gcovr --xml coverage.xml",
    "LLVM profiles (.profraw, .profdata)": "cargo llvm-cov report --lcov --output-path lcov.info, or llvm-cov export"
                                           " -format=lcov",
    "Go coverage data (covmeta, covcounters)": "go tool covdata textfmt -i <folder> -o coverage.out",
    "nyc data (.nyc_output)": "npx nyc report --reporter=lcov",
    "V8 coverage (c8, NODE_V8_COVERAGE)": "npx c8 report --reporter=lcov",
    "Visual Studio coverage (.coverage)": "dotnet-coverage merge -f cobertura -o coverage.xml <file>",
    "dotCover snapshots (.dcvr)": "dotCover report --reportType=XML",
    "PHPUnit data (.cov)": "phpcov merge --clover clover.xml <folder>",
    "Haskell HPC data (.tix)": "hpc report",
    "Erlang/Elixir cover data (.coverdata)": "mix coveralls.json (excoveralls)",
    "LuaCov statistics (luacov.stats.out)": "luacov",
    "Xcode test results (.xcresult)": "xcrun xccov view --report --json <bundle>",
    "Devel::Cover database (cover_db)": "cover -report text",
}
MEASURE = {"lines": "line", "statements": "statement", "branches": "branch", "functions": "function"}
HTML_COVERAGE = "an HTML report, whose figures this script doesn't read"
RAW_COVERAGE_EXTS = {".gcda": "gcov data (.gcda)", ".profraw": "LLVM profiles (.profraw, .profdata)",
                     ".profdata": "LLVM profiles (.profraw, .profdata)", ".tix": "Haskell HPC data (.tix)",
                     ".coverdata": "Erlang/Elixir cover data (.coverdata)", ".dcvr": "dotCover snapshots (.dcvr)"}

# ####################
# How a project's tests write a report
# ####################
# Said when no report is found, for the kinds of project found.
COVERAGE_HINTS = [
    ("Python", "pytest --cov --cov-report=xml (pytest-cov), or coverage run -m pytest, then coverage xml"),
    ("JavaScript", "jest --coverage, vitest run --coverage, or the test command run through c8 or nyc"),
    ("Unity", "Unity's Code Coverage package (com.unity.testtools.codecoverage), then the tests in the Test Runner"),
    (".NET", "dotnet test --collect:\"XPlat Code Coverage\""),
    ("Java (Maven)", "mvn verify, with the JaCoCo plugin's report goal"),
    ("Java/Kotlin (Gradle)", "gradle test jacocoTestReport (the jacoco plugin), or Kover"),
    ("Go", "go test -coverprofile=coverage.out ./..."),
    ("Rust", "cargo llvm-cov --lcov --output-path lcov.info, or cargo tarpaulin"),
    ("C/C++ (CMake)", "a build with --coverage, then the tests, then gcovr --xml coverage.xml"),
]


# ##############################
# Reading reports
# ##############################
# Each reader returns {"format", "measures": {measure: [covered, total]}, "percent": {measure: %},
# "files"}, or None if the file isn't a report of its kind. Measures: lines, statements, branches,
# functions. Formats that list every line are counted line by line, each line once however often
# the report repeats it (one test suite after another, say).

def coverage_count(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0   # lcov's "-": never run


def coverage_found(fmt, measures=None, files=None, percent=None):
    measures = {k: [int(measures[k][0]), int(measures[k][1])] for k in MEASURE if (measures or {}).get(k, [0, 0])[1]}
    percent = {k: float(p) for k, p in (percent or {}).items() if p is not None}
    if not measures and not percent:
        return None
    return {"format": fmt, "measures": measures, "percent": percent, "files": files}


def line_hits(hits):
    """[covered, total] of {(file, line): run?}."""
    return [sum(1 for hit in hits.values() if hit), len(hits)]


def mark(hits, key, hit):
    hits[key] = hits.get(key, False) or hit


# ####################
# LCOV
# ####################
# JavaScript (Istanbul, c8, Jest, Vitest), Dart and Flutter, Rust (cargo-llvm-cov, grcov), C and
# C++ (lcov, gcovr), Elixir, Swift, Bazel ...

def read_lcov(data):
    if b"end_of_record" not in data or not re.search(rb"^SF:", data, re.M):
        return None
    lines, branches, summary, files = {}, {}, [0, 0], set()
    source = None
    for raw in data.splitlines():
        key, _, value = raw.strip().partition(b":")
        if key == b"SF":
            source = value
            files.add(source)
        elif key == b"DA" and source is not None:
            parts = value.split(b",")
            if len(parts) >= 2:
                mark(lines, (source, parts[0]), coverage_count(parts[1]) > 0)
        elif key == b"BRDA" and source is not None:
            parts = value.split(b",")
            if len(parts) >= 4:
                mark(branches, (source,) + tuple(parts[:3]), coverage_count(parts[3]) > 0)
        elif key in (b"LH", b"LF") and value.strip().isdigit():
            summary[key == b"LF"] += int(value)
    measures = {"lines": line_hits(lines) if lines else summary, "branches": line_hits(branches)}
    return coverage_found("LCOV", measures, len(files))


# ####################
# XML reports
# ####################
# Cobertura (coverage.py, Istanbul, coverlet, gcovr, tarpaulin, PHPUnit ...), JaCoCo (Java,
# Kotlin, Android, Kover), Clover (PHPUnit, Istanbul, OpenClover), OpenCover (.NET, Unity's Code
# Coverage package), ReportGenerator, SonarQube's generic format, scoverage (Scala), EMMA (old
# Java, DelphiCodeCoverage), dotCover and Visual Studio's XML. Streamed: big reports aren't held
# in memory.
COVERAGE_XML_ROOTS = {"coverage", "report", "CoverageSession", "CoverageReport", "scoverage", "Root", "results"}
EMMA_VALUE = re.compile(r"\((\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\)")


def read_coverage_xml(path):
    import xml.etree.ElementTree as ET
    depth, fmt, root = 0, None, {}
    totals = defaultdict(lambda: [0, 0])   # measure -> [covered, total], as the report adds them up
    lines, files, source, package, listed_files = {}, set(), None, None, None
    try:
        for event, elem in ET.iterparse(path, events=("start", "end")):
            tag = elem.tag.rsplit("}", 1)[-1]
            if event == "end":
                depth -= 1
                if fmt == "ReportGenerator" and depth == 2 and elem.text and elem.text.strip().isdigit():
                    root.setdefault("summary", {})[tag.lower()] = int(elem.text.strip())
                elem.clear()   # done with it: free its memory
                continue
            depth += 1
            a = elem.attrib

            # ####################
            # Which format, from the top element and its first child
            # ####################
            if depth == 1:
                if tag not in COVERAGE_XML_ROOTS:
                    return None
                root = dict(a)
                fmt = {"CoverageSession": "OpenCover", "CoverageReport": "ReportGenerator", "scoverage": "scoverage",
                       "Root": "dotCover" if "TotalStatements" in a else None}.get(tag)
                if tag == "coverage" and ("line-rate" in a or "lines-valid" in a):
                    fmt = "Cobertura"
                root["tag"] = tag
                continue
            if fmt is None and depth == 2:
                fmt = {("coverage", "project"): "Clover", ("coverage", "file"): "SonarQube generic",
                       ("report", "stats"): "EMMA", ("report", "data"): "EMMA", ("report", "sessioninfo"): "JaCoCo",
                       ("report", "package"): "JaCoCo", ("report", "group"): "JaCoCo", ("report", "counter"): "JaCoCo",
                       ("results", "modules"): "Visual Studio"}.get((root["tag"], tag))
                if fmt is None:
                    return None

            # ####################
            # Its figures
            # ####################
            if fmt == "Cobertura":
                if tag == "class":
                    source = a.get("filename")
                    files.add(source)
                elif tag == "line" and "number" in a:
                    mark(lines, (source, a["number"]), coverage_count(a.get("hits")) > 0)
            elif fmt == "SonarQube generic":
                if tag == "file":
                    source = a.get("path")
                    files.add(source)
                elif tag == "lineToCover":
                    mark(lines, (source, a.get("lineNumber")), a.get("covered") == "true")
                    totals["branches"][0] += int(a.get("coveredBranches") or 0)
                    totals["branches"][1] += int(a.get("branchesToCover") or 0)
            elif fmt == "JaCoCo":
                if tag == "counter" and depth == 2:   # the report's own totals
                    measure = {"LINE": "lines", "BRANCH": "branches", "METHOD": "functions"}.get(a.get("type"))
                    if measure:
                        totals[measure] = [int(a.get("covered", 0)), int(a.get("covered", 0)) + int(a.get("missed", 0))]
                elif tag == "package":
                    package = a.get("name")
                elif tag == "sourcefile":
                    files.add((package, a.get("name")))
            elif fmt == "Clover":
                if tag == "metrics" and depth == 3:   # the project's totals
                    for measure, count in (("statements", "statements"), ("branches", "conditionals"),
                                           ("functions", "methods")):
                        totals[measure] = [int(a.get("covered" + count, 0)), int(a.get(count, 0))]
                    listed_files = int(a["files"]) if a.get("files", "").isdigit() else None
            elif fmt == "OpenCover":
                if tag == "Summary" and depth == 2:
                    totals["statements"] = [int(a.get("visitedSequencePoints", 0)), int(a.get("numSequencePoints", 0))]
                    totals["branches"] = [int(a.get("visitedBranchPoints", 0)), int(a.get("numBranchPoints", 0))]
                    totals["functions"] = [int(a.get("visitedMethods", 0)), int(a.get("numMethods", 0))]
                elif tag == "File" and "fullPath" in a:
                    files.add(a["fullPath"])
            elif fmt == "EMMA":
                if tag == "coverage" and depth == 4:   # report > data > all > coverage: the totals
                    m = EMMA_VALUE.search(a.get("value", ""))
                    measure = {"line": "lines", "block": "statements", "method": "functions"}.get(
                        a.get("type", "").split(",")[0])
                    if m and measure:
                        totals[measure] = [round(float(m.group(1))), round(float(m.group(2)))]
                elif tag == "package":
                    package = a.get("name")
                elif tag == "srcfile":
                    files.add((package, a.get("name")))
            elif fmt == "Visual Studio":
                if tag == "module":
                    covered = int(a.get("lines_covered", 0)) + int(a.get("lines_partially_covered", 0))
                    totals["lines"][0] += covered
                    totals["lines"][1] += covered + int(a.get("lines_not_covered", 0))
                elif tag == "source_file":
                    files.add(a.get("path"))
    except ET.ParseError:
        if fmt is None:
            return None
        return {"format": fmt + " XML", "unread": "malformed XML"}

    # ####################
    # The totals of formats that give them at the top
    # ####################
    if fmt == "Cobertura":
        valid = int(root.get("lines-valid") or 0)
        if valid:   # what the tool itself counted
            totals["lines"] = [int(root.get("lines-covered") or 0), valid]
        elif lines:
            totals["lines"] = line_hits(lines)
        totals["branches"] = [int(root.get("branches-covered") or 0), int(root.get("branches-valid") or 0)]
        percent = {} if totals["lines"][1] else {"lines": 100 * coverage_count(root.get("line-rate"))}
        return coverage_found("Cobertura XML", totals, len(files) or None, percent)
    if fmt == "SonarQube generic":
        totals["lines"] = line_hits(lines)
    elif fmt == "scoverage":
        totals["statements"] = [int(root.get("statements-invoked") or 0), int(root.get("statement-count") or 0)]
    elif fmt == "dotCover":
        totals["statements"] = [int(root.get("CoveredStatements") or 0), int(root.get("TotalStatements") or 0)]
    elif fmt == "ReportGenerator":
        s = root.get("summary", {})
        for measure, covered, total in (("lines", "coveredlines", "coverablelines"),
                                        ("branches", "coveredbranches", "totalbranches"),
                                        ("functions", "coveredmethods", "totalmethods")):
            totals[measure] = [s.get(covered, 0), s.get(total, 0)]
        return coverage_found("ReportGenerator summary", totals, s.get("files"))
    return coverage_found(fmt + " XML", totals, listed_files or len(files) or None)


# ####################
# JSON reports
# ####################
# coverage.py, Istanbul (coverage-final.json, coverage-summary.json), llvm-cov and cargo-llvm-cov,
# tarpaulin, gcovr, kcov, Xcode's xccov, ReportGenerator, Coveralls (excoveralls and others),
# SimpleCov (Ruby) and coverlet's own format.

def read_coverage_json(data):
    if re.match(rb'\s*\{\s*"result"\s*:\s*\[\s*\{\s*"scriptId"', data[:200]):
        return {"raw": "V8 coverage (c8, NODE_V8_COVERAGE)"}
    try:
        doc = json.loads(data)
    except (ValueError, RecursionError):
        return None
    if not isinstance(doc, dict) or not doc:
        return None
    get = doc.get
    first = next(iter(doc.values()))

    # ####################
    # Formats that give their totals
    # ####################
    totals = get("totals")
    if isinstance(get("meta"), dict) and isinstance(totals, dict) and "num_statements" in totals:
        return coverage_found("coverage.py JSON", {
            "lines": [totals.get("covered_lines", 0), totals["num_statements"]],
            "branches": [totals.get("covered_branches", 0), totals.get("num_branches", 0)]}, len(get("files") or ()))
    total = get("total")
    if isinstance(total, dict) and isinstance(total.get("lines"), dict) and "total" in total["lines"]:
        return coverage_found("Istanbul summary JSON", {
            measure: [total[key].get("covered", 0), total[key].get("total", 0)]
            for measure, key in (("lines", "lines"), ("statements", "statements"), ("branches", "branches"),
                                 ("functions", "functions")) if isinstance(total.get(key), dict)}, len(doc) - 1)
    if get("type") == "llvm.coverage.json.export" and isinstance(get("data"), list):
        found = defaultdict(lambda: [0, 0])
        files = 0
        for export in get("data"):
            files += len(export.get("files") or ())
            for measure, key in (("lines", "lines"), ("branches", "branches"), ("functions", "functions")):
                t = (export.get("totals") or {}).get(key) or {}
                found[measure][0] += t.get("covered", 0)
                found[measure][1] += t.get("count", 0)
        return coverage_found("llvm-cov JSON", found, files)
    if "line_total" in doc and "line_covered" in doc:
        return coverage_found("gcovr summary JSON", {
            "lines": [get("line_covered"), get("line_total")], "branches": [get("branch_covered", 0), get("branch_total", 0)],
            "functions": [get("function_covered", 0), get("function_total", 0)]}, len(get("files") or ()))
    if "covered_lines" in doc and "total_lines" in doc:
        return coverage_found("kcov JSON", {"lines": [int(get("covered_lines")), int(get("total_lines"))]},
                              len(get("files") or ()))
    if "coveredLines" in doc and "executableLines" in doc:
        return coverage_found("xccov JSON", {"lines": [get("coveredLines"), get("executableLines")]},
                              sum(len(t.get("files") or ()) for t in get("targets") or ()) or None)
    summary = get("summary")
    if isinstance(summary, dict) and "coverablelines" in summary:
        return coverage_found("ReportGenerator summary JSON", {
            "lines": [summary.get("coveredlines", 0), summary["coverablelines"]],
            "branches": [summary.get("coveredbranches") or 0, summary.get("totalbranches") or 0],
            "functions": [summary.get("coveredmethods") or 0, summary.get("totalmethods") or 0]})
    if isinstance(get("files"), list) and get("files") and isinstance(get("files")[0], dict) \
            and "coverable" in get("files")[0]:
        return coverage_found("tarpaulin JSON", {"lines": [sum(f.get("covered", 0) for f in get("files")),
                                                           sum(f.get("coverable", 0) for f in get("files"))]},
                              len(get("files")))
    result = get("result")
    if isinstance(result, dict) and ("line" in result or "covered_percent" in result):   # SimpleCov's .last_run.json
        return coverage_found("SimpleCov summary", percent={"lines": result.get("line", result.get("covered_percent")),
                                                            "branches": result.get("branch")})

    # ####################
    # Formats counted line by line
    # ####################
    lines, branches, statements, functions = {}, [0, 0], [0, 0], [0, 0]
    if "gcovr/format_version" in doc:
        for f in get("files") or ():
            for line in f.get("lines") or ():
                if not line.get("gcovr/noncode"):
                    mark(lines, (f.get("file"), line.get("line_number")), (line.get("count") or 0) > 0)
        return coverage_found("gcovr JSON", {"lines": line_hits(lines)}, len(get("files") or ()))
    if isinstance(get("source_files"), list):   # Coveralls
        for f in get("source_files"):
            for i, count in enumerate(f.get("coverage") or ()):
                if isinstance(count, int):
                    mark(lines, (f.get("name"), i), count > 0)
        return coverage_found("Coveralls JSON", {"lines": line_hits(lines)}, len({f.get("name") for f in get("source_files")}))
    if isinstance(first, dict) and "statementMap" in first:   # Istanbul's coverage-final.json
        for path, f in doc.items():
            counts = f.get("s") or {}
            for key, where in (f.get("statementMap") or {}).items():
                mark(lines, (path, where.get("start", {}).get("line")), (counts.get(key) or 0) > 0)
            statements[0] += sum(1 for n in counts.values() if n)
            statements[1] += len(counts)
            functions[0] += sum(1 for n in (f.get("f") or {}).values() if n)
            functions[1] += len(f.get("f") or {})
            for taken in (f.get("b") or {}).values():
                branches[0] += sum(1 for n in taken if n)
                branches[1] += len(taken)
        return coverage_found("Istanbul JSON", {"lines": line_hits(lines), "statements": statements,
                                                "branches": branches, "functions": functions}, len(doc))
    if isinstance(first, dict) and isinstance(first.get("coverage"), dict) and "timestamp" in first:   # SimpleCov
        for suite in doc.values():
            for path, counts in (suite.get("coverage") or {}).items():
                for i, count in enumerate((counts.get("lines") if isinstance(counts, dict) else counts) or ()):
                    if isinstance(count, int):
                        mark(lines, (path, i), count > 0)
        return coverage_found("SimpleCov results", {"lines": line_hits(lines)}, len({p for p, _ in lines}))
    if all(k.lower().endswith((".dll", ".exe")) for k in doc) and isinstance(first, dict):   # coverlet
        for sources in doc.values():
            for path, classes in sources.items():
                for methods in classes.values():
                    for method in methods.values():
                        for line, hits in (method.get("Lines") or {}).items():
                            mark(lines, (path, line), hits > 0)
                        for branch in method.get("Branches") or ():
                            branches[0] += branch.get("Hits", 0) > 0
                            branches[1] += 1
        return coverage_found("coverlet JSON", {"lines": line_hits(lines), "branches": branches},
                              len({p for p, _ in lines}))
    return None


# ####################
# Text reports
# ####################
GO_BLOCK = re.compile(rb"^(.+):(\d+\.\d+,\d+\.\d+) (\d+) (\d+)\s*$")
LUACOV_TOTAL = re.compile(rb"^Total\s+(\d+)\s+(\d+)\s+[\d.]+%\s*$", re.M)
JULIA_LINE = re.compile(rb"^\s*(-|\d+) ")


def read_go_profile(data):
    """go test -coverprofile: one line per block of statements, with how often it ran."""
    rows = data.splitlines()
    if not rows or not re.match(rb"mode: (set|count|atomic)\s*$", rows[0]):
        return None
    blocks = {}
    for row in rows[1:]:
        m = GO_BLOCK.match(row)
        if m:
            key = (m.group(1), m.group(2))
            ran = int(m.group(4)) > 0 or blocks.get(key, (0, False))[1]
            blocks[key] = (int(m.group(3)), ran)
    statements = [sum(n for n, ran in blocks.values() if ran), sum(n for n, _ in blocks.values())]
    return coverage_found("Go cover profile", {"statements": statements}, len({f for f, _ in blocks}))


def read_luacov_report(data):
    totals = LUACOV_TOTAL.findall(data)
    if not totals:
        return None
    hits, missed = (int(n) for n in totals[-1])
    return coverage_found("LuaCov report", {"lines": [hits, hits + missed]})


def read_jacoco_csv(data):
    import csv
    import io
    rows = csv.DictReader(io.StringIO(data.decode("utf-8", "replace")))
    if not rows.fieldnames or "LINE_COVERED" not in rows.fieldnames:
        return None
    found = defaultdict(lambda: [0, 0])
    for row in rows:
        for measure, key in (("lines", "LINE"), ("branches", "BRANCH"), ("functions", "METHOD")):
            covered = int(row.get(key + "_COVERED") or 0)
            found[measure][0] += covered
            found[measure][1] += covered + int(row.get(key + "_MISSED") or 0)
    return coverage_found("JaCoCo CSV", found)


def gcov_lines(data):
    """{(source, line): run?} from gcov's annotated copy of a source file, or None."""
    if not re.match(rb"\s*-:\s*0:Source:", data):
        return None
    lines, source = {}, None
    for row in data.splitlines():
        parts = row.split(b":", 2)
        if len(parts) < 3:
            continue
        count, number = parts[0].strip(), parts[1].strip()
        if number == b"0":
            if parts[2].startswith(b"Source:"):
                source = parts[2][7:].strip()
        elif count != b"-" and number.isdigit():
            mark(lines, (source, number), count.rstrip(b"*") not in (b"#####", b"=====", b"0"))
    return lines


def julia_lines(data, source):
    """{(source, line): run?} from a Julia .cov file (each source line, after how often it ran)."""
    lines = {}
    for i, row in enumerate(data.splitlines()):
        m = JULIA_LINE.match(row)
        if m is None:
            return None
        if m.group(1) != b"-":
            mark(lines, (source, i), int(m.group(1)) > 0)
    return lines


# ####################
# HTML reports
# ####################
# Read only when they're the only copy: coverage.py's and Istanbul's front pages.
ISTANBUL_FIGURE = r"<span class=.quiet.>\s*{}\s*</span>\s*<span class=.fraction.>\s*(\d+)\s*/\s*(\d+)"


def read_coverage_html(data):
    if b"coverage.py" in data:
        row = re.search(rb'<tr class="total">(.*?)</tr>', data, re.S)
        numbers = [int(n) for n in re.findall(rb"<td[^>]*>\s*(\d+)\s*</td>", row.group(1))] if row else []
        if len(numbers) >= 2:   # statements, missing
            return coverage_found("coverage.py HTML", {"lines": [numbers[0] - numbers[1], numbers[0]]})
    if b"istanbul" in data.lower():
        found = {}
        for measure, label in (("lines", "Lines"), ("statements", "Statements"), ("branches", "Branches"),
                               ("functions", "Functions")):
            m = re.search(ISTANBUL_FIGURE.format(label).encode(), data)
            if m:
                found[measure] = [int(m.group(1)), int(m.group(2))]
        if found:
            return coverage_found("Istanbul HTML", found)
    return None


# ##############################
# Collecting and reporting
# ##############################

def coverage_folder(rel):
    """A folder relative to the scanned one, with "/", and "" for the scanned folder itself."""
    rel = os.path.normpath(rel).replace(os.sep, "/")
    return "" if rel == "." else rel


def coverage_home(folder):
    """The folder a report belongs to: above its own subfolders (coverage/lcov-report -> coverage)."""
    parts = folder.split("/") if folder else []
    while parts and parts[-1].lower() in COVERAGE_SUBFOLDERS:
        parts.pop()
    return "/".join(parts)


def folder_within(folder, other):
    return not other or folder == other or folder.startswith(other + "/")


def coverage_beside(folder, home):
    """Whether raw data in folder is beside a report in home, and so what the report was made from:
    both in the same top-level folder (app/build/jacoco and app/build/reports/jacoco; build/CMakeFiles/...
    and build), or both at the top or just below it (.coverage and coverage.xml or htmlcov;
    .nyc_output and coverage)."""
    folder = coverage_home(folder)
    top = lambda f: f.split("/")[0]
    shallow = lambda f: "/" not in f
    return bool(folder and home and top(folder) == top(home)) or (shallow(folder) and shallow(home))


class CoverageReports:
    """Collects, while the folder is walked, the coverage reports the project's tests wrote, and
    raw coverage data that only the project's own tools can read."""

    def __init__(self):
        self.reports = []                  # {"folder", "format", "date", "measures", "percent", "files"}
        self.unread = {}                   # (folder, kind) -> {"files", "date", "how"}
        self.by_line = {}                  # format -> [{(source, line): run?}, {folders}, latest date]
        self.html_folders = []             # folders with an HTML report: the pages below them are its own

    # ####################
    # During the walk
    # ####################

    def saw_folder(self, name, rel):
        n = name.lower()
        if n.endswith(".xcresult") or n == "cover_db":
            kind = "Xcode test results (.xcresult)" if n.endswith(".xcresult") else "Devel::Cover database (cover_db)"
            self.found_unread(coverage_folder(rel), kind, None)

    def search(self, folder, rel):
        """A folder the walk skips as build output, where reports are often written."""
        seen, top = 0, folder.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(folder):
            here = os.path.join(rel, os.path.relpath(dirpath, folder))
            deep = dirpath.count(os.sep) - top >= COVERAGE_SEARCH_DEPTH
            dirnames[:] = [] if deep else [d for d in dirnames if d.lower() not in ALWAYS_SKIP
                                           and not is_link(os.path.join(dirpath, d))]
            for d in dirnames:
                self.saw_folder(d, here)
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    st = os.lstat(path)
                except OSError:
                    continue
                if S_ISREG(st.st_mode):
                    self.saw_file(path, name, here, st)
            seen += len(dirnames) + len(filenames)
            if seen > COVERAGE_SEARCH_ENTRIES:
                break

    def saw_file(self, path, name, rel, st):
        """Any file of the studio's own (rel: its folder): a report, or raw coverage data, or neither."""
        n = name.lower()
        ext = os.path.splitext(n)[1]
        kind = RAW_COVERAGE_EXTS.get(ext)
        if kind is None and n.startswith(("covmeta.", "covcounters.")):
            kind = "Go coverage data (covmeta, covcounters)"
        elif kind is None and n == "luacov.stats.out":
            kind = "LuaCov statistics (luacov.stats.out)"
        elif kind is None and ext == ".coverage" and n != ".coverage":
            kind = "Visual Studio coverage (.coverage)"
        if kind:
            self.found_unread(coverage_folder(rel), kind, st.st_mtime)
            return
        lcov = ext in (".lcov", ".info", ".dat") and ("lcov" in n or n in ("coverage.info", "coverage.dat")
                                                      or n.endswith("_coverage_report.dat"))
        if not (n == ".coverage" or n.startswith(".coverage.") or ext in (".exec", ".gcov") or lcov
                or n == "luacov.report.out" or JULIA_COVERAGE.search(n)
                or (ext in GO_PROFILE_EXTS and (COVERAGE_WORD.search(n) or n in ("c.out", "profile.out")))
                or (ext in (".xml", ".coveragexml", ".json", ".csv", ".html", ".htm")
                    and (COVERAGE_WORD.search(n) or COVERAGE_WORD.search(rel)))):
            return
        folder = coverage_folder(rel)
        try:
            self.read(path, n, ext, folder, st, lcov)
        except Exception:   # a report this script misreads: listed, not counted
            self.found_unread(folder, "a coverage report it couldn't read", st.st_mtime)

    def read(self, path, n, ext, folder, st, lcov):
        if ext in (".xml", ".coveragexml"):
            found = read_coverage_xml(path)
        else:
            if ".nyc_output" in folder.split("/"):
                if ext == ".json":
                    self.found_unread(folder, "nyc data (.nyc_output)", st.st_mtime)
                return
            if ext in (".html", ".htm") and (any(folder_within(folder, f) for f in self.html_folders)
                                             or not (n.startswith("index.") or COVERAGE_WORD.search(n))):
                return   # one of an HTML report's own pages
            sniff = n == ".coverage" or n.startswith(".coverage.") or ext == ".exec"   # only the start is needed
            if st.st_size > COVERAGE_MAX_READ and not sniff:
                if COVERAGE_WORD.search(n):
                    self.found_unread(folder, "a coverage report too large to read", st.st_mtime)
                return
            with open(path, "rb") as f:
                data = f.read(4096) if sniff else f.read()
            found = None
            if n == ".coverage" or n.startswith(".coverage."):
                if data.startswith((b"SQLite format 3", b"!coverage.py")):
                    found = {"raw": "coverage.py data (.coverage)"}
            elif ext == ".exec":
                if data.startswith(b"\x01\xc0\xc0"):
                    found = {"raw": "JaCoCo data (.exec)"}
            elif ext == ".json":
                found = read_coverage_json(data)
            elif ext == ".csv":
                found = read_jacoco_csv(data) if "jacoco" in n else None
            elif ext in (".html", ".htm"):
                if b"coverage" in data.lower():
                    self.html_folders.append(folder)
                    found = read_coverage_html(data) or {"raw": HTML_COVERAGE}
            elif ext == ".gcov" or JULIA_COVERAGE.search(n):
                lines = gcov_lines(data) if ext == ".gcov" else julia_lines(data, (folder, JULIA_COVERAGE.sub(".jl", n)))
                if lines is not None:
                    fmt = "gcov files" if ext == ".gcov" else "Julia .cov files"
                    hits, folders, latest = self.by_line.setdefault(fmt, [{}, set(), 0])
                    for key, hit in lines.items():
                        mark(hits, key, hit)
                    folders.add(folder)
                    self.by_line[fmt][2] = max(latest, st.st_mtime)
                return
            elif data.startswith(b"<?php") and b"CodeCoverage" in data[:4096]:
                found = {"raw": "PHPUnit data (.cov)"}
            elif n == "luacov.report.out":
                found = read_luacov_report(data)
            elif lcov:
                found = read_lcov(data)
            else:
                found = read_go_profile(data)
        if found is None:
            return
        if "raw" in found:
            self.found_unread(folder, found["raw"], st.st_mtime)
        elif "unread" in found:
            self.found_unread(folder, f"a {found['format']} report it couldn't read ({found['unread']})", st.st_mtime)
        else:
            self.reports.append(dict(found, folder=folder, date=st.st_mtime))

    def found_unread(self, folder, kind, mtime):
        got = self.unread.setdefault((folder, kind), {"files": 0, "date": None, "how": RAW_COVERAGE.get(kind)})
        got["files"] += 1
        if mtime is not None:
            got["date"] = max(got["date"] or 0, mtime)

    # ####################
    # The report
    # ####################

    def readable(self):
        """The reports, one per folder: where a test run wrote the same figures in several formats
        (lcov.info, coverage-final.json and clover.xml, say), the one that counts lines, and the most."""
        reports = list(self.reports)
        for fmt, (hits, folders, latest) in self.by_line.items():
            shared = []   # the folder they're all in
            for parts in zip(*(f.split("/") if f else [] for f in folders)):
                if len(set(parts)) > 1:
                    break
                shared.append(parts[0])
            folder = "/".join(shared)
            reports.append({"format": fmt, "measures": {"lines": line_hits(hits)}, "percent": {},
                            "files": len({source for source, _ in hits}), "folder": folder, "date": latest})
        best = {}
        for r in reports:
            r["home"] = coverage_home(r["folder"])
            # Lines first, then the most measures, then a machine-readable format, then by name.
            r["rank"] = ("lines" not in r["measures"], -len(r["measures"]), "HTML" in r["format"], r["format"])
            best.setdefault(r["home"], []).append(r)
        chosen = []
        for home, group in best.items():
            top = min(r["rank"] for r in group)
            # The best format in each folder; reports in the same format there are separate runs.
            fmt = next(r["format"] for r in group if r["rank"] == top)
            chosen += [r for r in group if r["format"] == fmt]
        return sorted(chosen, key=lambda r: -max([t for _, t in r["measures"].values()] or [0]))

    def report(self, kinds):
        """(report lines, the summary's line, facts)."""
        reports = self.readable()
        homes = [r["home"] for r in reports]
        # Raw data beside a report (coverage.py's .coverage beside its coverage.xml, say) is what
        # the report was made from.
        unread = sorted(((folder, kind, got) for (folder, kind), got in self.unread.items()
                         if not any(coverage_beside(folder, h) for h in homes)), key=lambda row: (row[0], row[1]))
        day = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d") if t else None
        where = lambda folder: folder or "(top level)"
        where_in = lambda folder: f"in {folder}" if folder else "at the top level"

        def figures(r):
            main = next((m for m in ("lines", "statements") if m in r["measures"]), None)
            parts = []
            for measure in ([main] if main else []) + [m for m in ("branches", "functions") if m in r["measures"]]:
                covered, total = r["measures"][measure]
                parts.append(f"{100 * covered / total:.1f}% of {total:,} {measure if total != 1 else MEASURE[measure]}")
            if not parts:
                parts = [f"{p:.1f}% of {m}" for m, p in r["percent"].items()]
            return ", ".join(parts)

        # ####################
        # Report lines
        # ####################
        out = [""]
        if reports:
            out += ["Test coverage, from the reports the project's tests already wrote (read, not measured: each",
                    "shows the code as it was when its tests last ran, as its own tool counted it):"]
            for r in reports[:10]:
                detail = ", ".join([r["format"]] + ([plural(r["files"], "file")] if r["files"] else [])
                                   + [day(r["date"])])
                out.append(f"  {where(r['folder']):<32} {figures(r)}  ({detail})")
            if len(reports) > 10:
                out.append(f"  ... and {len(reports) - 10} more")
        else:
            out.append("Test coverage: no coverage reports found in the folder.")
        if unread:
            out.append(("  " if reports else "") + "Coverage data that only the project's own tools can read (a report"
                       " made from it would be counted):")
            for folder, kind, got in unread[:10]:
                when = f", {day(got['date'])}" if got["date"] else ""
                how = f": {got['how']}" if got["how"] else ""
                out.append(f"    {where(folder)}: {kind} ({plural(got['files'], 'file')}{when}){how}")
            if len(unread) > 10:
                out.append(f"    ... and {len(unread) - 10} more")
        hints = [(kind, how) for kind, how in COVERAGE_HINTS if kind in kinds]
        if not reports:
            out += ["To include it, run the tests with coverage turned on first, so their report is in the folder, then",
                    "run this again (this script itself runs nothing of the project's)." + (" For example:" if hints else "")]
            out += [f"  {kind}: {how}" for kind, how in hints]

        # ####################
        # The summary's line, and facts
        # ####################
        if reports:
            r = reports[0]
            summary = (f"  Test coverage: {figures(r).split(', ')[0]} ({r['format']} {where_in(r['folder'])},"
                       f" {day(r['date'])})" + (f"; {plural(len(reports) - 1, 'more report')} below"
                                                if len(reports) > 1 else ""))
        else:
            summary = "  Test coverage: " + ("no readable report (coverage data found: see below)" if unread
                                             else "no reports found")
        facts = {"reports": [{"folder": r["folder"], "format": r["format"], "date": day(r["date"]),
                              "files": r["files"], **{m: {"covered": c, "total": t} for m, (c, t) in r["measures"].items()},
                              **({"percent": r["percent"]} if r["percent"] else {})} for r in reports],
                 "unread": [{"folder": folder, "kind": kind, "files": got["files"], "date": day(got["date"]),
                             "how_to_make_a_report": got["how"]} for folder, kind, got in unread]}
        return out, summary, facts


# #######################################
# More about the copy
# #######################################

# More about the copy that was scanned: whether it's complete, whose it is, and what would have
# to be cleaned up before it could change hands.

# ##############################
# Console code
# ##############################
# Console code: usually under the platform holder's NDA, so it may not be sellable with the rest.
CONSOLE_DIRS = {"ps3", "ps4", "ps5", "orbis", "prospero", "psvita", "psp", "xbox360", "xboxone", "xboxseries",
                "xboxonegdk", "xsx", "durango", "scarlett", "gdk", "xdk", "gamecore", "nx", "nx64", "wiiu", "3ds"}
CONSOLE_BESIDE_PLATFORMS = {"switch", "xbox", "playstation", "nintendo", "sony"}   # only next to other platforms
PLATFORM_DIRS = CONSOLE_DIRS | {"windows", "win32", "win64", "linux", "mac", "macos", "osx", "android", "ios", "pc",
                                "desktop", "steam", "egs"}
CONSOLE_FILE = re.compile(r"(?i)(?:^|[_.\-])(ps[345]|orbis|prospero|xboxone|xb1|xsx|durango|scarlett|nx64)(?=[_.\-])")


def console_children(dirnames):
    """The subfolders that hold console (PlayStation, Xbox, Switch ...) code."""
    low = {d.lower(): d for d in dirnames}
    beside = bool(set(low) & (PLATFORM_DIRS - CONSOLE_BESIDE_PLATFORMS))
    return {d for l, d in low.items() if l in CONSOLE_DIRS or (beside and l in CONSOLE_BESIDE_PLATFORMS)}


# ##############################
# Precompiled libraries and credentials
# ##############################
BINARY_LIBRARY_EXTS = {".dll", ".lib", ".a", ".so", ".dylib", ".jar", ".aar", ".bpl", ".ocx", ".pyd"}
SECRET_SCAN_EXTS = {".env", ".ini", ".cfg", ".conf", ".config", ".json", ".yml", ".yaml", ".xml", ".properties",
                    ".plist", ".toml", ".txt", ".asset"}
KEY_FILES = re.compile(r"(?i)^(id_rsa|id_dsa|id_ecdsa|id_ed25519|\.env(\..+)?|.+\.(pem|p12|pfx|keystore|jks|ppk|"
                       r"mobileprovision))$")


# ##############################
# Licences
# ##############################
LICENCE_KINDS = [   # (kind, what its text says), most specific first
    ("non-commercial licence", r"non[- ]?commercial"),
    ("AGPL", r"affero general public license"), ("LGPL", r"lesser general public license"),
    ("GPL", r"gnu general public license"), ("MPL", r"mozilla public license"), ("Apache 2.0", r"apache license"),
    ("MIT", r"permission is hereby granted, free of charge"), ("BSD", r"redistribution and use in source and binary"),
    ("zlib", r"this software is provided ['‘’]as-is['‘’]"), ("Creative Commons", r"creative commons"),
    ("Unlicense / public domain", r"unlicense|dedicated to the public domain"),
    ("proprietary (all rights reserved)", r"all rights reserved|proprietary|confidential"),
]
ROOT_LICENCE = re.compile(r"^(licen[cs]e|copying|copyright|eula)([._-].*)?$", re.I)


def licence_kind(text):
    low = text[:30000].lower()
    return next((kind for kind, pattern in LICENCE_KINDS if re.search(pattern, low)), "a licence of its own")


def root_licence(root):
    """The kind of licence in a licence file at the top of the folder, or None."""
    for name in sorted(list_files(root)):
        if ROOT_LICENCE.match(name) and os.path.isfile(os.path.join(root, name)):
            try:
                with open(os.path.join(root, name), encoding="utf-8", errors="replace") as f:
                    return licence_kind(f.read(30000))
            except OSError:
                pass
    return None


# ##############################
# The repository
# ##############################
ARCHIVE_NAME = re.compile(r"-(main|master|develop|dev|trunk|release|default|[0-9a-f]{7,40})$", re.I)


def repo_owner(url):
    """("github.com", "owner") for a repository's URL, or None."""
    m = re.search(r"(?:^|@|//)([\w.-]+\.\w+)[:/]+(?:scm/)?([^/\s]+)/[^/\s]+?(?:\.git)?/?$", url or "")
    return (m.group(1).lower(), m.group(2).lower()) if m else None


def public_repositories(root):
    """["github.com/owner/repo"] of the repository's remotes that anyone can read: asked without
    any login, on the public hosting services."""
    found = []
    for _, url in git_remotes(root):
        m = re.search(r"(github\.com|gitlab\.com|bitbucket\.org)[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
        if m and OFFLINE:
            left_out_offline("whether anyone can read the repository (asked of GitHub, GitLab or Bitbucket)")
        elif m and ls_remote(root, f"https://{m.group(1)}/{m.group(2)}/{m.group(3)}.git", "HEAD", options=["--exit-code"],
                             login=False, timeout=30) is not None:
            found.append(f"{m.group(1)}/{m.group(2)}/{m.group(3)}")
    return found


def git_tracked_files(root):
    """The files Git holds, relative to root (normcase), or None if root isn't in a repository with commits."""
    if run(["git", "rev-parse", "HEAD"], root, 60) is None:
        return None
    out = run(["git", "ls-files", "-z"], root, 600)
    return None if out is None else {os.path.normcase(p.replace("/", os.sep)) for p in out.split("\0") if p}


def submodules(repo_dir):
    """[(path, url)] from a repository's .gitmodules."""
    try:
        with open(os.path.join(repo_dir, ".gitmodules"), encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    out = []
    for entry in re.split(r"^\s*\[submodule\b", text, flags=re.M)[1:]:
        path = re.search(r"^\s*path\s*=\s*(.+?)\s*$", entry, re.M)
        url = re.search(r"^\s*url\s*=\s*(.+?)\s*$", entry, re.M)
        if path:
            out.append((path.group(1), url.group(1) if url else ""))
    return out


# ##############################
# Code by folder
# ##############################

def folder_key(rel):
    """Top-level folder used for the per-folder breakdown, e.g. 'Assets/Scripts' or 'src/app'."""
    parts = [] if rel == "." else rel.split(os.sep)
    if not parts:
        return "(top level)"
    if len(parts) > 2 and parts[0].lower() == "development" and parts[1].lower() == "src":
        return "/".join(parts[:3])   # Unreal Engine 3: Development/Src/MyGame
    if parts[0].lower() in {"assets", "src", "packages", "apps", "lib", "libs", "game", "source", "plugins",
                            "content", "script", "scripts"} and len(parts) > 1:
        return parts[0] + "/" + parts[1]
    return parts[0]


def folder_breakdown(lines_by_dir):
    """[(folder, lines)] largest first, starting from the top-level folders. A folder holding more
    than half of the code is opened up, so a library copied into e.g. Source/MyGame shows up."""
    total = sum(lines_by_dir.values())
    opened = set()

    def group(rel):
        parts, key = rel.split(os.sep), folder_key(rel)
        while key in opened:
            depth = len(key.split("/"))
            key = "/".join(parts[:depth + 1]) if len(parts) > depth else key + " (files directly in it)"
        return key

    while True:
        groups = Counter()
        for rel, lines in lines_by_dir.items():
            groups[group(rel)] += lines
        key, lines = groups.most_common(1)[0]
        if len(opened) >= 6 or lines * 2 <= total:
            return groups.most_common()
        # Open it, going down through folders that hold nothing but one subfolder.
        tried = []
        while True:
            opened.add(key)
            tried.append(key)
            inside = {group(rel) for rel in lines_by_dir
                      if (rel.replace(os.sep, "/") + "/").startswith(key + "/")}
            if len(inside) != 1:
                break
            key = inside.pop()
            if key.endswith(" (files directly in it)") or not any(
                    rel.replace(os.sep, "/").startswith(key + "/") for rel in lines_by_dir):
                inside = set()
                break
        if len(inside) < 2:   # nothing to split: keep the folder whole
            opened.difference_update(tried)
            return groups.most_common()


# #######################################
# Standard measures
# #######################################

# Standard measures: the numbers buyers' codebase forms ask for, as the tools those forms name
# define them. scc counts logical lines (not blank, not only a comment) and, with --gen, generated
# code; jscpd measures duplication (code copied and pasted, at least 5 lines and 50 tokens long).
# Both are run the way the forms ask, over the studio's own code. Where one can't be run, its
# figures are left out of the report, which says why: this script doesn't estimate them.

# ##############################
# Primary language
# ##############################
# The languages on forms' lists, and the names this script and scc give some of them.
FORM_LANGUAGES = {"C#", "C", "C++", "CSS", "Go", "HTML", "Java", "JavaScript", "Kotlin", "PHP", "Python", "Ruby",
                  "Rust", "SQL", "Scala", "Shell", "Swift", "TypeScript", "ABAP", "Ada", "Apex", "Assembly", "COBOL",
                  "Delphi", "Erlang", "Fortran", "JCL", "LabVIEW", "MUMPS", "OCaml", "Object Pascal", "PL/I", "Perl",
                  "Progress ABL", "RPG", "Smalltalk", "Tcl", "VHDL", "Verilog", "Visual Basic 6"}
FORM_LANGUAGE_NAMES = {"UnityScript": "JavaScript", "T-SQL": "SQL", "PL/SQL": "SQL", "Pascal": "Object Pascal",
                       # scc's names
                       "C Header": "C header", "C++ Header": "C++", "BASH": "Shell", "Zsh": "Shell", "Korn Shell": "Shell",
                       "C Shell": "Shell", "Fish": "Shell", "FORTRAN Legacy": "Fortran", "Fortran Modern": "Fortran",
                       "SystemVerilog": "Verilog", "JSX": "JavaScript", "TypeScript Typings": "TypeScript", "TCL": "Tcl",
                       "Objective C": "Objective-C", "Objective C++": "Objective-C", "Unreal Script": "UnrealScript",
                       "Powershell": "PowerShell", "Cuda": "CUDA"}
# What scc counts that isn't code (settings, data, documents, project files): never the primary language.
SCC_NOT_CODE = {"JSON", "JSONC", "JSON5", "JSONL", "XML", "YAML", "TOML", "INI", "CSV", "Markdown", "Plain Text",
                "License", "ReStructuredText", "AsciiDoc", "Org", "Rich Text Format", "LaTeX", "TeX", "Textile",
                "Creole", "SVG", "MSBuild", "Properties File", "gitignore", "ignore", "Docker ignore", "Patch",
                "Jupyter", "Godot Scene", "Game Maker Project", "XML Schema", "Document Type Definition", "XAML",
                "Qt Translation Source", "Report Definition Language", "Xcode Config", "nuspec", "Module-Definition",
                "SPDX", "TaskPaper", "HEX", "Intel HEX", "CloudFormation (JSON)", "CloudFormation (YAML)",
                "Bitbucket Pipeline", "Systemd", "Windows Resource-Definition Script"}


def form_language(lang, ext=""):
    """A language as forms name it: "C/C++" split by file, "Python (build scripts)" as Python."""
    if lang == "C/C++":
        return "C" if ext == ".c" else "C header" if ext == ".h" else "C++"
    lang = re.sub(r" \(.*\)$", "", lang)
    return FORM_LANGUAGE_NAMES.get(lang, lang)


def primary_language(lines_by_language):
    """(the language with the most lines, as forms name it, or "Other"; its own name) from {language
    as forms name it: lines}. C headers go with C or C++, whichever has more."""
    langs = Counter(lines_by_language)
    headers = langs.pop("C header", 0)
    if headers:
        langs["C" if langs["C"] > langs["C++"] else "C++"] += headers
    top = next((lang for lang, n in langs.most_common(1) if n > 0), None)
    if top is None:
        return None, None
    return (top if top in FORM_LANGUAGES else "Other"), top


# ##############################
# scc and jscpd
# ##############################

# ####################
# Their options
# ####################
SCC_ARGS = ["-x", "csv"]
SCC_GENERATED_ARGS = ["--gen", "--generated-markers", "do not edit,<auto-generated />,<auto-generated>",
                      "--exclude-dir", "vendor,node_modules,dist,build,generated,migrations,Migrations"]
JSCPD_ARGS = ["--min-tokens", "50", "--min-lines", "5", "--reporters", "json"]
JSCPD_IGNORE = ["**/*.csv"]   # forms' --ignore; given in a config file, beside what isn't the studio's


# ####################
# Fetching them
# ####################
# scc and jscpd, the tools buyers' forms name, at pinned versions: fetched once from their official
# releases (GitHub for scc; npmjs.org for jscpd, published there as a self-contained program, so
# Node.js isn't needed), over HTTPS with the certificate checked. The download is checked against
# its SHA-256 checksum below, and so is the program taken out of it, before it's kept, and again
# before every run. Nothing is sent anywhere. They're kept in tools_folder(); deleting it removes
# them. No other copy of scc or jscpd (one installed on this computer, say) is ever run.
SCC_URL = "https://github.com/boyter/scc/releases/download/v4.1.0/scc_"
JSCPD_URL = "https://registry.npmjs.org/jscpd-{0}/-/jscpd-{0}-5.4.1.tgz"
PINNED_TOOLS = {   # tool: (version, the program's place in the download,
    #                       {(system, cpu[, C library]): (url, the download's sha256, the program's sha256)})
    "scc": ("4.1.0", "", {
        ("Darwin", "arm64"): (SCC_URL + "Darwin_arm64.tar.gz",
                              "7201c7aa4aace058d43308462cba72adb18f6094c08c0741727455976d0a0747",
                              "84967748ef1cff481867adff389d0ec138542d30508f1b3aa1186e2bf83de9f0"),
        ("Darwin", "x64"): (SCC_URL + "Darwin_x86_64.tar.gz",
                            "7f705031228add7e55edded409179a60de6b538d41f153ba2922dee95adda50d",
                            "181240384c83fa8055d5676e58a96885846aa3b6757dcebb1d55ee60fe952bd8"),
        ("Linux", "arm64"): (SCC_URL + "Linux_arm64.tar.gz",
                             "6e0d2a1f8d3540ba7df185477dec40bb7340f1b214bfd303147de5cad2bd7b8b",
                             "5751b4f79502ec0fa40e2205347c79c19680fe4cbf4dd31f7daef7bcd4475af7"),
        ("Linux", "x64"): (SCC_URL + "Linux_x86_64.tar.gz",
                           "c7328436d3027f4357d3d7853f7dc3ac2bbcb4ca08f1adad91a27c593884079b",
                           "4763d7437218d2d642e2f2a4f7f078e044aa67e0e15b90bab6c70d5fc0ab4022"),
        ("Linux", "x86"): (SCC_URL + "Linux_i386.tar.gz",
                           "cddeda90ec848c614c6c390eae8b638f94d88e9450e00bf2ba5f420f83b66de1",
                           "5c0bce19affaa9ddcce385ad10d74966f133554fe43a4ed0f045d09cde711387"),
        ("Windows", "arm64"): (SCC_URL + "Windows_arm64.zip",
                               "fdc1188bec07ab46fd391686c404abcd0bed92fffb5f1bb03aa9050dd7bc7f15",
                               "f001ba25f8121b30eef0f6d51eb35c44fbfb922ceebed4376b326db78ef3bc68"),
        ("Windows", "x64"): (SCC_URL + "Windows_x86_64.zip",
                             "4a433984f45ff29c94eeb3af6db5b511c58f5bf74063dccedafcbf473cb8ff31",
                             "b22c38e5bd888d98cdc3987cd125b0041fa1154ed4ef59238052d156461324e8"),
        ("Windows", "x86"): (SCC_URL + "Windows_i386.zip",
                             "7b5b924e85b6fe7f1ba56f15e7e27220a2c0c7089f815368e61f24c6ef317688",
                             "54bbb39702484f960ae051c5bb6cf927ec1dd2dd17b485a95269df38152abecd"),
    }),
    "jscpd": ("5.4.1", "package/bin/", {
        ("Darwin", "arm64"): (JSCPD_URL.format("darwin-arm64"),
                              "cafdb84c9345d0790e4a2297789cfeb16ac939442f322c49a54961468c895aff",
                              "aaa9cd3cef9d1e1e7280e0f4f551b50de533d62f2ec7effb19a99bd6b58d3f7a"),
        ("Darwin", "x64"): (JSCPD_URL.format("darwin-x64"),
                            "43dd411716d0a90803d2ad3d3cd74da96523fc31f13f202c6c6e77b0b4841beb",
                            "da19d3a2de025f52e00550fc2437eb955ccfdc9aa4b3b2c24e7e1e77f86e5c06"),
        ("Linux", "arm64", "gnu"): (JSCPD_URL.format("linux-arm64-gnu"),
                                    "74cbf9d3faa5240d2a17f03a6829fb67cc04f7a37059b3a6f57e9d3adb438b94",
                                    "ea943633332cbf9f14e966f4aa12964a4dfb27e74de7040df0e4303d13afb29f"),
        ("Linux", "arm64", "musl"): (JSCPD_URL.format("linux-arm64-musl"),
                                     "e81c41fa6fa70788c8e47f4eff0ee3d5f00dd8b8cf0489ac7f610105798e4847",
                                     "7227178e87816b8ad54ddb7df084db4c9487ebb34848ead2635b0da162232619"),
        ("Linux", "x64", "gnu"): (JSCPD_URL.format("linux-x64-gnu"),
                                  "5cfd74b986e3d9205dd639a84249203595be67f6062ac652f1b78884b1dea439",
                                  "9656bc09c9a537006735356798c2f4b78299f81e0d57431e7843b88622e74372"),
        ("Linux", "x64", "musl"): (JSCPD_URL.format("linux-x64-musl"),
                                   "28f47a136fc81577ecb67db247b4575abd17941a5682bb57caf7ca967911dc73",
                                   "a2217c30cf91205ccabf7ed42509fcebcac44c2fc1d6c43fe4ef82ecf63c8f7c"),
        ("Windows", "arm64"): (JSCPD_URL.format("windows-arm64-msvc"),
                               "4250180ae1129b22ed6d3e3be7c60c18678fae78d36b2cc65c67d04b0406dad9",
                               "02a68936be7fc3b689318dce55e7120d13e13821375871fd5f5607e91b88bd77"),
        ("Windows", "x64"): (JSCPD_URL.format("windows-x64-msvc"),
                             "657b833dbe8c642984d859bafc9557827ea11808bed76fa23bed63fe6d3da3a0",
                             "d6a514877c1e5c4ac647f4d2f0cb2321b0170d9b5eb088104e809b64020023a9"),
    }),
}
FETCH_TOOLS = True          # --no-download: don't download scc or jscpd (copies downloaded before are still used)
KEEP_TOOL_REPORTS = False   # --reports: save scc's and jscpd's own reports beside this one


def this_computer():
    """(system, cpu, C library) as PINNED_TOOLS names them."""
    import platform
    system = platform.system()
    cpu = platform.machine().lower()
    cpu = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "i386": "x86", "i686": "x86"}.get(cpu, cpu)
    libc = ("gnu" if platform.libc_ver()[0] == "glibc" else "musl") if system == "Linux" else None
    return system, cpu, libc


def pinned_build(name):
    """(url, the download's sha256, the program's sha256) of scc's or jscpd's build for this
    computer, or None if there's none."""
    system, cpu, libc = this_computer()
    builds = PINNED_TOOLS[name][2]
    return builds.get((system, cpu, libc)) or builds.get((system, cpu))


def tools_folder():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "size_codebase_tools")


def download(url):
    """The file at url, over HTTPS with the server's certificate checked as Python always does.
    Raises an exception if it can't be had."""
    import urllib.request
    with urllib.request.urlopen(url, timeout=300) as response:
        return response.read()


def archive_member(data, name):
    """One file's bytes from a .zip or .tar.gz, read by its exact name (nothing else is unpacked)."""
    import io
    if data[:2] == b"PK":
        import zipfile
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return z.read(name)
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        member = t.extractfile(name)
        if member is None:
            raise KeyError(name)
        return member.read()


def find_tool(name):
    """(path, version) of the pinned build of scc or jscpd, downloaded if need be (and allowed), or
    (None, why it can't be used). A copy kept from before is checked against the program's checksum
    each time: one that doesn't match is deleted, and downloaded again if allowed."""
    import hashlib
    version, inside, _ = PINNED_TOOLS[name]
    build = pinned_build(name)
    if build is None:
        system, cpu, _ = this_computer()
        return None, f"{name} has no build for this computer ({system}, {cpu})"
    url, download_sha256, program_sha256 = build
    exe = name + (".exe" if this_computer()[0] == "Windows" else "")
    target = os.path.join(tools_folder(), f"{name}-{version}", exe)

    # ####################
    # A copy kept from before
    # ####################
    replaced = ""
    if os.path.lexists(target):
        if not os.path.islink(target) and file_sha256(target) == program_sha256:
            return target, version
        try:
            os.remove(target)
        except OSError:
            return None, f"the copy of {name} kept on this computer isn't the pinned build, and it couldn't be deleted"
        replaced = f"the copy of {name} kept on this computer wasn't the pinned build, so it was deleted; "

    # ####################
    # Downloading it
    # ####################
    if OFFLINE:
        left_out_offline(f"downloading {name}, which measures some of the standard measures")
        return None, replaced + f"{name} wasn't downloaded, because of --offline"
    if not FETCH_TOOLS:
        return None, replaced + f"{name} isn't downloaded yet, and downloading it was turned off (--no-download)"
    try:
        progress(f"Downloading {name} {version} (once) from {url.split('/')[2]} ...")
        data = download(url)
        if hashlib.sha256(data).hexdigest() != download_sha256:
            raise ValueError("the download doesn't match its checksum, so it wasn't used")
        program = archive_member(data, inside + exe)
        if hashlib.sha256(program).hexdigest() != program_sha256:
            raise ValueError("the program in the download doesn't match its checksum, so it wasn't used")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target + ".part", "wb") as f:
            f.write(program)
        os.chmod(target + ".part", 0o755)
        os.replace(target + ".part", target)
    except Exception as e:   # offline, a proxy, a certificate that can't be checked, a full disk ...
        why = scrub(getattr(e, "reason", None) or e) or type(e).__name__
        return None, replaced + f"{name} couldn't be downloaded ({why})"
    finally:
        progress()
    return target, version


# ####################
# Running them
# ####################

def run_tool(name, path, args, cwd, timeout=900):
    """Runs scc or jscpd (path from find_tool), after checking once more that it's the pinned build."""
    build = pinned_build(name)
    if build is None or os.path.islink(path) or file_sha256(path) != build[2]:
        return None
    return run([path, *args], cwd, timeout)


def added_code(unrecognised=()):
    """The code scc and jscpd are told about: the languages named with --code-ext, and the extensions
    among unrecognised (see UNRECOGNISED_CODE) that they don't name. {extension: (name, like)}."""
    added = {ext: (CODE_EXTS[ext], UNRECOGNISED_CODE[ext]) for ext in unrecognised if ext in UNRECOGNISED_CODE}
    added.update(EXTRA_CODE)
    return added


def extra_code_args(unrecognised=()):
    """(scc's, jscpd's) options for the code they're told about (see added_code)."""
    scc, formats = [], defaultdict(list)
    for ext, (name, like) in sorted(added_code(unrecognised).items()):
        scc_like, jscpd_like = LIKE_LANGUAGES[like]
        for variant in sorted({ext, ext.upper()}):
            scc += ["--count-as-pattern", f"*{glob_escape(variant)}:{name}:{scc_like}"]
        formats[jscpd_like] += [ext[1:], ext[1:].upper()]
    jscpd = ["--formats-exts", ";".join(f"{f}:{','.join(exts)}" for f, exts in sorted(formats.items()))] if formats else []
    return scc, jscpd

def glob_escape(path):
    return re.sub(r"([*?\[\]{}])", r"[\1]", path)


def is_left_out(rel, leave_out):
    """Is this file (relative path, with /) one of leave_out ("folder/**" or "file"), or inside one?"""
    parts = os.path.normcase(rel).replace("\\", "/").split("/")
    return any("/".join(parts[:i]) in leave_out for i in range(1, len(parts) + 1)) or "**" in leave_out


def left_out_paths(root, transitions, files, kept):
    """What scc and jscpd should leave out: the folders where the studio's own code gives way to
    someone else's (or to build output), as "folder/**", and someone else's files among its own.
    kept: paths marked as the studio's own by hand, which may lie inside such a folder; then the
    folder's other contents are left out one by one instead."""
    def key(path):
        return os.path.normcase(path).replace("\\", "/")
    out = set(files)
    kept = [key(k) for k in kept]
    for folder in transitions:
        inside = [k for k in kept if folder == "." or k == key(folder) or k.startswith(key(folder) + "/")]
        if not inside:
            out.add("**" if folder == "." else folder + "/**")
            continue
        pending = [folder]
        while pending:
            current = pending.pop()
            for name in list_files(os.path.join(root, current)):
                path = name if current == "." else current + "/" + name
                if key(path) in inside:
                    continue
                if any(k.startswith(key(path) + "/") for k in inside):
                    pending.append(path)
                else:
                    out.add(path + "/**" if os.path.isdir(os.path.join(root, path)) else path)
    return sorted(out)


def tool_measures(root, leave_out, unrecognised=()):
    """scc's and jscpd's figures, with the options forms give, for the studio's own code: leave_out
    lists the folders ("folder/**") and files that aren't (see left_out_paths). scc counts the whole
    folder file by file, so the figure for all of it comes too. unrecognised: extensions of the
    studio's own code that the tools are told to read (see UNRECOGNISED_CODE); scc's figure without
    them comes too, as the forms' commands give it. ({figures}, {tool: why it wasn't run}, {tool:
    its report to save, if KEEP_TOOL_REPORTS}). jscpd's own report holds copies of the code, so only
    its totals are kept (jscpd_summary)."""
    found, missing, reports = {}, {}, {}
    matching = {os.path.normcase(p[:-3] if p.endswith("/**") else p).replace("\\", "/") for p in leave_out}
    matching |= {"**"} if "**" in leave_out else set()
    scc_extra, jscpd_extra = extra_code_args(unrecognised)
    told = {ext: [name, like] for ext, (name, like) in added_code(unrecognised).items() if ext not in EXTRA_CODE}
    if told:
        found["unrecognised_code_read_as"] = dict(sorted(told.items()))

    # ####################
    # scc
    # ####################
    scc, version = find_tool("scc")
    if scc is None:
        missing["scc"] = version
    else:
        progress("Counting lines with scc ...")
        for key, extra in (("logical", []), ("generated", SCC_GENERATED_ARGS)):
            try:
                langs = json.loads(run_tool("scc", scc, [*SCC_ARGS, *scc_extra, *extra, "--by-file", "--format", "json",
                                                        "."], root) or "null")
            except ValueError:
                langs = None
            if not isinstance(langs, list):
                missing["scc"] = "scc ran, but failed"
                for figure in ("scc_logical_lines", "scc_whole_folder_logical_lines", "scc_logical_lines_by_language",
                               "scc_logical_lines_without_unrecognised"):
                    found.pop(figure, None)
                break
            files = [(str(lang.get("Name", "")), f) for lang in langs for f in lang.get("Files") or []]
            own_files = [(lang, f) for lang, f in files
                         if not is_left_out(re.sub(r"^\.[/\\]", "", str(f.get("Location", ""))), matching)]
            own = [(lang, int(f.get("Code", 0))) for lang, f in own_files]
            if key == "logical":
                found["scc_logical_lines"] = sum(n for _, n in own)
                found["scc_whole_folder_logical_lines"] = sum(int(f.get("Code", 0)) for _, f in files)
                by_lang = Counter()
                for lang, n in own:
                    by_lang[lang] += n
                found["scc_logical_lines_by_language"] = dict(by_lang.most_common())
                if told:
                    found["scc_logical_lines_without_unrecognised"] = sum(
                        int(f.get("Code", 0)) for _, f in own_files
                        if os.path.splitext(str(f.get("Location", "")))[1].lower() not in told)
            else:
                found["scc_generated_lines"] = sum(n for lang, n in own if lang.endswith("(gen)"))
        else:
            found["scc_version"] = version
            if KEEP_TOOL_REPORTS:
                reports["scc"] = run_tool("scc", scc, [*SCC_ARGS, *scc_extra, "--format", "json", "."], root)
        progress()

    # ####################
    # jscpd
    # ####################
    jscpd, version = find_tool("jscpd")
    if jscpd is None:
        missing["jscpd"] = version
    else:
        out = temp_folder("jscpd")
        progress("Measuring duplication with jscpd (slow on big projects) ...")
        try:
            config = os.path.join(out, "jscpd.json")
            with open(config, "w", encoding="utf-8") as f:
                json.dump({"ignore": JSCPD_IGNORE + [glob_escape(p[:-3]) + "/**" if p.endswith("/**") else
                                                     "**" if p == "**" else glob_escape(p) for p in leave_out]}, f)
            run_tool("jscpd", jscpd, [".", *JSCPD_ARGS, *jscpd_extra, "--output", out, "--config", config], root, 3600)
            with open(os.path.join(out, "jscpd-report.json"), encoding="utf-8") as f:
                text = f.read()
            total = json.loads(text)["statistics"]["total"]
            percentage = float(total.get("percentage") or 0)
            found["jscpd_duplication_ratio"] = round(percentage / 100, 4) if percentage == percentage else 0.0
            found["jscpd_duplicated_lines"], found["jscpd_lines"] = total.get("duplicatedLines"), total.get("lines")
            found["jscpd_by_format"] = jscpd_by_format(text)
            found["jscpd_version"] = version
            if KEEP_TOOL_REPORTS:
                reports["jscpd"] = jscpd_summary(text)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            missing["jscpd"] = "jscpd ran, but failed"
        finally:
            shutil.rmtree(out, ignore_errors=True)
            progress()
    return found, missing, reports


def jscpd_by_format(text):
    """jscpd's figures for each kind of file it read (its "formats": python, txt ...), most lines
    first: {format: {"lines", "duplicated_lines", "duplication_ratio"}}. Counts only."""
    out = {}
    for fmt, v in (json.loads(text)["statistics"].get("formats") or {}).items():
        v = (v or {}).get("total") if "total" in (v or {}) else (v or {})
        lines, duplicated = v.get("lines"), v.get("duplicatedLines")
        if not isinstance(lines, int) or not isinstance(duplicated, int):
            continue
        out[re.sub(r"[^\w+#.-]", "", str(fmt))[:40]] = {
            "lines": lines, "duplicated_lines": duplicated,
            "duplication_ratio": round(duplicated / lines, 4) if lines else 0.0}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["lines"]))


def jscpd_summary(text):
    """jscpd's report cut down to its totals, as forms ask for it ({"statistics": ...}): the numbers
    for each format and in all, and the date. The rest of the report (each copy, with the code
    copied and the files it's in) is left behind, and so is anything in the totals that isn't a
    number, so no code and no file name can get through."""
    stats = json.loads(text)["statistics"]

    def numbers(d):
        return {k: v for k, v in (d or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    return json.dumps({"statistics": {
        "detectionDate": str(stats.get("detectionDate", ""))[:40],
        "formats": {re.sub(r"[^\w+#.-]", "", str(fmt))[:40]: numbers((v or {}).get("total") if "total" in (v or {}) else v)
                    for fmt, v in (stats.get("formats") or {}).items()},
        "total": numbers(stats.get("total"))}}, indent=2)


# ##############################
# Report section
# ##############################
AI_ERA = "2022"   # changes made before this year were almost certainly written without AI assistants
TOOL_FIGURES = {"scc": "logical lines of code and generated lines (scc)", "jscpd": "the duplication ratio (jscpd)"}


def standard_measures_report(histories, vcs_found, tools, missing, left_out, own_languages, database_languages):
    """(report lines, facts) for the standard measures: scc's and jscpd's figures (see tool_measures)
    where they could be run (missing: {tool: why not}), the commits forms count, and the primary
    language. own_languages: the apparently original code's non-blank lines by language as forms
    name them (the tables above); database_languages: the part of them read from databases, which
    scc can't see."""

    # ####################
    # The figures
    # ####################
    # A history converted into another system's, which is also here, is counted in that one (see
    # across_systems): it isn't another repository, and its changes aren't counted again.
    live = [h for h in histories if not h.get("held_by")]
    counted = [h for h in live if h.get("standard_commits") is not None]
    commits = sum(max(0, h["standard_commits"] - h.get("standard_duplicates", 0)) for h in counted)
    twice = sum(h.get("standard_duplicates", 0) for h in counted)
    dates = [r.date for h in histories for i, r in enumerate(h.get("records", ()))
             if r.date and i not in h.get("counted_elsewhere", ())]
    before = sum(1 for d in dates if d < AI_ERA)
    shallow = any("shallow clone" in note for h in live for note in h.get("notes", ()))
    if not live:
        delivery = "flat snapshot (no version-control history found)"
    elif all(h["vcs"] == "Git" for h in live):
        delivery = "Git, but a shallow clone: its older history is missing" if shallow else "Git, full history"
    else:
        delivery = (f"{', '.join(sorted({h['vcs'] for h in live}))}: convert it to Git, or deliver a flat"
                    " snapshot")
    where = "; ".join(f"{h['vcs']}" + (f" {h['standard_branch']}" if h.get("standard_branch") else "")
                      for h in counted)
    scc = "scc_logical_lines" in tools
    jscpd = "jscpd_duplication_ratio" in tools
    measured = " and ".join(f"{t} {tools[t + '_version']}" for t in ("scc", "jscpd") if t + "_version" in tools)

    # Primary language: by scc's logical lines, with the code read from databases (which scc can't
    # see) as its non-blank lines; without scc, by the non-blank lines in the tables above.
    database_lines = sum(database_languages.values())
    if scc:
        langs = Counter()
        for lang, n in tools.get("scc_logical_lines_by_language", {}).items():
            if lang not in SCC_NOT_CODE:
                langs[form_language(lang)] += n
        langs.update(database_languages)
        basis = "scc's logical lines" + (", and the non-blank lines of the code read from databases, which scc can't"
                                         " see" if database_lines else "")
    else:
        langs = own_languages
        basis = "this script's own line counts above (non-blank lines), as scc wasn't run"
    language, raw = primary_language(langs)

    # ####################
    # Report lines
    # ####################
    out = ["", "Standard measures, as buyers' codebase forms ask for them, of the apparently original code above"
               + (f"\n(measured with {measured}, with the forms' options):" if measured else ":")]
    if scc:
        out += [f"  {'Logical lines of code (scc)':<56} {tools['scc_logical_lines']:>12,}",
                f"  {'  of which generated (scc --gen)':<56} {tools['scc_generated_lines']:>12,}"]
    if jscpd:
        out.append(f"  {'Duplication ratio (jscpd)':<56} {tools['jscpd_duplication_ratio']:>12.4f}")
    out += [f"  {'Commits on the main branch, without merges or reverts':<56} "
            + (f"{commits:>12,}   ({where})" if counted else f"{'none':>12}"),
            f"  {'Repositories':<56} {max(1, len(live)):>12,}",
            f"  {'Primary language':<56} {language or '?':>12}" + (f"   ({raw})" if raw and raw != language else ""),
            f"  {'History':<56} {delivery}"]
    if dates:
        out.append(f"  {'Changes made before ' + AI_ERA + ' (before AI coding assistants)':<56} {before:>12,}"
                   f"   of {len(dates):,} ({100 * before // len(dates)}%)")
    if measured and left_out:
        n = len(left_out)
        out.append(f"  (left out as not the studio's own: {n:,} {'folder or file' if n == 1 else 'folders and files'},"
                   " such as libraries, plugins, build output and translations"
                   + (f"; the whole folder has {tools['scc_whole_folder_logical_lines']:,} logical lines)" if scc
                      else ")"))
    told = tools.get("unrecognised_code_read_as") or {}
    if told and (scc or jscpd):
        by_name = defaultdict(list)
        for ext, (name, like) in told.items():
            by_name[(name, like)].append(ext)
        how = "; ".join(f"{', '.join(exts)} as {name}, " + ("every non-blank line counted" if like == "text"
                                                             else f"with {like}'s comments")
                        for (name, like), exts in sorted(by_name.items()))
        which = " and ".join(t for t, ran in (("scc", scc), ("jscpd", jscpd)) if ran)
        out.append(f"  ({which} {'doesn' if which in ('scc', 'jscpd') else 'don'}'t recognise some of the code, so"
                   f" {'it was' if which in ('scc', 'jscpd') else 'they were'} told to read it: {how}"
                   + (f". Without it, as the forms' commands give it: "
                      f"{tools['scc_logical_lines_without_unrecognised']:,} logical lines)"
                      if "scc_logical_lines_without_unrecognised" in tools else ")"))
    formats = tools.get("jscpd_by_format") or {}
    if jscpd and len(formats) > 1:
        out.append("  (jscpd by kind of file: " + ", ".join(
            f"{fmt} {v['duplication_ratio']:.4f} of {plural(v['lines'], 'line')}" for fmt, v in formats.items()) + ")")
    if language and (not scc or database_lines):
        out.append(f"  (primary language from {basis})")
    if counted and len(counted) < len(live):
        out.append(f"  (commits from {len(counted)} of the {len(live)} histories: the others couldn't be counted)")
    held = [h for h in histories if h.get("held_by")]
    if held or twice:
        out.append("  (" + "; ".join([f"the {short_name(h['vcs'])} history is already in {h['held_by']}'s, so it isn't"
                                      " counted again" for h in held]
                                     + ([f"{plural(twice, 'change')} in two systems' histories counted once"] if twice
                                        else [])) + ")")

    # ####################
    # What's not included, and how to include it
    # ####################
    if missing:
        out += ["", "NOTE: Not included in the standard measures above, as the tool that measures them couldn't be used:"]
        out += [f"      - {TOOL_FIGURES[tool]}: {why}" for tool, why in missing.items()]
        whys = " ".join(missing.values())
        if "download" in whys:
            out.append("      To include them, run this again on a computer with an internet connection"
                       + (", without --offline" if OFFLINE else ", without --no-download" if not FETCH_TOOLS else "")
                       + ": scc and jscpd are downloaded once, then kept.")
        if "certificate" in whys.lower() and sys.platform == "darwin":
            out += ["      The download failed because Python couldn't check the server's certificate. With Python from",
                    "      python.org, open the Python folder in Applications, double-click \"Install Certificates.command\",",
                    "      then run this again."]

    # ####################
    # Facts, for the machine-readable copy
    # ####################
    facts = {"logical_lines": tools["scc_logical_lines"] if scc else None,
             "generated_lines": tools["scc_generated_lines"] if scc else None,
             "duplication_ratio": tools["jscpd_duplication_ratio"] if jscpd else None,
             "measured_with": measured or None, "not_measured": missing,
             "commits_main_branch_no_merges_or_reverts": commits if counted else None,
             "commit_branches": where or None, "repositories": max(1, len(live)),
             "primary_language": language, "primary_language_detail": raw,
             "primary_language_from": basis if language else None, "history": delivery,
             "changes_before_" + AI_ERA: [before, len(dates)] if dates else None,
             "left_out": len(left_out) if measured else None,   # how many: their names stay out of reports
             "version_control": vcs_found, **tools}
    return out, facts


# #######################################
# Sizing a project
# #######################################

def size_project(root, third_party=(), own=(), facts=None, sql_servers=(), only=None, sourcesafe=()):
    """The report for one folder. third_party / own: folders or files (relative to root, or
    absolute) that the user says are someone else's code, or their own. facts: a dict to fill
    with the report's numbers, for the machine-readable copy. only: the one file in root to
    look at (e.g. an Access database given on its own), instead of the whole folder.
    sourcesafe: SourceSafe databases elsewhere (folders with srcsafe.ini) that hold its history."""

    # ##############################
    # Setting up
    # ##############################

    # ####################
    # The folder, and what the user marked
    # ####################
    root = os.path.abspath(root)
    walk_root = long_path(root)
    marked = {os.path.normcase(os.path.abspath(os.path.join(root, p))): c
              for c, paths in (("third-party", third_party), ("own", own)) for p in paths}
    del _git_other_owners[:], _left_out_offline[:]   # noted afresh for each project

    # ####################
    # What the walk collects
    # ####################
    problems = []           # unexpected errors: reported, but the scan carries on
    alerts = []             # what a reader should check, for the summary at the top
    links = lfs_pointers = epic_notice_lines = 0   # links: symbolic links and junctions, not followed
    vendor_notice_lines = Counter()
    licensed_dirs = []      # own folders with their own licence file: pointed out in the report
    store_guids = None      # Unity Asset Store packages downloaded on this computer, once a Unity project is found
    categories = ("own", "test", "third-party", "engine", "generated", "translation", "data")
    lines_by = {c: defaultdict(lambda: [0, 0]) for c in categories}
    own_lines_by_dir = Counter()
    libraries = Counter()   # third-party lines by library or licence
    custom_engines = []     # (project folder, engine association) of projects on a custom-built engine
    engine_sources = []     # folders holding a source copy of Unreal Engine (Engine/Build/Build.version)
    nested_repos = []       # (rel, path) of repositories inside the scanned folder
    deps = Dependencies(root)
    dbcode = DatabaseCode()
    test_coverage = CoverageReports()
    source_lines = Counter()   # own lines read from source files, by language (the rest came from databases)
    unrecognised = set()       # extensions of the studio's own code that scc and jscpd must be told about
    c_family = Counter()       # own C/C++ lines, as forms name them: "C", "C header", "C++"
    not_own_folders = []    # where the studio's own code gives way to someone else's, or to build output
    unknown_text = defaultdict(lambda: [0, 0])   # text files of unknown kinds among the studio's own: [files, bytes]
    textual = {}            # extension -> whether its files are text
    not_own_files = []      # someone else's files among the studio's own
    vss = SourceSafe(sourcesafe)
    dac_packages = []       # (category, contents) of .dacpac / .bacpac files, counted once .sql names are known
    digests = set()
    duplicates = [0, 0]     # own files that are exact copies of another one: [files, lines]
    console = Counter()     # own lines in console-platform folders and files, by platform
    binaries = Counter()    # precompiled libraries: "own" / "third-party" folders
    secrets = Counter()     # kind of credential -> files
    copyright_years = Counter()
    named_authors = []      # people named as authors in the comments of the studio's own code
    mtimes = []             # [earliest, latest] modification time of the studio's own code files
    tracked = git_tracked_files(root)
    untracked = [0, 0]      # own code files not committed to Git: [files, lines]
    submodule_marks = {}    # folder -> (category, library) for Git submodules
    submodule_list = []     # (folder, third-party?)
    root_owner = repo_owner(next((url for remote, url in git_remotes(root) if remote == "origin"), ""))
    assets = Counter()
    projects = []
    total_bytes = total_files = 0
    years = Counter()
    build_files = set()   # telltale files of a built (compiled) Unity game
    # Unreal: visual scripting by row and category ([files, nodes]); versions that saved the assets;
    # cooked assets; UnrealScript compiled into UE1/2 .u files ([packages, classes, lines]).
    graphs = {c: defaultdict(lambda: [0, 0]) for c in ("own", "third-party", "engine")}
    unreal_versions = Counter()
    coverage = Counter()    # UE3-5 packages by how much of them could be read (see read_unreal_package)
    cooked = 0
    compiled_script = [0, 0, 0]

    # ####################
    # What each folder passes on to its subfolders
    # ####################
    # Inherited by each folder: its category ("own", "test", "third-party" or "engine"); where it
    # is relative to a Unity project (None, "assets" = the Assets folder itself, "inside" = below
    # it); which kinds of project enclose it; and, for third-party code, the library's name.
    inherited = {walk_root: ("own", None, frozenset(), None, None)}

    # ##############################
    # Walking the folder
    # ##############################
    for dirpath, dirnames, filenames in os.walk(walk_root):
        if only:
            dirnames[:], filenames[:] = [], [f for f in filenames if f == only]

        # ####################
        # The kinds of project rooted here
        # ####################
        category, unity, enclosing, library, platform = inherited.pop(dirpath)
        came_own = category in ("own", "test")
        in_unity_assets = unity is not None
        rel = os.path.relpath(dirpath, walk_root)
        if vss.visit(dirpath, filenames):   # a SourceSafe database: its history is read below, its files aren't code
            dirnames[:] = []
            continue
        kinds = detect_kinds(dirpath, filenames, dirnames)
        for kind, detail in kinds.items():
            if kind in enclosing or (kind == "UnrealScript" and (enclosing | set(kinds)) & (UNREAL_KINDS - {kind})):
                continue   # don't list e.g. docs/requirements.txt as a second project
            projects.append((kind, rel, detail))
        if kinds.get("Unreal") == CUSTOM_ENGINE:
            custom_engines.append((dirpath, engine_association(dirpath, filenames)))
        if "Unreal Engine source" in kinds:
            engine_sources.append(os.path.dirname(short_path(dirpath)))
        progress(f"Scanning: {total_files:,} files so far ...")
        enclosing = enclosing | set(kinds)
        if "Unity" in kinds and store_guids is None:
            store_guids = asset_store_guids()[0]
        skip = set(ALWAYS_SKIP)
        for kind in kinds:
            skip |= ROOT_SKIP.get(kind, set())

        # ####################
        # Whose code this folder is
        # ####################
        # Unreal folders that are someone else's code: the engine itself, bought plugins, and
        # Epic's UnrealScript packages in UE1-3 games.
        uplugin = next((f for f in filenames if f.lower().endswith(".uplugin")), None)
        if uplugin:
            skip |= UNREAL_PLUGIN_SKIP
        if category in ("own", "test"):
            if "Unreal Engine source" in kinds:
                category = "engine"
            elif uplugin and is_bought_unreal_plugin(os.path.join(dirpath, uplugin)):
                category, library = "third-party", os.path.basename(dirpath)
            elif (not in_unity_assets and os.path.basename(dirpath).lower() in EPIC_UNREAL_PACKAGES
                  and {d.lower() for d in dirnames} & {"classes", "inc", "src"}):
                category = "engine"
            elif unity == "inside" and store_guids and store_guids.get(meta_guid(short_path(dirpath))):
                category, library = "third-party", "Asset Store: " + store_guids[meta_guid(short_path(dirpath))]
            elif unity == "inside" and looks_like_asset_store_package(dirpath, filenames, dirnames):
                category, library = "third-party", os.path.basename(dirpath)
            elif rel != "." and any(LICENSE_FILE.match(f) for f in filenames):
                if not kinds and any(os.path.splitext(f)[1].lower() in CODE_EXTS
                                     for f in list_files(os.path.dirname(dirpath))):
                    category, library = "third-party", os.path.basename(dirpath)
                else:
                    licensed_dirs.append(rel)
        if ".gitmodules" in filenames:
            # A submodule from another owner's repository is a library someone else wrote.
            owner = repo_owner(run(["git", "remote", "get-url", "origin"], short_path(dirpath), 60) or "") or root_owner
            for sub_path, url in submodules(short_path(dirpath)):
                theirs = bool(owner and repo_owner(url) and repo_owner(url) != owner)
                name = re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]) or sub_path
                full = os.path.normcase(os.path.abspath(os.path.join(short_path(dirpath), sub_path)))
                if theirs:
                    submodule_marks[full] = ("third-party", name)
                submodule_list.append((name, theirs))
        mark = submodule_marks.get(os.path.normcase(short_path(dirpath)))
        if mark and category in ("own", "test"):
            category, library = mark
        hand = marked.get(os.path.normcase(short_path(dirpath)))
        if hand:   # the user knows best
            category, library = hand, (os.path.basename(dirpath) if hand == "third-party" else None)
        here_own = category in ("own", "test")
        rel_slash = rel.replace(os.sep, "/")
        if came_own and not here_own:
            not_own_folders.append(rel_slash)

        # ####################
        # Repositories inside the scanned folder
        # ####################
        if rel != "." and category in ("own", "test"):
            here = set(dirnames) | set(filenames)
            for marker, name in REPOSITORY_MARKERS.items():
                first = marker.split(os.sep)[0]
                # Old SVN, CVS and SourceSafe put their folder in every folder: only the top one counts.
                if first in here and marker_is(os.path.join(dirpath, marker), marker) and \
                        not os.path.exists(os.path.join(os.path.dirname(dirpath), marker)):
                    nested_repos.append((rel, short_path(dirpath)))
                    break

        # ####################
        # Which subfolders to enter, and as whose code
        # ####################
        in_unreal_content = "Unreal" in enclosing and os.path.basename(dirpath).lower() == "content"
        in_renpy_game = "Ren'Py" in enclosing and os.path.basename(dirpath).lower() == "game"
        in_unity_packages = "Unity" in enclosing and unity is None and os.path.basename(dirpath).lower() == "packages"

        consoles = console_children(dirnames)
        kept = []
        for d in dirnames:
            dl = d.lower()
            full = os.path.join(dirpath, d)
            listed = here_own and dl not in (".git", ".svn", ".hg", ".bzr")
            if listed:   # until it's found to be the studio's own, below
                not_own_folders.append(d if rel == "." else f"{rel_slash}/{d}")
            if here_own:
                test_coverage.saw_folder(d, rel)
            if dl in skip or dl.endswith(".egg-info") or os.path.isfile(os.path.join(full, "pyvenv.cfg")):
                if here_own and dl in COVERAGE_OUTPUT_DIRS and not is_link(full):
                    test_coverage.search(full, os.path.join(rel, d))   # build output, but tests write reports there
                continue
            if dl.startswith("cmake-build-") or os.path.isfile(os.path.join(full, "CMakeCache.txt")):
                if here_own and not is_link(full):
                    test_coverage.search(full, os.path.join(rel, d))
                continue   # a CMake build folder
            if dl == "packages" and any(f.lower().endswith(".nupkg") for sub in list_files(full)[:5]
                                        for f in list_files(os.path.join(full, sub))):
                continue   # NuGet's downloaded packages
            if is_link(full):
                links += 1
                continue
            child, child_library = category, library
            if category in ("own", "test"):
                if dl in KNOWN_LIBRARY_DIRS:
                    child, child_library = "third-party", d
                elif in_renpy_game and dl == "tl":
                    child = "translation"   # Ren'Py's translations of the game's text into other languages
                elif in_unity_assets and dl in UNITY_ASSET_STORE_DIRS:
                    child, child_library = "third-party", d
                elif (dl in THIRD_PARTY_DIRS or (in_unity_assets and dl in UNITY_PLUGIN_DIRS)
                        or ("Godot" in kinds and dl == "addons")):
                    child, child_library = "third-party", None   # a folder of libraries, named by its subfolders
                elif ((unity == "assets" and (dl in UNITY_ASSETS_THIRD_PARTY_DIRS or dl.startswith("standard assets")))
                        or (in_unity_packages and dl.startswith("com.unity."))
                        or ("Ren'Py" in kinds and dl in RENPY_ROOT_THIRD_PARTY_DIRS)
                        or (in_unreal_content and dl in UNREAL_CONTENT_THIRD_PARTY_DIRS)):
                    child, child_library = "third-party", d      # one package
                elif dl in TEST_DIRS:
                    child = "test"
            elif category == "third-party" and library is None:
                child_library = d   # e.g. ThirdParty/boost
            if "Unity" in kinds and dl == "assets":
                child_unity = "assets"
            else:
                child_unity = "inside" if in_unity_assets else None
            inherited[full] = (child, child_unity, enclosing, child_library, platform or (d if d in consoles else None))
            kept.append(d)
            if listed and child in ("own", "test"):
                not_own_folders.pop()
        dirnames[:] = kept

        # ##############################
        # The folder's files
        # ##############################
        for name in filenames:
            try:
                if name.startswith("._"):   # macOS metadata left on non-Mac drives and in zips
                    continue

                # ####################
                # Every file: size, dependencies, precompiled libraries, data and credentials
                # ####################
                path = os.path.join(dirpath, name)
                if os.path.islink(path):   # not followed, like linked folders
                    links += 1
                    continue
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not S_ISREG(st.st_mode):   # a named pipe or device: reading it could wait forever
                    continue
                total_files += 1
                if name.lower() in UNITY_BUILD_FILES:
                    build_files.add(name.lower())
                total_bytes += st.st_size
                ext = os.path.splitext(name)[1].lower()
                rel_file = os.path.join(rel, name) if rel != "." else name
                deps.saw_file(rel_file)
                if category in ("own", "test"):
                    if BUILD_FILE.match(name):
                        deps.saw_build_file(path, name)
                    if MANIFEST_FILE.match(name) or (name.lower() == "manifest.json" and in_unity_packages):
                        deps.saw_manifest(path, name)
                    test_coverage.saw_file(path, name, rel, st)
                if ext in BINARY_LIBRARY_EXTS:
                    binaries["own" if category in ("own", "test") else "third-party"] += 1
                if ext in DATA_FILE_EXTS and st.st_size >= DATA_FILE_MIN and name.lower() != "thumbs.db" \
                        and category != "third-party":
                    dbcode.data["Data files (.csv, .xlsx, .sqlite, database dumps ...)"] += 1
                    dbcode.data_bytes["Data files (.csv, .xlsx, .sqlite, database dumps ...)"] += st.st_size
                if KEY_FILES.match(name):
                    secrets["key or credential files (.pem, .p12, .env ...)"] += 1
                elif ext in SECRET_SCAN_EXTS and st.st_size < 1_000_000 and category != "third-party":
                    try:
                        with open(path, "rb") as f:
                            for kind in secrets_in(f.read()):
                                secrets[kind] += 1
                    except OSError:
                        pass

                # ####################
                # Unreal packages
                # ####################
                if ext in UNREAL_PACKAGE_EXTS:
                    info = read_unreal_package(path)
                    if info is None and st.st_size < 1024 and is_lfs_pointer(path):
                        lfs_pointers += 1
                    if ext in (".uasset", ".umap"):
                        assets[unreal_asset_kind(info, ext, os.path.join(rel, name))] += 1
                    else:
                        assets[next(k for k, exts in ASSET_EXTS.items() if ext in exts)] += 1
                    if info:
                        c = category
                        if c != "engine" and ext == ".u" and os.path.splitext(name)[0].lower() in EPIC_UNREAL_PACKAGES:
                            c = "engine"
                        g = "own" if c in ("own", "test") else c
                        for row, nodes in graph_rows(info):
                            graphs[g][row][0] += 1
                            graphs[g][row][1] += nodes
                        if g == "own":
                            if info["engine"] in ("UE3", "UE4", "UE5"):   # the ones that can hold graphs
                                coverage[info["status"]] += 1
                                coverage["unreadable, looks like Blueprint"] += info["looks_like_blueprint"]
                                coverage["Blueprints with no nodes"] += (
                                    info["status"] == "read" and (info["main_class"] or "").endswith("Blueprint")
                                    and not sum(info["nodes"].values()))
                            unreal_versions[info["version"] or info["engine"]] += 1
                            cooked += info["cooked"]
                            if info["classes"]:
                                compiled_script[0] += 1
                                compiled_script[1] += info["classes"]
                                compiled_script[2] += info["script_lines"]
                    continue

                # ####################
                # Database files
                # ####################
                if ext in ACCESS_EXTS or ext in SQL_SERVER_FILES or ext in DAC_EXTS or ext in (".dtsx", ".ispac", ".rdl", ".rdlc"):
                    database_file(path, ext, name, category, st, dbcode, dac_packages, lines_by, assets)
                    continue

                # ####################
                # Its language (or else an asset, or text of an unknown kind)
                # ####################
                lang = CODE_EXTS.get(ext)
                if lang is None and ext in ACCESS_EXPORT_EXTS:
                    try:
                        with open(path, "rb") as f:
                            if access_export(f.read(4000)):
                                lang = "Access objects"   # an Access object exported as text: see below
                    except OSError:
                        pass
                context = CONTEXT_CODE_EXTS.get(ext)
                if context and context[0] in enclosing:
                    lang = context[1]
                if BUILD_SCRIPTS.match(name):
                    lang = BUILD_SCRIPT_LANGUAGE.get(ext, "Python (build scripts)" if name.lower() in
                                                     ("sconstruct", "sconscript", "wscript") else "Make (build scripts)")
                if lang is None:
                    asset = next((kind for kind, exts in ASSET_EXTS.items() if ext in exts), None)
                    if asset:
                        assets[asset] += 1
                    elif ext and ext not in NOT_CODE_TEXT and category in ("own", "test"):
                        if ext not in textual:   # judged by its first file: no NUL bytes means text
                            try:
                                with open(path, "rb") as f:
                                    textual[ext] = b"\0" not in f.read(4096)
                            except OSError:
                                textual[ext] = False
                        if textual[ext]:
                            unknown_text[ext][0] += 1
                            unknown_text[ext][1] += st.st_size
                    continue
                if ext == ".js" and in_unity_assets:
                    lang = "UnityScript"
                elif ext == ".as" and "Unreal" in enclosing:
                    lang = "AngelScript"
                elif name.lower().endswith((".build.cs", ".target.cs")):
                    lang = "C# (build rules)"   # Unreal's build scripts

                # ####################
                # Reading the code
                # ####################
                code = read_code_file(path, ext)
                lines, generated, licence = code["lines"], code["generated"], code["licence"]
                if "language" in code:            # Visual Basic or an exported Access object, looked at closely
                    if code.get("access_object") and category in ("own", "test"):
                        dbcode.access_exports[{"query": "queries"}.get(code["access_object"], code["access_object"] + "s")] += 1
                    if not code["lines"] and (code["language"] is None or code.get("access_object") == "query"):
                        continue                  # not code (a LaTeX class, an Access macro), or counted elsewhere
                    lang = code["language"] or lang
                    if lang == "Visual Basic / VBA" and "Visual Basic 6" in enclosing:
                        lang = "Visual Basic 6"
                    elif lang == "Visual Basic / VBA" and enclosing & {"Microsoft Access", "Microsoft Access (exported as text)"}:
                        lang = "VBA (Access)"
                for kind in code["secrets"]:
                    secrets[kind] += 1

                # ####################
                # Whose code this file is
                # ####################
                known = next((label for pattern, label in KNOWN_LIBRARY_FILES if pattern.match(name)), None)
                c = category
                hand = marked.get(os.path.normcase(short_path(path)))
                if hand:
                    c, known = hand, (name if hand == "third-party" else None)
                elif generated or GENERATED_FILE.search(name):
                    c = "generated"
                elif c in ("own", "test") and (known or (licence and licence not in ENGINE_NOTICES)):
                    c = "third-party"   # a library file copied in among the studio's own
                elif c in ("own", "test") and in_unity_assets and store_guids and store_guids.get(meta_guid(path)):
                    c, known = "third-party", "Asset Store: " + store_guids[meta_guid(path)]
                elif c in ("own", "test") and code["data"]:
                    c = "data"          # an image, font or table pasted in as numbers, or a script of INSERTs
                elif c == "own" and TEST_FILE.search(name):
                    c = "test"

                # ####################
                # Counting it
                # ####################
                if code.get("data_lines") and c in ("own", "test"):
                    dbcode.data["SQL scripts with INSERT statements (rows of data)"] += 1
                    dbcode.data_bytes["SQL scripts with INSERT statements (rows of data)"] += st.st_size
                if code.get("data_lines"):   # the INSERTs in a SQL script: data, not code
                    lines_by["data" if c in ("own", "test") else c][lang + " (INSERT statements)"][0] += 1
                    lines_by["data" if c in ("own", "test") else c][lang + " (INSERT statements)"][1] += code["data_lines"]
                    if not lines:
                        continue             # nothing but data
                lines_by[c][lang][0] += 1
                lines_by[c][lang][1] += lines
                if c in ("third-party", "engine") and category in ("own", "test"):
                    not_own_files.append(rel_file.replace(os.sep, "/"))
                if c in ("own", "test"):
                    source_lines[lang] += lines
                    if ext in UNRECOGNISED_CODE and lines:
                        unrecognised.add(ext)
                    if lang == "C/C++":
                        c_family[form_language(lang, ext)] += lines
                if c == "third-party":
                    libraries[library or known or licence or "other"] += lines
                if c in ("own", "test") and licence == EPIC_NOTICE:
                    epic_notice_lines += lines
                elif c in ("own", "test") and licence in ENGINE_NOTICES:
                    vendor_notice_lines[licence] += lines
                if c in ("own", "test"):
                    for kind, key in code.get("sql_objects", ()):
                        if (kind, key) not in dbcode.sql_defined:   # each object once, however often it's altered
                            dbcode.sql_defined.add((kind, key))
                            dbcode.sql_files[kind] += 1
                        dbcode.sql_keys.add(key)

                # ####################
                # What else the studio's own code shows
                # ####################
                if c in ("own", "test") and lines:
                    own_lines_by_dir[rel] += lines
                    years[datetime.fromtimestamp(st.st_mtime, timezone.utc).year] += 1
                    mtimes[:] = [min(mtimes[0], st.st_mtime), max(mtimes[1], st.st_mtime)] if mtimes else [st.st_mtime] * 2
                    deps.includes.update(code["includes"])
                    engine = next((name for kind, name in (("Unreal", "Unreal Engine"), ("Godot", "Godot (godot-cpp)"),
                                                           ("Source engine (Valve)", "Source SDK"), ("CRYENGINE", "CRYENGINE"))
                                   if kind in enclosing), None)
                    if engine:
                        for include in code["includes"]:
                            deps.engine_includes.setdefault(include, engine)
                    copyright_years.update(code["years"])
                    named_authors += code["authors"]
                    if code["digest"] in digests:
                        duplicates[0] += 1
                        duplicates[1] += lines
                    digests.add(code["digest"])
                    file_platform = platform or (CONSOLE_FILE.search(name) or [None, None])[1]
                    if file_platform:
                        console[file_platform] += lines
                    if tracked is not None and os.path.normcase(rel_file) not in tracked:
                        untracked[0] += 1
                        untracked[1] += lines
            except Exception as e:   # an unexpected file shouldn't cost the whole report
                problem = describe(e, root)
                if len(problems) < 5 and problem not in problems:
                    problems.append(problem)
        progress()

    # ##############################
    # Code inside databases
    # ##############################

    # ####################
    # Access databases
    # ####################
    count_access_code(dbcode, lines_by)
    for _, _, got in dbcode.access:
        if got.get("category", "own") in ("own", "test") and not got.get("exported"):
            for vba in got.get("vba", []):
                named_authors += authors_in(vba.encode("utf-8", "replace"))

    # ####################
    # .dacpac and .bacpac packages
    # ####################
    # Database code that may also be in the .sql scripts: counted once, the scripts' copy first.
    for c, got in dac_packages:
        for kind, key, body in got["code"]:
            if key not in dbcode.sql_keys:
                lines_by[c]["T-SQL (in .dacpac / .bacpac packages)"][0] += 1
                lines_by[c]["T-SQL (in .dacpac / .bacpac packages)"][1] += count_text_lines(body)
        for script in got["scripts"]:
            lines = [l for l in script.encode("utf-8").splitlines() if l.strip()]
            inserts = sql_data_lines(lines)
            lines_by[c]["SQL (in .dacpac / .bacpac packages)"][0] += 1
            lines_by[c]["SQL (in .dacpac / .bacpac packages)"][1] += len(lines) - inserts
            if inserts:
                lines_by["data"]["SQL (INSERT statements)"][0] += 1
                lines_by["data"]["SQL (INSERT statements)"][1] += inserts

    # ####################
    # Running SQL Servers (--sql-server)
    # ####################
    for server, databases in sql_servers:
        dbcode.live = read_sql_server(server, databases)
        for kind, key, definition in dbcode.live.get("code", ()):
            if key.split(".", 1)[-1] not in dbcode.sql_keys:
                lines_by["own"]["T-SQL (in the SQL Server database)"][0] += 1
                lines_by["own"]["T-SQL (in the SQL Server database)"][1] += count_text_lines(definition)

    # ##############################
    # The report
    # ##############################

    # ####################
    # Tables of lines by language
    # ####################
    def table(buckets):
        merged = defaultdict(lambda: [0, 0])
        for b in buckets:
            for lang, (files, lines) in b.items():
                merged[lang][0] += files
                merged[lang][1] += lines
        rows = [f"  {lang:<18} {lines:>11,} lines  {files:>8,} files"
                for lang, (files, lines) in sorted(merged.items(), key=lambda kv: -kv[1][1])]
        return rows, sum(v[1] for v in merged.values())

    # ####################
    # Project types, version control and size
    # ####################
    try:
        vcs_found, histories = version_control(root)
    except Exception as e:
        vcs_found, histories = [], []
        problems.append(f"reading the version-control history: {describe(e, root)}")
    out = [f"size_codebase.py {__version__}" + (" (run with --offline: no connections to other computers)"
                                                 if OFFLINE else ""),
           f"Project: {only or os.path.basename(root)}"]
    kinds_found = Counter(kind for kind, _, _ in projects)
    if projects:
        out.append("Project types found:")
        for kind, count in kinds_found.items():
            entries = [(r, d) for k, r, d in projects if k == kind]
            if count <= 5:
                for r, d in entries:
                    where = "top level" if r == "." else r.split(os.sep)[0] + ("/..." if os.sep in r else "")
                    out.append(f"  {kind}{' ' + d if d else ''}  ({where})")
            else:
                out.append(f"  {kind}  ({count} projects)")
    else:
        out.append("Project types found: none recognized (counted by file extension)")
    if unreal_versions:
        found = sorted(unreal_versions.items(), key=lambda kv: [int(n) if n.isdigit() else 0
                                                                 for n in re.findall(r"\d+|\D+", kv[0])])
        out.append("Unreal versions that saved the assets: "
                   + ", ".join(f"{v} ({plural(n, 'file')})" for v, n in found[:8])
                   + (f", and {len(found) - 8} more" if len(found) > 8 else ""))
    out += [f"Version control: {', '.join(vcs_found) or 'none found'}",
            f"Total size: {total_bytes / 1e9:.2f} GB in {total_files:,} files "
            "(excluding dependencies, caches and build output)",
            "",
            "Apparently original source code (non-blank lines). This is code that looks like the studio's own;",
            "it is not a finding on legal ownership or licensing rights:"]

    # ####################
    # Apparently original code
    # ####################
    rows, own_total = table([lines_by["own"], lines_by["test"]])
    out += rows + [f"  {'TOTAL':<18} {own_total:>11,} lines"]
    test_total = sum(v[1] for v in lines_by["test"].values())
    if test_total:
        out.append(f"  (of which tests: {test_total:,} lines)")
    if epic_notice_lines:
        out.append(f"  (of which {epic_notice_lines:,} lines in files with Epic's copyright notice: usual for files that"
                   " began from Unreal's templates, but check none are copied from the engine)")
    for notice, n in vendor_notice_lines.most_common():
        out.append(f"  (of which {n:,} lines in files with {notice}: check they're not the engine's own code)")
    if duplicates[0]:
        out.append(f"  (of which {duplicates[1]:,} lines in {plural(duplicates[0], 'file')} are exact copies of other files"
                   f" counted here: backups, or the same code kept twice? Without them: {own_total - duplicates[1]:,} lines)")
        alerts.append(f"{duplicates[1]:,} lines are copies of other files")
    if untracked[0]:
        out.append(f"  (of which {untracked[1]:,} lines in {plural(untracked[0], 'file')} aren't committed to Git: they're"
                   " only in this copy)")
    if console:
        out.append(f"  (of which {sum(console.values()):,} lines are for consoles ({', '.join(sorted(console))}): usually"
                   " under the platform holder's NDA, which may keep them out of a sale)")
        alerts.append("console code (likely under NDA)")

    # ####################
    # By folder
    # ####################
    if own_lines_by_dir:
        folders = folder_breakdown(own_lines_by_dir)
        out += ["", "Apparently original code by folder (check for copied-in libraries):"]
        for key, lines in folders[:15]:
            out.append(f"  {key:<40} {lines:>11,} lines")
        if len(folders) > 15:
            out.append(f"  ... and {len(folders) - 15} more folders")
    licensed = [(rel.replace(os.sep, "/"), sum(n for d, n in own_lines_by_dir.items()
                                                if d == rel or d.startswith(rel + os.sep)))
                for rel in licensed_dirs]
    licensed = [(rel, n) for rel, n in licensed if n]
    if licensed:
        out += ["", "Folders with their own licence file, counted as original code (check they aren't someone else's;",
                "if one is, run again with --third-party <folder>):"]
        out += [f"  {rel:<40} {n:>11,} lines" for rel, n in sorted(licensed, key=lambda kv: -kv[1])[:10]]

    # ####################
    # Text files of unknown kinds
    # ####################
    unknown = sorted(((ext, n, size) for ext, (n, size) in unknown_text.items() if n >= UNKNOWN_TEXT_MIN_FILES),
                     key=lambda row: -row[2])
    if unknown:
        out += ["", "Text files of kinds this script doesn't count as code. If some are code (a language of the",
                "studio's own, say), run again with --code-ext, e.g. --code-ext .par=PARLANSE:"]
        out += [f"  {ext:<16} {plural(n, 'file'):>14}  {size / 1e6:>10,.1f} MB" for ext, n, size in unknown[:10]]
        alerts.append(f"text files of unknown kinds ({', '.join(ext for ext, _, _ in unknown[:3])}"
                      f"{' ...' if len(unknown) > 3 else ''}): code?")

    # ####################
    # Blueprints and other visual scripting
    # ####################
    if graphs["own"]:
        out += ["", "Blueprints and other visual scripting (graph nodes, not counting comments and reroutes):"]
        for row in GRAPH_ROWS:
            if row in graphs["own"]:
                files, nodes = graphs["own"][row]
                out.append(f"  {row:<52} {plural(files, 'file'):>11}  {plural(nodes, 'node'):>15}")
        out.append(f"  {'TOTAL':<52} {'':>11}  {plural(sum(n for _, n in graphs['own'].values()), 'node'):>15}")
        elsewhere = sum(n for c in ("third-party", "engine") for _, n in graphs[c].values())
        if elsewhere:
            out.append(f"  (plus {elsewhere:,} nodes in third-party plugins/packs or Epic's content, not counted)")
    if coverage:
        read = coverage["read"] + coverage["header"]
        total = read + coverage["cooked"] + coverage["unreadable"]
        out += ["", f"How much of the Unreal assets could be measured: {read:,} of {plural(total, 'file')} read in full"]
        if coverage["cooked"]:
            out.append(f"  {coverage['cooked']:,} cooked (from a packaged game): their graphs were stripped, so no nodes")
        if coverage["unreadable"]:
            out.append(f"  {coverage['unreadable']:,} couldn't be read (an unusual format), "
                       f"{coverage['unreadable, looks like Blueprint']:,} of which seem to hold Blueprint graphs:"
                       " their nodes are missing above")
        if lfs_pointers:
            out.append(f"  {lfs_pointers:,} not downloaded (Git LFS placeholders), so not read at all")
        out.append(f"  {coverage['Blueprints with no nodes']:,} Blueprints read in full have no nodes (data-only"
                   " Blueprints: they set values, without logic)")

    # ####################
    # Databases, and what the code needs
    # ####################
    for section, what in ((dbcode.report, "the databases"), (deps.report, "what the code needs")):
        try:
            out += section()
        except Exception as e:   # a report section shouldn't cost the whole report
            problems.append(f"reporting {what}: {describe(e, root)}")
    if any(compiled for _, compiled, _ in dbcode.access):
        alerts.append("a compiled Access database (its VBA source is gone)")
    if any(got.get("macros_on") for _, _, got in dbcode.access):
        alerts.append("Access databases not opened (Access couldn't switch off their macros)")
    elif any(got.get("how") is None and not got.get("offline") for _, _, got in dbcode.access):
        alerts.append("Access databases not opened (needs Windows with Microsoft Access)")
    if dbcode.server_files and not dbcode.live:
        alerts.append("SQL Server database files or backups whose code isn't counted")
    if dbcode.data:
        alerts.append(f"{plural(sum(dbcode.data.values()), 'file')} of data to keep out of what's shared")

    # ####################
    # UnrealScript compiled into .u packages
    # ####################
    if compiled_script[0]:
        has_source = bool(lines_by["own"].get("UnrealScript") or lines_by["test"].get("UnrealScript"))
        packages, classes, lines = compiled_script
        out += ["", f"UnrealScript compiled into .u packages: {plural(packages, 'package')}, "
                    f"{classes:,} class{'' if classes == 1 else 'es'}, "
                    f"{plural(lines, 'line')} of source inside them",
                "  (the same classes as the .uc files counted above)" if has_source else
                "  (no .uc source files found: this is the only copy of the source, and it isn't counted above)"]

    # ####################
    # Someone else's code, and code that isn't code
    # ####################
    for cat, label in [("third-party", "Someone else's code, not counted above and not the studio's to license "
                                       "(copied-in libraries, Unity Asset Store packages, plugins, engine copies ...)"),
                       ("engine", "Unreal Engine's own code (Epic's, possibly with the studio's changes)"),
                       ("translation", "Translations (Ren'Py game/tl: the game's text in other languages), "
                                       "not counted as code"),
                       ("generated", "Generated or minified code (not counted above)"),
                       ("data", "Data, not code (images, fonts and tables pasted into source files as numbers; the"
                                " INSERT statements that fill a database)")]:
        rows, total = table([lines_by[cat]])
        if total:
            out += ["", f"{label}: {total:,} lines"] + rows
        if cat == "third-party" and "Unity" in kinds_found:
            _, read, found = asset_store_guids()
            out.append(f"  (Unity Asset Store downloads on this computer: {read:,} of {plural(found, 'package')} read"
                       " to recognise their files)" if found else
                       "  (no Unity Asset Store downloads on this computer: Asset Store packages recognised by"
                       " their folders only)")
        if cat == "third-party" and libraries:
            out.append("  By library, package or licence (found by Asset Store download, folder, file name or licence):")
            out += [f"    {lib:<52} {n:>11,} lines" for lib, n in libraries.most_common(12)]
            if len(libraries) > 12:
                out.append(f"    ... and {len(libraries) - 12} more")
    unknown_deps = deps.unknown_libraries()
    if unknown_deps:
        named = [n for n in unknown_deps if n in deps.build]
        folders = len(unknown_deps) - len(named)
        alerts.append("needs code that isn't in this folder: " + (", ".join(named[:3]) + (" ..." if len(named) > 3 else "")
                      + (f" (and {plural(folders, 'folder')} of headers)" if folders else "") if named else
                      f"{plural(folders, 'folder')} of headers"))

    # ####################
    # Notes on what was found
    # ####################
    if binaries:
        out += ["", f"Precompiled libraries (.dll, .lib, .so, .jar ...) with no source here, so not licensable as source:"
                    f" {binaries['own']:,} in the studio's own folders, {binaries['third-party']:,} in third-party ones"]
    if build_files and "Unity" not in kinds_found:
        out += ["", "NOTE: This looks like a built (compiled) Unity game, not the Unity project. A build",
                "      contains no source code to count. Run this on the project folder instead: the one",
                "      that contains Assets and ProjectSettings."]
        if "assembly-csharp.dll" in build_files:
            out.append("      (If the project is lost: this is a Mono build, so the C# can be recovered from "
                       "Assembly-CSharp.dll.)")
        elif build_files & {"gameassembly.dll", "gameassembly.so", "gameassembly.dylib"}:
            out.append("      (This is an IL2CPP build: the C# was compiled to machine code.)")
    if assets["Packaged Unreal game archives"] and "Unreal" not in kinds_found:
        out += ["", "NOTE: This looks like a packaged (shipped) Unreal game, not the Unreal project. It contains",
                "      no source code or Blueprint graphs to count. Run this on the project folder instead:",
                "      the one that contains the .uproject file."]
    if lfs_pointers:
        out += ["", f"NOTE: {lfs_pointers:,} Unreal assets are Git LFS placeholders that were never downloaded, so",
                "      their Blueprints and types couldn't be read. Run \"git lfs pull\" first for a full count."]
    if links:
        out += ["", f"NOTE: Skipped {plural(links, 'link')} to other folders or files (symbolic links or junctions), so",
                "      nothing is counted twice and no code outside this folder is read. If one leads to code that",
                "      lives nowhere else, run this script on that too."]
    if marked:
        out += ["", "Marked by hand: " + ", ".join(
            f"{plural(n, 'path')} as {c} code" for c, n in Counter(marked.values()).items()) + "."]
    if cooked:
        out += ["", f"NOTE: {cooked:,} Unreal assets are cooked (from a packaged game), so their Blueprint graphs",
                "      were stripped and aren't counted."]
    renpy_compiled = assets["Ren'Py compiled scripts"] + assets["Ren'Py archives (.rpa)"]
    if renpy_compiled and not lines_by["own"].get("Ren'Py"):
        out += ["", "NOTE: Found compiled Ren'Py scripts (.rpyc) or archives (.rpa) but no .rpy source files.",
                "      The script source is missing or packed into archives, so it isn't counted above."]
    if secrets:
        out += ["", "NOTE: Possible credentials, to remove before the code is shared (only counted here, never shown):",
                "      " + ", ".join(f"{kind} ({plural(n, 'file')})" for kind, n in secrets.most_common())]
        alerts.append("credentials in the code")
    content = sum(n for kind, n in assets.items() if kind not in ("Scenes/levels", "Jupyter notebooks"))
    if own_total >= 1000 and content < 20 and not graphs["own"]:
        out += ["", f"NOTE: This copy has hardly any art, audio or models ({plural(sum(assets.values()), 'asset file')}):"
                    " it looks like the source", "      code only. Ask whether the full project (with its assets) still exists."]
        alerts.append("source code only, no assets")

    # ####################
    # Assets
    # ####################
    if assets:
        out += ["", "Assets:"] + [f"  {k:<34} {v:>8,}" for k, v in assets.most_common()]

    # ####################
    # Version-control history
    # ####################
    git_h = next((h for h in histories if h["vcs"] == "Git"), None)
    for h in histories:
        out += ["", f"Version control history ({h['vcs']}):"] + history_lines(h)
    combined = None
    try:
        out += sourcesafe_lines(root, vss, git_h, histories, alerts)
    except Exception as e:
        problems.append(f"reading the SourceSafe history: {describe(e, root)}")
    try:   # one folder's histories in more than one system: how they fit together, each change counted once
        lines, combined = across_systems(histories)
        out += lines
    except Exception as e:
        problems.append(f"fitting the histories of the different systems together: {describe(e, root)}")
    if not histories:
        if mtimes and mtimes[1] - mtimes[0] < 86400:
            day = datetime.fromtimestamp(mtimes[0], timezone.utc).strftime("%Y-%m-%d")
            out += ["", f"File dates are all from {day}: that's when these files were copied or unzipped, not when the"
                        " code was written."]
        elif years:
            out += ["", f"Source files last modified: {min(years)}–{max(years)} "
                        "(file dates only; can be reset by copying)"]
        out.append("No version-control history found here, so no commit or pull-request counts.")
        if ARCHIVE_NAME.search(os.path.basename(root)) or (mtimes and mtimes[1] - mtimes[0] < 3600 and
                                                            sum(len(f) for f in deps.files.values()) >= 20):
            out += ["", "NOTE: This looks like a downloaded copy (such as GitHub's \"Download ZIP\") rather than the",
                    "      repository itself, so its history is missing. Run this on a clone (git clone ...) instead."]
            alerts.append("a downloaded copy without its history")

    # ####################
    # Authors, copyright and licence
    # ####################
    named = count_people(named_authors)
    if named:
        out.append(f"People named as authors in the code's comments: {named:,}"
                   + ("" if histories else " (with no version control, the only record of who wrote it;"
                                           " there were probably more)"))
    if copyright_years:
        out.append(f"Years in the code's copyright notices: {min(copyright_years)}–{max(copyright_years)}")
    licence = root_licence(root)
    if licence:
        out.append(f"Licence file at the top of the folder: {licence}")
        if licence not in ("proprietary (all rights reserved)", "a licence of its own"):
            alerts.append(f"licensed to others already ({licence})")
    public = public_repositories(root) if histories else []
    if public:
        out += ["", f"NOTE: Anyone can read this repository at {', '.join(public)}: the code is already public."]
        alerts.append("the repository is public")
    if submodule_list:
        theirs = [name for name, other in submodule_list if other]
        out.append(f"Git submodules: {len(submodule_list)}" + (f", {len(theirs)} of them from other owners and counted as"
                                                              f" someone else's code: {', '.join(theirs[:10])}" if theirs else ""))

    # ####################
    # Custom-built engines
    # ####################
    # A custom-built engine (a fork of Epic's) is often its own repository, outside the project,
    # or a separate repository (a submodule) inside it. Report its history unless the history
    # above already covers it.
    root_top = git_top(root)
    engines, missing = [], False
    for project_dir, association in custom_engines:
        engine = find_custom_engine(project_dir, association)
        if engine is None:
            missing = True
        else:
            engines.append(engine)
    reported = set()
    for engine in engines + engine_sources:
        key = os.path.normcase(os.path.abspath(engine))
        if key in reported:
            continue
        reported.add(key)
        engine_top = git_top(engine)
        if is_within(engine, root) and (engine_top is None or engine_top == root_top):
            continue
        try:
            out += engine_report(engine)
        except Exception as e:
            problems.append(f"reading the engine's history: {describe(e, root)}")

    # ####################
    # Repositories inside the scanned folder
    # ####################
    # Say, Game/ and Tools/ side by side, or a submodule.
    shown = 0
    for rel, path in nested_repos:
        key = os.path.normcase(os.path.abspath(path))
        if key in reported or (git_top(path) or key) == root_top:
            continue
        reported.add(key)
        shown += 1
        if shown > 10:
            continue
        try:
            vcs, nested = version_control(path)
        except Exception as e:
            problems.append(f"reading the history of {rel}: {describe(e, root)}")
            continue
        out += ["", f"Repository inside this folder: {rel.replace(os.sep, '/')} ({', '.join(vcs) or 'unreadable'})"]
        for h in nested:
            out += [f"  History ({h['vcs']}):"] + history_lines(h, "  ")
            histories.append(h)
        try:
            out += ["  " + line if line else line for line in across_systems(nested)[0][1:]]
        except Exception as e:
            problems.append(f"fitting the histories of {rel} together: {describe(e, root)}")
    if shown > 10:
        out.append(f"(and {shown - 10} more repositories inside this folder, not listed)")

    # ####################
    # Caveats about the history
    # ####################
    if histories or any("History (" in line for line in out):
        out += [""] + HISTORY_CAVEATS
    if _git_other_owners:
        n = len(_git_other_owners)
        which = "this repository: it belongs" if n == 1 else f"{n} of these repositories: they belong"
        out += ["", f"NOTE: Git at first refused to read {which} to another user account on this computer",
                "      (Git's \"dubious ownership\" check; usual for external drives and copied folders). Read anyway,",
                "      for this scan only, with the repository's own settings that could start programs switched off.",
                "      Git's own settings weren't changed."]
    if missing:
        out += ["", "NOTE: This project is built with a custom Unreal Engine that isn't registered on this computer,",
                "      so the engine's own history and changes aren't included. Run this script on the engine's",
                "      folder too (the one that contains Engine/)."]

    # ####################
    # Test coverage
    # ####################
    coverage_summary = coverage_facts = None
    try:
        section, coverage_summary, coverage_facts = test_coverage.report(kinds_found)
        out += section
    except Exception as e:   # a report section shouldn't cost the whole report
        problems.append(f"reporting the test coverage: {describe(e, root)}")

    # ####################
    # Standard measures
    # ####################
    standard_facts = None
    try:
        # The apparently original code's lines by language, as forms name them; and the part of
        # them that wasn't read from source files (but from databases), which scc can't see.
        own_by_lang, own_languages, database_languages = Counter(), Counter(c_family), Counter()
        for c in ("own", "test"):
            for lang, (_, n) in lines_by[c].items():
                own_by_lang[lang] += n
        for lang, n in own_by_lang.items():
            if lang != "C/C++":
                own_languages[form_language(lang)] += n
            if n > source_lines[lang]:
                database_languages[form_language(lang)] += n - source_lines[lang]
        kept = [os.path.relpath(p, root).replace(os.sep, "/") for p, c in marked.items() if c == "own"]
        left_out = left_out_paths(root, not_own_folders, not_own_files, kept)
        if only:
            tools, not_measured, tool_reports = {}, {t: "not run on a single file" for t in TOOL_FIGURES}, {}
        else:
            tools, not_measured, tool_reports = tool_measures(root, left_out, unrecognised)
        not_measured = {tool: scrub(why, root) for tool, why in not_measured.items()}
        section, standard_facts = standard_measures_report(histories, vcs_found, tools, not_measured, left_out,
                                                           own_languages, database_languages)
        out += section
        if not_measured and not only:
            alerts.append(" and ".join(TOOL_FIGURES[t].split(" (")[0] for t in not_measured)
                          + " not included (" + " and ".join(not_measured) + " couldn't be used)")
        if tool_reports and facts is not None:
            facts["tool_reports"] = tool_reports
    except Exception as e:   # a report section shouldn't cost the whole report
        problems.append(f"reporting the standard measures: {describe(e, root)}")

    # ####################
    # What --offline left out
    # ####################
    if OFFLINE:
        out += ["", "Run with --offline: this computer connected to no other one (no downloads, no version-control or",
                "database servers, no network shares besides the folder scanned)."]
        if _left_out_offline:
            out.append("Left out because of that:")
            out += [f"  - {what}" for what in _left_out_offline]
            alerts.append("run with --offline, so some figures are left out (see near the end)")
        else:
            out.append("Nothing was left out because of that.")

    # ####################
    # Problems
    # ####################
    if problems:
        out += ["", "Problems while scanning (the rest of the report is fine; please pass these on to Jimmy):"]
        out += [f"  {p}" for p in problems]

    # ##############################
    # The headline numbers, at the top
    # ##############################
    langs = sorted(((lang, n) for b in (lines_by["own"], lines_by["test"]) for lang, (_, n) in b.items()),
                   key=lambda kv: -kv[1])
    merged = Counter()
    for lang, n in langs:
        merged[lang] += n
    summary = ["Summary:", f"  Apparently original code: {plural(own_total, 'line')}"
               + (f" ({', '.join(f'{lang} {n:,}' for lang, n in merged.most_common(3))})" if merged else "")]
    nodes = sum(n for _, n in graphs["own"].values())
    if nodes:
        summary.append(f"  Blueprints and other visual scripting: {nodes:,} nodes")
    if histories:
        main = next((h for h in histories if not h.get("held_by")), histories[0])   # not one wholly in another
        rows, reviews = dict(main["rows"]), main["reviews"]
        unit = next(k for k, _ in main["rows"] if not k.startswith(" ") and "Epic" not in k)
        prs = max([v for k, v in reviews if isinstance(v, int) and "pull request" in k] or [0])
        people = rows["contributors"]
        count = rows[unit]
        unit_word = re.sub(r"s\b", "", unit, count=1) if count == 1 else unit   # "1 commit", "1 submitted changelist"
        summary.append(f"  History ({main['vcs']}): {fmt(count)} {unit_word} by {people:,}"
                       f" {'person' if people == 1 else 'people'}, {rows['first change']} to {rows['last change']};"
                       f" {plural(prs, 'pull request')} found")
    else:
        summary.append("  History: none found")
    people_all = contributors_across(histories)
    if len(histories) > 1:
        summary.append(f"  Contributors, all {len(histories)} histories together: {people_all:,}"
                       f" {'person' if people_all == 1 else 'people'} (each counted once)")
    elif not histories and named:
        summary.append(f"  Contributors: {named:,} named as authors in the code's comments"
                       " (no version control, so probably more)")
    if combined:
        n, first, last, how = combined
        summary.append(f"  History, all systems together: {n:,} changes, {first} to {last} ({how})")
    if coverage_summary:
        summary.append(coverage_summary)
    if alerts:
        summary.append("  Check: " + "; ".join(alerts))
    out[2:2] = summary + [""]

    # ##############################
    # The numbers, for the machine-readable copy
    # ##############################
    if facts is not None:
        facts.update({
            "script_version": __version__, "offline": OFFLINE, "left_out_offline": list(_left_out_offline),
            "git_repositories_of_other_users": len(_git_other_owners),
            "project": os.path.basename(root), "project_types": [[k, r.replace(os.sep, "/"), d] for k, r, d in projects],
            "lines": {c: {lang: {"files": f, "lines": n} for lang, (f, n) in lines_by[c].items()} for c in categories},
            "own_total": own_total, "duplicate_lines": duplicates[1], "untracked_lines": untracked[1],
            "console_lines": dict(console), "third_party_by_library": dict(libraries),
            "folders": [[k, n] for k, n in folder_breakdown(own_lines_by_dir)] if own_lines_by_dir else [],
            "visual_scripting": {row: {"files": f, "nodes": n} for row, (f, n) in graphs["own"].items()},
            "unreal_coverage": dict(coverage), "unreal_versions": dict(unreal_versions), "assets": dict(assets),
            "version_control": vcs_found,
            "histories": [{"vcs": h["vcs"], "rows": dict(h["rows"]), "reviews": dict(h["reviews"]),
                           "notes": h.get("notes", []), "changes_counted_in_another_history": len(h.get("counted_elsewhere", ())),
                           "held_by": h.get("held_by")} for h in histories],
            "history_across_systems": dict(zip(("changes", "first", "last", "how"), combined)) if combined else None,
            "contributors": {"version_control": people_all if histories else None, "named_in_code": named},
            "dependencies_not_here": {"unknown": unknown_deps, "packages": {k: sorted(v) for k, v in deps.packages.items()},
                                      "missing_includes": dict(deps.missing_includes())},
            "precompiled_libraries": dict(binaries), "credentials": dict(secrets),
            "copyright_years": [min(copyright_years), max(copyright_years)] if copyright_years else None,
            "licence": licence, "public_repositories": public, "submodules": submodule_list,
            "alerts": alerts, "problems": problems, "standard_measures": standard_facts,
            "test_coverage": coverage_facts,
            "unknown_text_files": {ext: {"files": n, "bytes": size} for ext, n, size in unknown},
            "code_extensions_named": {ext: name for ext, (name, _) in EXTRA_CODE.items()},
            "databases": {"access": [{"format": f, "compiled": c, **{k: v for k, v in g.items() if k not in ("queries", "vba")},
                                      "queries": len(g.get("queries", [])), "vba_modules": len(g.get("vba", []))}
                                     for f, c, g in dbcode.access],
                          "access_exports": dict(dbcode.access_exports), "sql_files": dict(dbcode.sql_files),
                          "packages": dict(dbcode.dac), "ssis": dict(dbcode.ssis), "ssrs": dict(dbcode.ssrs),
                          "server_files": dict(dbcode.server_files),
                          "sql_server": {k: (dict(v) if isinstance(v, Counter) else v) for k, v in (dbcode.live or {}).items()
                                         if k != "code"}},
        })
    return "\n".join(out)


# #######################################
# Command line
# #######################################

def dropped_path(text):
    """The folder a user dragged into the terminal (or pasted). Windows wraps paths with spaces in
    "quotes"; macOS Terminal escapes them (My\\ Game); Linux terminals use 'quotes' or file:// URLs."""
    text = text.strip()
    if text.startswith("file://"):
        from urllib.parse import unquote, urlparse
        text = unquote(urlparse(text).path)
        if os.name == "nt" and re.match(r"^/[A-Za-z]:", text):
            text = text[1:]
    if os.name != "nt" and not os.path.isdir(text):
        import shlex
        try:
            words = shlex.split(text)
        except ValueError:
            words = []
        if len(words) == 1:
            return words[0]
    return text.strip("'\"")


TOOL_REPORT_NAMES = {"scc": "scc", "jscpd": "jscpd-summary"}   # size_report_<name>_<this>.json


def save_report(report, name, here, facts=None):
    """Saves next to this script or, if that folder is read-only, in the current or home folder. The
    numbers go in a .json beside it too, for reading by machine, and scc's report and jscpd's
    totals (facts["tool_reports"], with --reports) beside that."""
    tool_reports = (facts or {}).pop("tool_reports", {})
    for folder in (here, os.getcwd(), os.path.expanduser("~")):
        out_path = os.path.join(folder, f"size_report_{name}.txt")
        try:
            write_report_file(out_path, report + "\n")
            if facts is not None:
                write_report_file(os.path.join(folder, f"size_report_{name}.json"),
                                  json.dumps(facts, indent=1, default=sorted))
            for tool, text in tool_reports.items():
                if text:
                    write_report_file(os.path.join(folder, f"size_report_{name}_{TOOL_REPORT_NAMES[tool]}.json"), text)
            return out_path
        except OSError:
            continue
    return None


def write_report_file(path, text):
    """Writes one of the report's files. A link already in its place (one a project put beside this
    script, say, pointing at some other file) is removed, not written through."""
    if os.path.islink(path):
        os.remove(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def scan(root, here, third_party=(), own=(), sql_servers=(), sourcesafe=()):
    root = dropped_path(root)
    only = None
    if os.path.isfile(root):   # a single file, e.g. an Access database: just that file, from its folder
        root, only = os.path.split(os.path.abspath(root))
    elif not os.path.isdir(root):
        print(f"Not a folder or file: {root}")
        return
    print(f"Scanning {os.path.join(root, only) if only else root} ... (large projects can take a few minutes)")
    facts = {}
    report = size_project(root, third_party, own, facts, sql_servers, only, sourcesafe)
    print("\n" + report + "\n")
    name = "".join(c if c.isalnum() else "_" for c in only or os.path.basename(os.path.abspath(root)))
    out_path = save_report(report, name, here, facts)
    print(f"Saved: {out_path}\n" if out_path else "Couldn't save the report: please copy it from above.\n")
    if out_path and KEEP_TOOL_REPORTS:
        print("Also saved beside it: scc's report and jscpd's totals (_scc.json, _jscpd-summary.json), for attaching\n"
              "to a form. Both hold counts only.\n")


def usage():
    """The part of this script's description that says how to run it."""
    return __doc__[__doc__.index("Usage"):].strip()


def stop(message):
    print(message)
    sys.exit(2)


def main():
    for stream in (sys.stdout, sys.stderr):   # never crash printing an unusual folder name
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    # ####################
    # Options
    # ####################
    here = os.path.dirname(os.path.abspath(__file__))
    global FETCH_TOOLS, KEEP_TOOL_REPORTS, OFFLINE, TRUST_SERVER_CERTIFICATE, NETWORK_SOURCESAFE
    roots, args = [], sys.argv[1:]
    marks = {"--third-party": [], "--own": [], "--sql-server": [], "--sql-database": [], "--sourcesafe": [],
             "--code-ext": []}
    while args:
        arg = args.pop(0)
        if arg in ("-h", "--help"):
            print(f"size_codebase.py {__version__}\n\n{usage()}")
            sys.exit(0)
        elif arg == "--no-download":
            FETCH_TOOLS = False
        elif arg == "--offline":
            OFFLINE = True
        elif arg == "--reports":
            KEEP_TOOL_REPORTS = True
        elif arg == "--trust-server-certificate":
            TRUST_SERVER_CERTIFICATE = True
        elif arg == "--network-sourcesafe":
            NETWORK_SOURCESAFE = True
        elif arg in marks:
            if not args:
                stop(f"{arg} needs a value after it. For help: python3 size_codebase.py --help")
            marks[arg].append(args.pop(0))
        elif arg.startswith("--"):
            stop(f"Unknown option: {arg}. For help: python3 size_codebase.py --help")
        else:
            roots.append(arg)
    sql_servers = [(server, marks["--sql-database"]) for server in marks["--sql-server"]]
    for spec in marks["--code-ext"]:
        try:
            add_code_extension(spec)
        except ValueError as e:
            stop(str(e))

    # ####################
    # Options that contradict --offline
    # ####################
    if OFFLINE and sql_servers:
        stop("--sql-server reads a database server over the network, and --offline says not to connect to any other"
             " computer. Leave out one of the two.")
    if OFFLINE and any(is_network_path(db) for db in marks["--sourcesafe"]):
        stop("--sourcesafe names a folder on a network share, and --offline says not to connect to any other"
             " computer. Leave out one of the two, or name a copy of the database on this computer.")
    if OFFLINE and NETWORK_SOURCESAFE:
        stop("--network-sourcesafe opens SourceSafe databases on network shares, and --offline says not to connect"
             " to any other computer. Leave out one of the two.")
    remove_old_temp_folders()

    # ####################
    # Folders named on the command line
    # ####################
    if roots:
        for root in roots:
            scan(root, here, marks["--third-party"], marks["--own"], sql_servers, marks["--sourcesafe"])
        return

    # ####################
    # Started without arguments
    # ####################
    # E.g. double-clicked on Windows: ask for folders, and keep the window open at the end.
    try:
        prompt = "Drag a project folder (or an Access database) into this window, or paste its path, then press Enter: "
        while True:
            root = input(prompt).strip()
            if not root:
                break
            scan(root, here)
            prompt = "Drag in another folder, or just press Enter to finish: "
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nSomething went wrong. Please send a screenshot of this window to whoever sent you this script.")
    input("Done. Press Enter to close this window.")


if __name__ == "__main__":
    main()
