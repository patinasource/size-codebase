#!/usr/bin/env python3
"""
size_codebase.py — size up a codebase. Understands Unity, Unreal (every version from
Unreal Engine 1 to 5: C++, Blueprints, UnrealScript, Kismet, AngelScript, Verse ...),
Ren'Py, Python and JavaScript/TypeScript projects out of the box, and counts most other
languages too, and systems built with Microsoft Access and SQL Server (forms, reports, queries, VBA,
stored procedures, SSIS and SSRS). Counts commits, contributors and pull requests from Git, Perforce,
SVN, Mercurial, Plastic SCM (Unity Version Control), Team Foundation (TFVC), Bazaar, Fossil, Darcs, CVS
and Visual SourceSafe; without version control, counts the people named as authors in the code.

Usage (Windows, macOS or Linux):
    python3 size_codebase.py "/path/to/project"  ["/path/to/other" ...]
    python3 size_codebase.py            (asks for the folder; drag it into the window)
    python3 size_codebase.py "/path/to/Program.mdb"     (a single file, e.g. an Access database)
On Windows, "py" instead of "python3" also works, and so does double-clicking the script.

If it gets a folder wrong, say so (paths relative to the project folder, or absolute; repeatable):
    python3 size_codebase.py "/path/to/project" --third-party Source/Game/SomeLib --own Plugins/MyPlugin

Code in a language it doesn't know (one of the studio's own, say) is listed as text files of unknown
kinds. Name each extension, optionally with a known language whose comments it shares (text, the
default, counts every non-blank line; or C, Ada, SQL, Lisp, Python, Pascal); repeatable:
    python3 size_codebase.py "/path/to/project" --code-ext .par=PARLANSE --code-ext ".atg=DMS grammar:Ada"

Visual SourceSafe: its history is read straight from the SourceSafe database (the folder with
srcsafe.ini and a data folder), found inside the project, through the SSDIR setting, or where the
project files say it is. If it's somewhere else, name it; its history is then put together with the
Git history, without counting work that is in both twice:
    py size_codebase.py "C:\\path\\to\\project" --sourcesafe "D:\\OldVSS"
SourceSafe has no server program: its database is just a folder of files, so a copy of it (from a
backup or an old disk) works as well as the original, as does its data folder on its own.

Microsoft Access and SQL Server: Access databases (.accdb, .mdb ...) are read in full on Windows
with Microsoft Access installed (on a copy, with their macros and code switched off), and without
their VBA through mdbtools elsewhere. Code that lives only inside a SQL Server database is read
from the running server, through sqlcmd, with your Windows sign-in (or set SQLCMDUSER and
SQLCMDPASSWORD):
    py size_codebase.py "C:\\path\\to\\project" --sql-server MYSERVER\\SQLEXPRESS [--sql-database Sales]

It only READS files. It prints a summary and saves it next to this script as
size_report_<folder>.txt. The report contains counts and folder names only: no source
code, no file names, no author names. Nothing is uploaded anywhere. From databases it reads
only code (stored procedures, queries, VBA ...) and the list of objects: never the rows in
a table, so no customer data. To count
pull requests and changelists it may ask your own version-control server (GitHub, GitLab,
Perforce ...) for them, read-only, with the access you already have.

The report ends with the standard measures buyers' codebase forms ask for: logical lines of code
and generated lines (scc), duplication (jscpd), commits on the main branch without merges or
reverts, and the primary language. scc and jscpd are fetched for this, once, from their official
releases (GitHub, npmjs.org) and checked against fixed checksums; nothing needs installing, and
they're kept in a cache folder (on Windows %LOCALAPPDATA%\\size_codebase_tools). Without them
(offline, or with --no-download) the script estimates their figures itself. To also save their own
reports beside this one, for attaching to a form:
    python3 size_codebase.py "/path/to/project" --reports
(jscpd's report holds copies of the duplicated code: look it over before sending it.)

Needs Python 3.8+ and nothing else (https://www.python.org/downloads/).
"""
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone


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
    for _ in range(levels):
        if os.path.exists(os.path.join(path, name)):
            return True
        path = os.path.dirname(path)
    return False


def is_lfs_pointer(path):
    """A Git LFS placeholder: the real file is on the server, not downloaded."""
    try:
        with open(path, "rb") as f:
            return f.read(40).startswith(b"version https://git-lfs")
    except OSError:
        return False


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
           r"C:\Program Files\Unity Version Control\client\cm.exe"],
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


def tool_path(name):
    """Where a command-line tool is installed. On Windows, tools that came with GitHub Desktop,
    TortoiseSVN, P4V, Visual Studio and the like often aren't on PATH."""
    found = shutil.which(name)
    if found or os.name != "nt":
        return found
    import glob
    for pattern in WINDOWS_TOOL_PATHS.get(name, []):
        matches = sorted(glob.glob(os.path.expandvars(pattern)), reverse=True)   # newest version first
        if matches:
            return matches[0]
    return None


def command(args):
    """args with the tool's full path. Git is told to trust any repository: it otherwise refuses
    ones on drives owned by another user account (external drives, exFAT, copied folders)."""
    exe = tool_path(args[0])
    if exe is None:
        return None
    return [exe, "-c", "safe.directory=*", *args[1:]] if args[0] == "git" else [exe, *args[1:]]


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
    plain, UTF-8 output whatever the user's settings."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", HGPLAIN="1", HGENCODING="utf-8",
               PYTHONIOENCODING="utf-8")
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    return env


def run(args, cwd, timeout=900):
    """stdout of a command, or None if it isn't installed, fails or takes too long."""
    args = command(args)
    if args is None:
        return None
    env = quiet_env()
    env["PWD"] = os.path.abspath(cwd)   # p4 finds its settings (P4CONFIG) from $PWD, not the real folder
    try:
        out = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, env=env,
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
    ".git", ".svn", ".hg", ".bzr", ".plastic", ".vs", ".idea", ".vscode",
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
    return folders


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
# Logical lines
# ##############################

# ####################
# Comment syntax by language
# ####################

# How each language writes comments, to count logical lines (lines with code on them: not blank and
# not only a comment) the way scc does. Strings are matched too, as "keep", so that a // or # inside
# one isn't taken for a comment.
def comment_syntax(comments, strings=(rb'"(?:\\.|[^"\\\n])*"', rb"'(?:\\.|[^'\\\n])*'"), first=()):
    """first: comments that win over strings starting at the same place (Python's docstrings)."""
    keep = b"(?P<keep>" + b"|".join(strings) + b")" if strings else b"(?P<keep>(?!))"
    return re.compile(b"|".join([*first, keep, *comments]), re.S | re.M)


SLASHES, STARS = rb"//[^\n]*", rb"/\*.*?(?:\*/|\Z)"
HASH, DASHES, SEMICOLON = rb"#[^\n]*", rb"--[^\n]*", rb";[^\n]*"
DQ, SQ = rb'"(?:\\.|[^"\\\n])*"', rb"'(?:\\.|[^'\\\n])*'"
SQL_SQ, VB_DQ = rb"'(?:[^'\n]|'')*'", rb'"(?:[^"\n]|"")*"'
TRIPLE_QUOTED = rb'(?:"""(?:\\.|[^\\])*?(?:"""|\Z)|\'\'\'(?:\\.|[^\\])*?(?:\'\'\'|\Z))'
BACKTICKS = rb"`(?:\\.|[^`\\])*`"
CPP_RAW = rb'R"(?P<delimiter>[^()\\\s"]{0,16})\(.*?\)(?P=delimiter)"'
C_COMMENTS = comment_syntax([SLASHES, STARS], [CPP_RAW, DQ, SQ, BACKTICKS])
HASH_COMMENTS = comment_syntax([HASH])
COMMENT_SYNTAX = {
    **dict.fromkeys(
        [".c", ".cc", ".cpp", ".cxx", ".c++", ".cppm", ".ixx", ".ipp", ".tcc", ".h", ".hh", ".hpp", ".hxx", ".h++",
         ".inl", ".cu", ".cuh", ".m", ".mm", ".java", ".kt", ".scala", ".swift", ".go", ".rs", ".dart",
         ".groovy", ".gradle", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".as", ".hx", ".gml",
         ".uc", ".uci", ".sk", ".zig", ".agc", ".ink", ".yarn", ".css", ".scss", ".sass", ".less", ".pli", ".pl1",
         ".sv", ".svh", ".vh", ".rpgle", ".sqlrpgle", ".shader", ".cginc", ".hlsl", ".glsl", ".compute", ".usf",
         ".ush", ".fx", ".fxh", ".cg", ".vert", ".frag", ".geom", ".tesc", ".tese", ".vsh", ".psh", ".metal",
         ".wgsl", ".slang", ".gdshader", ".gdshaderinc", ".glslinc", ".fs", ".fsx"], C_COMMENTS),
    ".cs": comment_syntax([SLASHES, STARS], [rb'\$?@\$?"(?:[^"]|"")*"', rb'\$*"""+.*?"""+', DQ, SQ]),   # @"verbatim", """raw"""
    **dict.fromkeys([".sh", ".bash", ".rb", ".pl", ".gd", ".rpy", ".rpym", ".cmake", ".ex", ".exs", ".tcl", ".verse",
                     ".coffee", ".nim"], HASH_COMMENTS),
    **dict.fromkeys([".py", ".pyi", ".pyx"], comment_syntax(
        [HASH], [rb"[rRuUbBfF]{0,2}" + TRIPLE_QUOTED, DQ, SQ], first=[rb"^[ \t]*[rRuU]?" + TRIPLE_QUOTED])),
    **dict.fromkeys([".php", ".nut"], comment_syntax([SLASHES, STARS, HASH])),
    ".ps1": comment_syntax([rb"<#.*?(?:#>|\Z)", HASH]),
    **dict.fromkeys([".lua", ".luau", ".moon"], comment_syntax(
        [rb"--\[(?P<level>=*)\[.*?(?:\](?P=level)\]|\Z)", DASHES], [DQ, SQ, rb"\[\[.*?(?:\]\]|\Z)"])),
    **dict.fromkeys([".sql", ".tsql", ".pks", ".pkb", ".prc", ".fnc"], comment_syntax([DASHES, STARS], [SQL_SQ])),
    **dict.fromkeys([".adb", ".ads", ".vhd", ".vhdl"], comment_syntax([DASHES], [DQ])),
    ".hs": comment_syntax([DASHES, rb"\{-.*?(?:-\}|\Z)"], [DQ]),
    **dict.fromkeys([".vb", ".bas", ".cls", ".frm", ".ctl", ".dsr", ".pag", ".dob", ".vbs", ".monkey", ".monkey2"],
                    comment_syntax([rb"'[^\n]*", rb"(?i:^[ \t]*rem\b[^\n]*)"], [VB_DQ])),
    ".bmx": comment_syntax([rb"'[^\n]*", rb"(?i:^[ \t]*rem\b.*?(?:^[ \t]*end[ \t]?rem\b[^\n]*|\Z))"], [VB_DQ]),
    **dict.fromkeys([".bat", ".cmd"], comment_syntax([rb"(?i:^[ \t]*(?:@?rem\b|::)[^\n]*)"], [])),
    **dict.fromkeys([".asm", ".clj", ".bb", ".nani"], comment_syntax([SEMICOLON])),
    ".erl": comment_syntax([rb"%[^\n]*"]),
    **dict.fromkeys([".html", ".htm"], comment_syntax([rb"<!--.*?(?:-->|\Z)"], [])),
    **dict.fromkeys([".vue", ".svelte"], comment_syntax([rb"<!--.*?(?:-->|\Z)", SLASHES, STARS], [DQ, SQ])),
    **dict.fromkeys([".pas", ".dpr"], comment_syntax([SLASHES, rb"\{(?!\$).*?(?:\}|\Z)", rb"\(\*.*?(?:\*\)|\Z)"],
                                                     [SQL_SQ])),
    ".ml": comment_syntax([rb"\(\*.*?(?:\*\)|\Z)"], [DQ]),
    # COBOL: a * or / in column 7 (fixed format), or *> anywhere. Fortran: !, or C or * in column 1
    # (fixed form). ABAP: * in column 1, or ". JCL: //* .
    **dict.fromkeys([".cbl", ".cob", ".cpy"], comment_syntax([rb"^[^\n]{6}[*/][^\n]*", rb"\*>[^\n]*"])),
    **dict.fromkeys([".f", ".for", ".f77"], comment_syntax([rb"![^\n]*", rb"^[cC*][^\n]*"])),
    **dict.fromkeys([".f90", ".f95", ".f03", ".f08"], comment_syntax([rb"![^\n]*"])),
    ".abap": comment_syntax([rb"^\*[^\n]*", rb'"[^\n]*'], [SQ, rb"`[^`\n]*`", rb"\|[^|\n]*\|"]),
    ".jcl": comment_syntax([rb"^//\*[^\n]*"], []),
}


def _drop_comment(m):
    """A comment becomes blank lines; a string stays, its blank lines marked with a NUL so that they
    count as code, as scc counts them."""
    text = m.group(0)
    return text.replace(b"\n", b"\n\0") if m.lastgroup == "keep" else b"\n" * text.count(b"\n")


def code_lines(text, ext):
    """A file's logical lines (see COMMENT_SYNTAX), stripped. Languages whose comments aren't known
    here count every non-blank line."""
    syntax = COMMENT_SYNTAX.get(ext)
    if syntax is not None:
        text = syntax.sub(_drop_comment, text)
    return [line.strip() for line in text.splitlines() if line.strip()]


# ####################
# Languages named with --code-ext
# ####################
# Languages this script doesn't know, named with --code-ext (".par=PARLANSE", ".atg=DMS grammar:Ada"):
# extension -> (name, the known language whose comments it shares). Every non-blank line of "text"
# counts. For each known language: a file extension with its comments here, scc's name, jscpd's.
EXTRA_CODE = {}
LIKE_LANGUAGES = {"text": (None, "Plain Text", "txt"), "C": (".c", "C", "c"), "Ada": (".adb", "Ada", "ada"),
                  "SQL": (".sql", "SQL", "sql"), "Lisp": (".clj", "Lisp", "lisp"), "Python": (".py", "Python", "python"),
                  "Pascal": (".pas", "Pascal", "pascal")}


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
    sample = LIKE_LANGUAGES[like][0]
    if sample:
        COMMENT_SYNTAX[ext] = COMMENT_SYNTAX[sample]
    else:
        COMMENT_SYNTAX.pop(ext, None)


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
    """What's in one source file, as a dict: lines (non-blank), code (its logical lines, stripped:
    see code_lines), generated, licence (the library or licence its header names, or EPIC_NOTICE,
    or None), data (mostly an embedded data array, not code), includes (#include paths, C-family
    only), years (in copyright notices), authors (people named as authors in comments, see
    authors_in), secrets (kinds of credentials found) and digest (to spot the same file in several
    places)."""
    facts = {"lines": 0, "code": [], "generated": False, "licence": None, "data": False, "includes": [], "years": [],
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
    facts["code"] = code_lines(text, ext)
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
# History brought into Git from another system, one marker per original change.
IMPORTED_HISTORY = {
    "Perforce changelists imported (git-p4)": re.compile(r"\[git-p4: depot-paths = .*?: change = (\d+)\]"),
    "SVN revisions imported (git-svn)": re.compile(r"^git-svn-id: (\S+)", re.M),
    "TFS changesets imported (git-tfs)": re.compile(r"^git-tfs-id: (.+)$", re.M),
}


class MessageScan:
    """Pull requests, code reviews and imported history named in commit messages."""

    def __init__(self):
        self.prs, self.reviews, self.imported = defaultdict(set), defaultdict(set), defaultdict(set)
        self.reverts = self.merges = 0   # changes whose first line says so (forms leave both out)

    def add(self, message):
        subject = message.strip().split("\n", 1)[0]
        self.reverts += bool(re.search("revert", subject, re.I))
        self.merges += bool(re.match(r"merg(e|ed|ing)\b", subject, re.I))
        self.prs["#"].update(PR_IN_SUBJECT.findall(subject))
        for numbering, pattern in PR_IN_MESSAGE:
            self.prs[numbering].update(pattern.findall(message))
        for label, pattern in REVIEWS_IN_MESSAGE.items():
            self.reviews[label].update(pattern.findall(message))
        for label, pattern in IMPORTED_HISTORY.items():
            self.imported[label].update(pattern.findall(message))

    def reviews_found(self):
        return ([("merged pull requests named in commit messages", sum(len(s) for s in self.prs.values()))]
                + [(label, len(s)) for label, s in self.reviews.items()])

    def imports_found(self):
        return [(label, len(s)) for label, s in self.imported.items() if s]


# ##############################
# Summing up a history
# ##############################

def history(vcs, unit, changes, merges=None, reviews=(), notes=(), scan=None):
    """A version-control history for the report. changes: [(date "YYYY-MM-DD" or year, author)], the
    author being a tuple of identities (see count_people) or a plain name. scan: the MessageScan of
    their messages, for the changes forms count (without merges or reverts; a system that doesn't
    record merges has the ones its messages name left out)."""
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
    return {"vcs": vcs, "rows": rows, "reviews": [(label, n) for label, n in reviews if n], "notes": list(notes),
            "per_year": dict(sorted(per_year.items())), "dates": dates, "authors": sorted(set(authors)),
            "standard_commits": standard}


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
    changes, merges, epic_commits, main_commits, vss_messages = [], 0, 0, 0, 0
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
        scan.add(body)
        vss_messages += bool(VSS_IN_MESSAGE.search(body))
    progress()
    if not changes and not epic_commits:
        return None

    # ####################
    # Pull requests and code reviews
    # ####################
    found = scan.reviews_found()
    unreachable = []
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
    h = history("Git", "commits by the studio (not Epic's)" if epic_commits else "commits", changes, merges, found,
                notes)
    standard = git_standard_commits(root, [] if whole_repo else ["--", "."])
    h["standard_commits"], h["standard_branch"] = standard or (None, None)
    h["rows"].insert(1, ("  of which on the main branch (the one checked out)", main_commits))
    h["rows"] += scan.imports_found()
    h["vss_messages"] = vss_messages

    # ####################
    # History from elsewhere: earlier systems, Epic's engine
    # ####################
    pre_git = sum(1 for d in h["dates"] if d < GIT_RELEASED)
    if pre_git:
        h["rows"].append(("dated before Git existed (April 2005): converted from an earlier system", pre_git))
    if epic_commits:
        h["rows"].insert(0, ("commits from Epic (Unreal Engine's own history)", epic_commits))
        h["rows"] += changes_to_epic_code(root, [] if whole_repo else ["--", "."])
    elif is_engine_repository(root) or is_engine_repository(top or root):
        h["rows"] += engine_changes_without_epic_history(root, [] if whole_repo else ["--", "."])
    return h


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
    out = run(["git", "log", "--no-merges", "--format=%x1e", "--shortstat", branch, *(pathspec or ["--"])], root, 3600)
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
    stat = run(["git", "diff", "--shortstat", sha.strip(), branch, *(pathspec or ["--"])], root) or ""
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


def git_server_pull_requests(root, unreachable=None):
    """[(remote, number of pull requests)]. GitHub, GitLab and Bitbucket Server keep a ref for every
    pull request ever opened (refs/pull/N/..., refs/merge-requests/N/..., refs/pull-requests/N/...).
    Remotes that can't be reached (say, they need a login we don't have) are added to `unreachable`."""
    found = []
    for remote, _ in git_remotes(root):
        progress(f"Asking {remote} for its pull requests ...")
        refs = run(["git", "ls-remote", remote, "refs/pull/*", "refs/merge-requests/*", "refs/pull-requests/*"],
                   root, 180)
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
    for remote, url in git_remotes(root):
        m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", url)
        if not m:
            continue
        out = run(["gh", "api", "-X", "GET", "search/issues", "-f", f"q=repo:{m.group(1)}/{m.group(2)} is:pr is:merged",
                   "--jq", ".total_count"], root, 60)
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
    """(commits, branch): forms' "git log --oneline --no-merges | grep -v -i revert | wc -l" on the
    main branch, leaving out Epic's own commits in a fork of Unreal Engine. None if git fails."""
    ref = git_default_branch(root)
    out = run(["git", "log", "--no-merges", "--invert-grep", "-E", "--grep", EPIC_GREP, "--format=%ae%x1f%s", ref,
               *(pathspec or ["--"])], root, 3600)
    if out is None:
        return None
    count = sum(1 for line in out.splitlines() if "\x1f" in line and not EPIC_EMAIL.search(line.split("\x1f")[0])
                and not re.search("revert", line.split("\x1f", 1)[1], re.I))
    if ref == "HEAD":   # no main branch: the one checked out
        return count, (run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root, 60) or "HEAD").strip()
    return count, re.sub(r"^refs/(heads|remotes)/", "", ref)


# ##############################
# Other version-control systems
# ##############################

def perforce_history(root):
    """Submitted changelists under this folder, if it's in a Perforce workspace and p4 is logged in."""
    path = os.path.join(root, "...")
    if not (run(["p4", "changes", "-m", "1", "-s", "submitted", path], root, 20) or "").startswith("Change "):
        return None
    out = run(["p4", "changes", "-l", "-s", "submitted", path], root) or ""
    changes, scan = [], MessageScan()
    # "Change 123 on 2020/01/02 by jane@workspace", then the full description, indented.
    for block in re.split(r"^(?=Change \d+ on )", out, flags=re.M):
        m = re.match(r"Change \d+ on (\d{4}/\d\d/\d\d) by ([^@\s]+)@\S*(.*)", block, re.S)
        if m:
            changes.append((m.group(1).replace("/", "-"), m.group(2)))
            scan.add(m.group(3))
    return history("Perforce", "submitted changelists", changes, reviews=scan.reviews_found(), scan=scan) if changes else None


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
        changes, scan = [], MessageScan()
        for e in entries:
            changes.append(((e.findtext("date") or "")[:10], e.findtext("author") or "(no author)"))
            scan.add(e.findtext("msg") or "")
    except ET.ParseError:
        return None
    if not changes:
        return None
    h = history("SVN", "revisions", changes, reviews=scan.reviews_found(), scan=scan)
    # Which path was counted: forms count trunk's revisions, not those of every branch.
    path = (run(["svn", "info", "--show-item", "relative-url", "--non-interactive", root], root, 120) or "").strip()
    if path.startswith("^/"):
        h["standard_branch"] = path
        if not re.search(r"(^|/)trunk(/|$)", path, re.I):
            h["notes"].append(f"Counted the revisions of {path}, not of a trunk: if that includes branches, run this"
                              " on a checkout of trunk for the count of trunk's revisions.")
    return h


def hg_history(root):
    out = run(["hg", "log", "--template",
               "{date|shortdate}\\x1f{author|person}\\x1f{author|email}\\x1f{p2rev}\\x1f{desc}\\x1e", "."], root)
    changes, merges, scan = [], 0, MessageScan()
    for record in (out or "").split("\x1e"):
        fields = record.split("\x1f")
        if len(fields) == 5:
            date, name, email, p2, desc = fields
            changes.append((date.strip(), (name, email)))
            merges += p2.strip() != "-1"
            scan.add(desc)
    return history("Mercurial", "commits", changes, merges, scan.reviews_found(), scan=scan) if changes else None


def bzr_history(root):
    """Bazaar, through Breezy (brz) or the original bzr."""
    out = run(["brz", "log", "--long", "-n0", "."], root)
    if out is None:
        out = run(["bzr", "log", "--long", "-n0", "."], root)
    changes, scan = [], MessageScan()
    for block in re.split(r"^\s*-{20,}\s*$", out or "", flags=re.M):
        if not re.search(r"^\s*revno:", block, re.M):
            continue
        who = re.search(r"^\s*authors?:\s*(.+)$", block, re.M) or re.search(r"^\s*committer:\s*(.+)$", block, re.M)
        when = re.search(r"^\s*timestamp:\s*\w+ (\d{4}-\d\d-\d\d)", block, re.M)
        changes.append((when.group(1) if when else "", identities(who.group(1).split(",")[0]) if who else ("",)))
        scan.add(block.split("message:", 1)[-1])
    return history("Bazaar", "revisions", changes, reviews=scan.reviews_found(), scan=scan) if changes else None


def darcs_history(root):
    # At the repository's root, "." would match nothing; darcs may print a notice before the XML.
    here = [] if os.path.isdir(os.path.join(root, "_darcs")) else ["."]
    out = run(["darcs", "log", "--xml-output", *here], root)
    if not out or "<changelog" not in out:
        return None
    import xml.etree.ElementTree as ET
    try:
        patches = list(ET.fromstring(out[out.index("<changelog"):]).iter("patch"))
    except ET.ParseError:
        return None
    changes, scan = [], MessageScan()
    for p in patches:
        d = p.get("date", "")
        changes.append((f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) >= 8 else "", identities(p.get("author", ""))))
        scan.add((p.findtext("name") or "") + "\n" + (p.findtext("comment") or ""))
    return history("Darcs", "patches", changes, reviews=scan.reviews_found(), scan=scan) if changes else None


def fossil_history(root):
    out = run(["fossil", "timeline", "-n", "0", "-t", "ci", "-W", "0", "-p", ".", "-F", "%H|%a|%d|%c"], root)
    changes, scan = [], MessageScan()
    for line in (out or "").splitlines():
        fields = line.split("|", 3)
        if len(fields) == 4 and re.fullmatch(r"[0-9a-f]{20,}", fields[0]) and fields[3] != "initial empty check-in":
            changes.append((fields[2][:10], fields[1]))
            scan.add(fields[3])
    return history("Fossil", "check-ins", changes, reviews=scan.reviews_found(), scan=scan) if changes else None


def cvs_history(root):
    """CVS keeps a history per file; a commit is the file revisions sharing a commit id (or, from
    before CVS had them, the same author, minute and message)."""
    out = run(["cvs", "-q", "log"], root)
    commits = {}
    for m in re.finditer(r"^revision [\d.]+\n(date: (\d{4}[-/]\d\d[-/]\d\d) (\d\d:\d\d)[^\n]*?author: ([^;]+);[^\n]*)\n"
                         r"(?:branches:[^\n]*\n)?(.*?)(?=^-{28}$|^={77}$)", out or "", re.M | re.S):
        info, date, minute, author, message = m.groups()
        cid = re.search(r"commitid: (\w+)", info)
        key = cid.group(1) if cid else (author, date, minute, message.strip())
        commits[key] = (date.replace("/", "-"), author.strip(), message)
    scan = MessageScan()
    for _, _, message in commits.values():
        scan.add(message)
    changes = [(date, author) for date, author, _ in commits.values()]
    return history("CVS", "commits", changes, reviews=scan.reviews_found(), scan=scan) if changes else None


def tfvc_history(root):
    """Team Foundation Version Control (Azure DevOps / TFS), through Visual Studio's tf command."""
    flag = "/" if os.name == "nt" else "-"
    out = run(["tf", "history", ".", f"{flag}recursive", f"{flag}noprompt", f"{flag}format:brief"], root)
    changes = []
    for line in (out or "").splitlines():
        m = re.match(r"^\s*(\d+)\s+(.+?)\s{2,}(\S+)", line)   # changeset, user, date (in the local format)
        if m:
            year = re.search(r"\d{4}", m.group(3))
            changes.append((year.group(0) if year else "", m.group(2).strip()))
    return history("Team Foundation (TFVC)", "changesets", changes) if changes else None


def plastic_history(root):
    """Plastic SCM (Unity Version Control): changesets, and code reviews (its pull requests)."""
    out = run(["cm", "find", "changeset", "--format={date}|{owner}|{comment}", "--nototal"], root)
    rows = [line.split("|", 2) for line in (out or "").splitlines() if "|" in line]
    if not rows:
        return None
    # Plastic prints dates in the computer's local format, so only the year is reliable.
    changes = [((re.findall(r"\d{4}", r[0]) or [""])[0], r[1]) for r in rows]
    scan = MessageScan()
    for r in rows:
        scan.add(r[2] if len(r) > 2 else "")
    reviews = run(["cm", "find", "review", "--format={id}", "--nototal"], root)
    review_count = len([line for line in (reviews or "").splitlines() if line.strip()])
    return history("Plastic SCM", "changesets", changes,
                   reviews=[("Plastic code reviews", review_count)] + scan.reviews_found(), scan=scan)


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
    # Found, but their history can't be read from the command line here.
    ("Unity Collaborate", [".collabignore"], [], None),
    ("Visual SourceSafe", ["vssver2.scc", "vssver.scc", "mssccprj.scc"], [], None),
    ("SourceGear Vault", ["_sgvault"], [], None),
]
# Their markers in a folder, for spotting repositories inside the scanned folder.
REPOSITORY_MARKERS = {m: name for name, markers, _, _ in VERSION_CONTROL for m in markers if name != "Visual SourceSafe"}
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
            present = any(find_up(root, m) for m in markers)
        if not present:
            continue
        if read is None:
            found.append(f"{name} (its history can't be read by this script: please ask for an export)")
        elif not any(tool_path(t) for t in tools):
            found.append(f"{name} (but the {tools[0]} command isn't installed, so no history)")
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
    p4 = perforce_history(root)
    if p4:
        found.append("Perforce")
        histories.append(p4)
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
        out.append(f"{indent}  Pull requests: none found in commit messages or on the server (which doesn't mean there"
                   " were none)")
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
    return os.path.join(db, data)


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
    checkins, last = [], None
    for when, user, comment, _ in changes:
        if last and user.lower() == last[1].lower() and (
                when - last[0] <= VSS_SAME_CHECKIN or (comment and comment == last[2] and when - last[0] <= VSS_SAME_COMMENT)):
            last = (when, user, comment)
            continue
        last = (when, user, comment)
        checkins.append((datetime.fromtimestamp(when, timezone.utc).strftime("%Y-%m-%d"), user or "(no name)"))
    notes = []
    if damaged or unreadable:
        notes.append(f"{plural(damaged + unreadable, 'damaged or unreadable record')} in the database left out.")
    h = history("Visual SourceSafe", "check-ins (revisions grouped by person and time)", checkins, notes=notes)
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
        for db in list(extra_databases) + [os.environ.get("SSDIR", "")]:
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
        """[(database, history)] of the databases found, including ones the project files name."""
        for where in self.recorded:
            self.add_database(where)
        return [(db, h) for db, h in ((db, read_sourcesafe(db)) for db in self.databases[:5]) if h]


# ##############################
# SourceSafe and Git together
# ##############################
GIT_RELEASED = "2005-04-07"   # Git's first release: a commit dated before it was imported
VSS_IN_MESSAGE = re.compile(r"source\s?safe|\bvss\b|vss2git|vssmigrate", re.I)


def imported_git_history(root, h):
    """What a Git history shows of an earlier system: commits dated before Git existed (converted
    history), messages that name SourceSafe, and a first commit that brings in the whole code at once."""
    pre_git = [d for d in h["dates"] if d < GIT_RELEASED]
    out = {"pre_git": pre_git, "vss_messages": h.get("vss_messages", 0), "bulk_start": None}
    roots = (run(["git", "rev-list", "--max-parents=0", "HEAD"], root, 120) or "").split()[:5]
    for sha in roots:
        stat = run(["git", "show", "--format=%ad", "--date=short", "--shortstat", sha], root, 300) or ""
        files = re.search(r"(\d+) files? changed", stat)
        if files and int(files.group(1)) >= 300:
            out["bulk_start"] = (stat.split("\n", 1)[0].strip(), int(files.group(1)))
    return out


def combined_history(git, vss):
    """(lines, (changes, first, last, how)) putting a SourceSafe history and a Git history
    together without counting the same work twice. git and vss are history dicts."""
    g, v = git["dates"], vss["dates"]
    if not g or not v:
        return [], None
    g_unit = git["rows"][0][0].split(" ")[0]   # "commits"
    vs, ve, gs, ge = v[0], v[-1], g[0], g[-1]
    out = [f"  SourceSafe: {len(v):,} check-ins, {vs} to {ve}",
           f"  Git:        {len(g):,} {g_unit}, {gs} to {ge}"]

    # ####################
    # How the two fit together
    # ####################
    from datetime import date
    v_days, g_days = set(v), set(g)
    shared = len(v_days & g_days) / len(v_days)
    starts_together = abs((date.fromisoformat(gs) - date.fromisoformat(vs)).days) <= 31
    if starts_together and shared >= 0.5:
        out += [f"  Git already holds the SourceSafe history: it has commits on {100 * shared:.0f}% of the days with SourceSafe",
                "  check-ins, so the history was converted into Git. The Git numbers are the whole history; don't add",
                "  the SourceSafe check-ins to them."]
        return out, (len(g), gs, ge, "converted into Git")
    if ve <= gs:
        out += [f"  One after the other: SourceSafe until {ve}, then Git from {gs}.",
                f"  Together: {len(v) + len(g):,} changes from {vs} to {ge}."]
        return out, (len(v) + len(g), vs, ge, "SourceSafe, then Git")
    both_from, both_to = max(vs, gs), min(ve, ge)
    v_both = sum(1 for d in v if both_from <= d <= both_to)
    g_both = sum(1 for d in g if both_from <= d <= both_to)
    v_alone = sum(1 for d in v if not (both_from <= d <= both_to))
    out += [f"  Both were in use from {both_from} to {both_to}: SourceSafe has {v_both:,} check-ins then, Git {g_both:,}",
            f"  {g_unit}. The same work may be in both, so that time is counted once, from Git.",
            f"  Together, without counting it twice: {v_alone + len(g):,} changes from {min(vs, gs)} to {max(ve, ge)}."]
    return out, (v_alone + len(g), min(vs, gs), max(ve, ge), "SourceSafe and Git, overlapping")


# ##############################
# Report section
# ##############################

def sourcesafe_lines(root, vss, git_h, histories, alerts):
    """The report's SourceSafe part: each database's history (added to histories), how it fits
    with the Git history, or, when the code was in SourceSafe but the database isn't here, how
    to include it. Returns (lines, combined), combined being (changes, first, last, how) or None."""

    # ####################
    # The databases found, and how they fit with Git
    # ####################
    out, combined = [], None
    found = vss.histories()
    for where in vss.recorded:   # on screen only: a server's name isn't for the report
        reachable = os.path.isfile(os.path.join(where, "srcsafe.ini"))
        print(f"SourceSafe database named in the project files (shown here only, not saved in the report): {where}"
              + ("" if reachable else " (not reachable from this computer)"))
    for _, h in found:
        out += ["", "Version control history (Visual SourceSafe database):"] + history_lines(h)
        histories.append(h)
    imported = imported_git_history(root, git_h) if git_h else None
    if git_h and found:
        lines, combined = combined_history(git_h, found[0][1])
        out += ["", "SourceSafe and Git together:"] + lines

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
    return out, combined


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


def sqlcmd(server, query, database="master"):
    """sqlcmd's output, or None. Windows sign-in unless SQLCMDUSER / SQLCMDPASSWORD are set."""
    exe = tool_path("sqlcmd")
    if exe is None:
        import glob
        exe = next((m for p in SQLCMD_PATHS for m in sorted(glob.glob(p), reverse=True)), None)
    if exe is None:
        return None
    auth = [] if os.environ.get("SQLCMDUSER") else ["-E"]
    base = [exe, "-S", server, "-d", database, *auth, "-y", "0", "-f", "65001", "-b", "-Q", query]   # -y 0: no width limit
    for extra in (["-C"], []):   # -C: trust the server's certificate (newer sqlcmd insists on encryption)
        try:
            out = subprocess.run(base[:1] + extra + base[1:], capture_output=True, timeout=600, env=quiet_env(),
                                 stdin=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            return None
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "replace")
    return None


def read_sql_server(server, databases=()):
    """{"databases": n, "objects": Counter, "code": [(kind, db.key, definition)], "tables": n, "error"}."""
    found = {"databases": 0, "objects": Counter(), "code": [], "tables": 0}
    names = list(databases)
    if not names:
        out = sqlcmd(server, SQL_SERVER_DATABASES)
        if out is None:
            found["error"] = ("couldn't connect (is sqlcmd installed? may this Windows account sign in? or set"
                              " SQLCMDUSER and SQLCMDPASSWORD)")
            return found
        names = [n.strip() for n in sqlcmd_values(out) if n.strip()]
    for db in names:
        progress(f"Reading the code in SQL Server database {db} ...")
        out = sqlcmd(server, SQL_SERVER_MODULES, db)
        if out is None:
            continue
        found["databases"] += 1
        for record in sqlcmd_values(out):
            fields = record.split("\x1f", 2)
            if len(fields) == 3:
                kind = SQL_MODULE_TYPES.get(fields[0].strip(), "other objects")
                if kind:
                    found["objects"][kind] += 1
                    found["code"].append((kind, f"{db.lower()}.{fields[1].strip().lower()}", fields[2]))
        tables = (sqlcmd_values(sqlcmd(server, SQL_SERVER_TABLES, db)) or ["0"])[0].strip()
        found["tables"] += int(tables) if tables.isdigit() else 0
    progress()
    if not found["databases"] and "error" not in found:
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
# the original is never touched.
ACCESS_POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$out = @{}
try { $app = New-Object -ComObject Access.Application } catch { '{"error":"Microsoft Access is not installed"}'; exit }
try {
  $app.Visible = $false
  try { $app.AutomationSecurity = 3 } catch {}
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
  try { $app.CloseCurrentDatabase() } catch {}
  try { $app.Quit() } catch {}
  try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {}
}
$out | ConvertTo-Json -Depth 5 -Compress
"""


def read_access_database(path):
    """{"how", "forms", "reports", "macros", "modules", "tables", "odbc", "queries": [(name, sql)],
    "vba": [code], "error"} for an Access database, read as fully as this computer allows."""
    import tempfile
    found = {"how": None, "queries": [], "vba": []}
    if os.name == "nt":
        # Access may write to a database it opens, so it gets a copy, deleted straight after.
        work = tempfile.mkdtemp(prefix="size_codebase_")
        try:
            copy = os.path.join(work, os.path.basename(path))
            shutil.copyfile(path, copy)
            found.update(read_access_with_access(copy, work))
        except OSError as e:
            found["error"] = str(e)
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
    if not isinstance(got, dict) or got.get("error") and "forms" not in got:
        return {"error": got.get("error") if isinstance(got, dict) else None}
    as_list = lambda v: v if isinstance(v, list) else ([v] if v else [])   # ConvertTo-Json unwraps 1-item lists
    return {"how": "Microsoft Access", "forms": got.get("forms", 0), "reports": got.get("reports", 0),
            "macros": got.get("macros", 0), "modules": got.get("modules", 0), "tables": got.get("tables", 0),
            "odbc": got.get("odbc", 0),
            "queries": [(q.get("name", ""), q.get("sql") or "") for q in as_list(got.get("queries")) if isinstance(q, dict)],
            "vba": [c.get("code") or "" for c in as_list(got.get("vba")) if isinstance(c, dict)],
            "vba_error": got.get("vba_error")}


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
    path = re.sub(r"\$\([^)]*\)|\$\{[^}]*\}|%[^%]+%|\$\w+", "", path).replace("\\", "/")
    parts = [p for p in path.split("/") if p.strip()]
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
            if clean in ("", ".", "./") or (local and os.path.exists(local) and is_within(local, self.root)):
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
        if m and run(["git", "-c", "credential.helper=", "ls-remote", "--exit-code",
                      f"https://{m.group(1)}/{m.group(2)}/{m.group(3)}.git", "HEAD"], root, 30) is not None:
            found.append(f"{m.group(1)}/{m.group(2)}/{m.group(3)}")
    return found


def git_tracked_files(root):
    """The files Git holds, relative to root (normcase), or None if root isn't in a repository with commits."""
    if run(["git", "rev-parse", "HEAD"], root, 60) is None:
        return None
    out = run(["git", "ls-files", "-z"], root, 600)
    return None if out is None else {os.path.normcase(p.replace("/", os.sep)) for p in out.split("\0") if p}


def git_ignored(root):
    """The files and folders Git is told to ignore (build output, local settings ...), relative to
    root (normcase): empty outside a Git repository."""
    out = run(["git", "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory"], root, 600)
    return {os.path.normcase(p.rstrip("/").replace("/", os.sep)) for p in (out or "").split("\0") if p}


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
# Both are counted here without them, over the studio's own code. If they happen to be installed,
# they're also run the way the forms ask, over the whole folder.

# ##############################
# This script's estimates
# ##############################
# The languages on forms' lists, and the names this script gives some of them.
FORM_LANGUAGES = {"C#", "C", "C++", "CSS", "Go", "HTML", "Java", "JavaScript", "Kotlin", "PHP", "Python", "Ruby",
                  "Rust", "SQL", "Scala", "Shell", "Swift", "TypeScript", "ABAP", "Ada", "Apex", "Assembly", "COBOL",
                  "Delphi", "Erlang", "Fortran", "JCL", "LabVIEW", "MUMPS", "OCaml", "Object Pascal", "PL/I", "Perl",
                  "Progress ABL", "RPG", "Smalltalk", "Tcl", "VHDL", "Verilog", "Visual Basic 6"}
FORM_LANGUAGE_NAMES = {"UnityScript": "JavaScript", "T-SQL": "SQL", "PL/SQL": "SQL", "Pascal": "Object Pascal"}
TOKEN = re.compile(rb"\w+|[^\w\s]")


def form_language(lang, ext=""):
    """A language as forms name it: "C/C++" split by file, "Python (build scripts)" as Python."""
    if lang == "C/C++":
        return "C" if ext == ".c" else "C header" if ext == ".h" else "C++"
    lang = re.sub(r" \(.*\)$", "", lang)
    return FORM_LANGUAGE_NAMES.get(lang, lang)


class StandardMeasures:
    """Logical lines, generated lines and copied lines of the studio's own code, file by file."""
    WINDOW, MIN_TOKENS = 5, 50   # jscpd's --min-lines and --min-tokens, as forms set them
    BLOOM_BITS = 1 << 28         # the runs of lines seen so far, in a Bloom filter: 32 MB however big the code

    def __init__(self):
        self.logical = self.generated = self.copied = self.ignored = 0
        self.languages = Counter()         # logical lines, by language as forms name them
        self.non_blank = Counter()         # non-blank lines seen, by this script's language name
        self.seen = bytearray(self.BLOOM_BITS >> 3)

    # ####################
    # Counting files
    # ####################

    def add(self, code, lines, lang, ext, generated):
        """code: a file's logical lines (see code_lines); lines: its non-blank lines as counted in
        the report, which can leave some out (the data in SQL scripts, a VB form's layout)."""
        logical = min(len(code), lines)
        self.logical += logical
        self.generated += logical if generated else 0
        self.languages[form_language(lang, ext)] += logical
        self.non_blank[lang] += lines
        self.copied += min(self.copied_lines(code), logical)

    def skip(self, lines, lang):
        """A file left out, as scc leaves it out: Git ignores it (build output, say)."""
        self.ignored += lines
        self.non_blank[lang] += lines

    def add_uncounted(self, lines_by_lang):
        """Code counted in the report that wasn't read here file by file (code inside databases),
        as its non-blank lines."""
        extra = 0
        for lang, n in lines_by_lang.items():
            more = n - self.non_blank[lang]
            if more > 0:
                self.logical += more
                self.languages[form_language(lang)] += more
                extra += more
        return extra

    # ####################
    # Copied code
    # ####################

    def copied_lines(self, code):
        """How many of a file's logical lines repeat code seen before, in it or in an earlier file:
        runs of at least WINDOW lines and MIN_TOKENS tokens. As jscpd counts, the first copy is
        original and each later one is copied. Lines are compared without their spacing."""
        n, w = len(code), self.WINDOW
        if n < w:
            return 0
        keys = [hash(b" ".join(line.split())) for line in code]
        copied = bytearray(n)
        seen, mask = self.seen, self.BLOOM_BITS - 1
        for i in range(n - w + 1):
            h = hash(tuple(keys[i:i + w])) & 0xFFFFFFFFFFFFFFFF
            a, b, c = h & mask, (h >> 28) & mask, ((h >> 36) ^ (h * 0x9E3779B1)) & mask
            if seen[a >> 3] >> (a & 7) & 1 and seen[b >> 3] >> (b & 7) & 1 and seen[c >> 3] >> (c & 7) & 1:
                copied[i:i + w] = b"\1" * w
            else:
                seen[a >> 3] |= 1 << (a & 7)
                seen[b >> 3] |= 1 << (b & 7)
                seen[c >> 3] |= 1 << (c & 7)
        return sum(m.end() - m.start() for m in re.finditer(rb"\x01+", bytes(copied))
                   if len(TOKEN.findall(b" ".join(code[m.start():m.end()]))) >= self.MIN_TOKENS)

    # ####################
    # Primary language
    # ####################

    def primary_language(self):
        """(the language with the most logical lines as forms name it, or "Other", its own name)."""
        langs = Counter(self.languages)
        headers = langs.pop("C header", 0)
        if headers:
            langs["C" if langs["C"] > langs["C++"] else "C++"] += headers
        top = next((lang for lang, n in langs.most_common(1) if n), None)
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
# Node.js isn't needed) and checked against these SHA-256 checksums before they're run. Nothing is
# sent anywhere. They're kept in tools_folder(); deleting it removes them.
SCC_URL = "https://github.com/boyter/scc/releases/download/v4.1.0/scc_"
JSCPD_URL = "https://registry.npmjs.org/jscpd-{0}/-/jscpd-{0}-5.4.1.tgz"
PINNED_TOOLS = {   # tool: (version, the program's place in the download, {(system, cpu[, C library]): (url, sha256)})
    "scc": ("4.1.0", "", {
        ("Darwin", "arm64"): (SCC_URL + "Darwin_arm64.tar.gz",
                              "7201c7aa4aace058d43308462cba72adb18f6094c08c0741727455976d0a0747"),
        ("Darwin", "x64"): (SCC_URL + "Darwin_x86_64.tar.gz",
                            "7f705031228add7e55edded409179a60de6b538d41f153ba2922dee95adda50d"),
        ("Linux", "arm64"): (SCC_URL + "Linux_arm64.tar.gz",
                             "6e0d2a1f8d3540ba7df185477dec40bb7340f1b214bfd303147de5cad2bd7b8b"),
        ("Linux", "x64"): (SCC_URL + "Linux_x86_64.tar.gz",
                           "c7328436d3027f4357d3d7853f7dc3ac2bbcb4ca08f1adad91a27c593884079b"),
        ("Linux", "x86"): (SCC_URL + "Linux_i386.tar.gz",
                           "cddeda90ec848c614c6c390eae8b638f94d88e9450e00bf2ba5f420f83b66de1"),
        ("Windows", "arm64"): (SCC_URL + "Windows_arm64.zip",
                               "fdc1188bec07ab46fd391686c404abcd0bed92fffb5f1bb03aa9050dd7bc7f15"),
        ("Windows", "x64"): (SCC_URL + "Windows_x86_64.zip",
                             "4a433984f45ff29c94eeb3af6db5b511c58f5bf74063dccedafcbf473cb8ff31"),
        ("Windows", "x86"): (SCC_URL + "Windows_i386.zip",
                             "7b5b924e85b6fe7f1ba56f15e7e27220a2c0c7089f815368e61f24c6ef317688"),
    }),
    "jscpd": ("5.4.1", "package/bin/", {
        ("Darwin", "arm64"): (JSCPD_URL.format("darwin-arm64"),
                              "cafdb84c9345d0790e4a2297789cfeb16ac939442f322c49a54961468c895aff"),
        ("Darwin", "x64"): (JSCPD_URL.format("darwin-x64"),
                            "43dd411716d0a90803d2ad3d3cd74da96523fc31f13f202c6c6e77b0b4841beb"),
        ("Linux", "arm64", "gnu"): (JSCPD_URL.format("linux-arm64-gnu"),
                                    "74cbf9d3faa5240d2a17f03a6829fb67cc04f7a37059b3a6f57e9d3adb438b94"),
        ("Linux", "arm64", "musl"): (JSCPD_URL.format("linux-arm64-musl"),
                                     "e81c41fa6fa70788c8e47f4eff0ee3d5f00dd8b8cf0489ac7f610105798e4847"),
        ("Linux", "x64", "gnu"): (JSCPD_URL.format("linux-x64-gnu"),
                                  "5cfd74b986e3d9205dd639a84249203595be67f6062ac652f1b78884b1dea439"),
        ("Linux", "x64", "musl"): (JSCPD_URL.format("linux-x64-musl"),
                                   "28f47a136fc81577ecb67db247b4575abd17941a5682bb57caf7ca967911dc73"),
        ("Windows", "arm64"): (JSCPD_URL.format("windows-arm64-msvc"),
                               "4250180ae1129b22ed6d3e3be7c60c18678fae78d36b2cc65c67d04b0406dad9"),
        ("Windows", "x64"): (JSCPD_URL.format("windows-x64-msvc"),
                             "657b833dbe8c642984d859bafc9557827ea11808bed76fa23bed63fe6d3da3a0"),
    }),
}
FETCH_TOOLS = True          # --no-download: use only an scc or jscpd that's already installed
KEEP_TOOL_REPORTS = False   # --reports: save scc's and jscpd's own reports beside this one


def this_computer():
    """(system, cpu, C library) as PINNED_TOOLS names them."""
    import platform
    system = platform.system()
    cpu = platform.machine().lower()
    cpu = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "i386": "x86", "i686": "x86"}.get(cpu, cpu)
    libc = ("gnu" if platform.libc_ver()[0] == "glibc" else "musl") if system == "Linux" else None
    return system, cpu, libc


def tools_folder():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "size_codebase_tools")


def download(url):
    import ssl
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=300) as response:
            return response.read()
    except urllib.error.URLError as e:
        if not isinstance(e.reason, ssl.SSLError):
            raise
    # Python from python.org on macOS has no certificates until its "Install Certificates" is run.
    # The pinned checksum is what vouches for the file, so fetch it without checking the certificate.
    with urllib.request.urlopen(url, timeout=300, context=ssl._create_unverified_context()) as response:
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
    """(path, version) of scc or jscpd: the pinned version, fetched if need be, or else a copy that's
    already installed. (None, why not) if neither."""
    import hashlib
    version, inside, builds = PINNED_TOOLS[name]
    system, cpu, libc = this_computer()
    exe = name + (".exe" if system == "Windows" else "")
    target = os.path.join(tools_folder(), f"{name}-{version}", exe)
    if os.path.isfile(target):
        return target, version

    # ####################
    # Fetching it
    # ####################
    build = builds.get((system, cpu, libc)) or builds.get((system, cpu))
    if not FETCH_TOOLS:
        why = f"{name} isn't installed, and fetching it was turned off (--no-download)"
    elif build is None:
        why = f"{name} has no build for this computer ({system}, {cpu})"
    else:
        url, sha256 = build
        try:
            progress(f"Fetching {name} {version} (once) from {url.split('/')[2]} ...")
            data = download(url)
            if hashlib.sha256(data).hexdigest() != sha256:
                raise ValueError("the download doesn't match its checksum, so it wasn't used")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target + ".part", "wb") as f:
                f.write(archive_member(data, inside + exe))
            os.chmod(target + ".part", 0o755)
            os.replace(target + ".part", target)
            return target, version
        except Exception as e:   # offline, a proxy, a full disk ...: fall back to an installed copy
            why = f"{name} couldn't be fetched ({type(e).__name__}: {e})"
        finally:
            progress()

    # ####################
    # Else, a copy that's already installed
    # ####################
    installed = tool_path(name)
    return (installed, "installed") if installed else (None, why)


# ####################
# Running them
# ####################

def extra_code_args():
    """(scc's, jscpd's) options for the languages named with --code-ext."""
    scc, formats = [], defaultdict(list)
    for ext, (name, like) in sorted(EXTRA_CODE.items()):
        _, scc_like, jscpd_like = LIKE_LANGUAGES[like]
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


def tool_measures(root, leave_out):
    """scc's and jscpd's figures, with the options forms give, for the studio's own code: leave_out
    lists the folders ("folder/**") and files that aren't (see left_out_paths). scc counts the whole
    folder file by file, so the figure for all of it comes too. ({figures}, [why a tool wasn't run],
    {tool: its own report, if KEEP_TOOL_REPORTS}). jscpd's report holds copies of the code."""
    import tempfile
    found, missing, reports = {}, [], {}
    matching = {os.path.normcase(p[:-3] if p.endswith("/**") else p).replace("\\", "/") for p in leave_out}
    matching |= {"**"} if "**" in leave_out else set()
    scc_extra, jscpd_extra = extra_code_args()

    # ####################
    # scc
    # ####################
    scc, version = find_tool("scc")
    if scc is None:
        missing.append(version)
    else:
        progress("Counting lines with scc ...")
        for key, extra in (("logical", []), ("generated", SCC_GENERATED_ARGS)):
            try:
                langs = json.loads(run([scc, *SCC_ARGS, *scc_extra, *extra, "--by-file", "--format", "json", "."], root)
                                   or "null")
            except ValueError:
                langs = None
            if not isinstance(langs, list):
                missing.append("scc failed")
                break
            files = [(str(lang.get("Name", "")), f) for lang in langs for f in lang.get("Files") or []]
            own = [(lang, int(f.get("Code", 0))) for lang, f in files
                   if not is_left_out(re.sub(r"^\.[/\\]", "", str(f.get("Location", ""))), matching)]
            if key == "logical":
                found["scc_logical_lines"] = sum(n for _, n in own)
                found["scc_whole_folder_logical_lines"] = sum(int(f.get("Code", 0)) for _, f in files)
                by_lang = Counter()
                for lang, n in own:
                    by_lang[lang] += n
                found["scc_logical_lines_by_language"] = dict(by_lang.most_common(15))
            else:
                found["scc_generated_lines"] = sum(n for lang, n in own if lang.endswith("(gen)"))
        else:
            found["scc_version"] = version
            if KEEP_TOOL_REPORTS:
                reports["scc"] = run([scc, *SCC_ARGS, *scc_extra, "--format", "json", "."], root)
        progress()

    # ####################
    # jscpd
    # ####################
    jscpd, version = find_tool("jscpd")
    if jscpd is None:
        missing.append(version)
    else:
        out = tempfile.mkdtemp(prefix="size_codebase_jscpd_")
        progress("Measuring duplication with jscpd (slow on big projects) ...")
        try:
            config = os.path.join(out, "jscpd.json")
            with open(config, "w", encoding="utf-8") as f:
                json.dump({"ignore": JSCPD_IGNORE + [glob_escape(p[:-3]) + "/**" if p.endswith("/**") else
                                                     "**" if p == "**" else glob_escape(p) for p in leave_out]}, f)
            run([jscpd, ".", *JSCPD_ARGS, *jscpd_extra, "--output", out, "--config", config], root, 3600)
            with open(os.path.join(out, "jscpd-report.json"), encoding="utf-8") as f:
                text = f.read()
            total = json.loads(text)["statistics"]["total"]
            percentage = float(total.get("percentage") or 0)
            found["jscpd_duplication_ratio"] = round(percentage / 100, 4) if percentage == percentage else 0.0
            found["jscpd_duplicated_lines"], found["jscpd_lines"] = total.get("duplicatedLines"), total.get("lines")
            found["jscpd_version"] = version
            if KEEP_TOOL_REPORTS:
                reports["jscpd"] = text
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            missing.append("jscpd failed")
        finally:
            shutil.rmtree(out, ignore_errors=True)
            progress()
    return found, missing, reports


# ##############################
# Report section
# ##############################
AI_ERA = "2022"   # changes made before this year were almost certainly written without AI assistants


def standard_measures_report(standard, histories, vcs_found, database_lines, tools, missing, left_out):
    """(report lines, facts) for the standard measures: scc's and jscpd's figures (see tool_measures)
    where they could be run, else this script's estimates of them (see StandardMeasures)."""

    # ####################
    # The figures
    # ####################
    language, raw = standard.primary_language()
    counted = [h for h in histories if h.get("standard_commits") is not None]
    commits = sum(h["standard_commits"] for h in counted)
    dates = [d for h in histories for d in h.get("dates", ())]
    before = sum(1 for d in dates if d < AI_ERA)
    shallow = any("shallow clone" in note for h in histories for note in h.get("notes", ()))
    estimate = round(standard.copied / standard.logical, 4) if standard.logical else 0.0
    if not histories:
        delivery = "flat snapshot (no version-control history found)"
    elif all(h["vcs"] == "Git" for h in histories):
        delivery = "Git, but a shallow clone: its older history is missing" if shallow else "Git, full history"
    else:
        delivery = (f"{', '.join(sorted({h['vcs'] for h in histories}))}: convert it to Git, or deliver a flat"
                    " snapshot")
    where = "; ".join(f"{h['vcs']}" + (f" {h['standard_branch']}" if h.get("standard_branch") else "")
                      for h in counted)
    scc = "scc_logical_lines" in tools
    jscpd = "jscpd_duplication_ratio" in tools
    logical = tools["scc_logical_lines"] if scc else standard.logical
    generated = tools["scc_generated_lines"] if scc else standard.generated
    ratio = tools["jscpd_duplication_ratio"] if jscpd else estimate
    measured = " and ".join(f"{t} {tools[t + '_version']}" for t in ("scc", "jscpd") if t + "_version" in tools)

    # ####################
    # Report lines
    # ####################
    out = ["", "Standard measures, as buyers' codebase forms ask for them, of the apparently original code above"
               + (f"\n(measured with {measured}, with the forms' options):" if measured else ":"),
           f"  {'Logical lines of code' + (' (scc)' if scc else ' (estimated as scc counts them)'):<56} {logical:>12,}",
           f"  {'  of which generated' + (' (scc --gen)' if scc else ' (estimated)'):<56} {generated:>12,}",
           f"  {'Duplication ratio' + (' (jscpd)' if jscpd else ' (estimated as jscpd measures it)'):<56}"
           f" {ratio:>12.4f}",
           f"  {'Commits on the main branch, without merges or reverts':<56} "
           + (f"{commits:>12,}   ({where})" if counted else f"{'none':>12}"),
           f"  {'Repositories':<56} {max(1, len(histories)):>12,}",
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
    if missing:
        out.append(f"  (estimated where scc or jscpd couldn't be used: {'; '.join(missing)})")
    if database_lines and not scc:
        out.append(f"  (includes {database_lines:,} lines of code read from databases, counted as non-blank lines)")
    if standard.ignored and not scc:
        out.append(f"  (leaves out {standard.ignored:,} lines in files Git ignores, such as build output, as scc does)")
    if counted and len(counted) < len(histories):
        out.append(f"  (commits from {len(counted)} of the {len(histories)} histories: the others couldn't be counted)")

    # ####################
    # Facts, for the machine-readable copy
    # ####################
    facts = {"logical_lines": logical, "generated_lines": generated, "duplication_ratio": ratio,
             "measured_with": measured or None, "not_measured": missing,
             "commits_main_branch_no_merges_or_reverts": commits if counted else None,
             "commit_branches": where or None, "repositories": max(1, len(histories)),
             "primary_language": language, "primary_language_detail": raw, "history": delivery,
             "changes_before_" + AI_ERA: [before, len(dates)] if dates else None,
             "left_out": len(left_out) if measured else None,   # how many: their names stay out of reports
             "estimates": {"logical_lines": standard.logical, "generated_lines": standard.generated,
                           "duplication_ratio": estimate, "copied_lines": standard.copied,
                           "logical_lines_by_language": dict(standard.languages.most_common()),
                           "database_lines": database_lines, "git_ignored_lines": standard.ignored},
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

    # ####################
    # What the walk collects
    # ####################
    problems = []           # unexpected errors: reported, but the scan carries on
    alerts = []             # what a reader should check, for the summary at the top
    linked_dirs = lfs_pointers = epic_notice_lines = 0
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
    standard = StandardMeasures()
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
    ignored = git_ignored(root)
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
                if first in here and os.path.exists(os.path.join(dirpath, marker)) and \
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
            if dl in skip or dl.endswith(".egg-info") or os.path.isfile(os.path.join(full, "pyvenv.cfg")):
                continue
            if dl.startswith("cmake-build-") or os.path.isfile(os.path.join(full, "CMakeCache.txt")):
                continue   # a CMake build folder
            if dl == "packages" and any(f.lower().endswith(".nupkg") for sub in list_files(full)[:5]
                                        for f in list_files(os.path.join(full, sub))):
                continue   # NuGet's downloaded packages
            if is_link(full):
                linked_dirs += 1
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
                try:
                    st = os.stat(path)
                except OSError:
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
                if c in ("own", "test") or (c == "generated" and category in ("own", "test")):
                    parts = os.path.normcase(rel_file).split(os.sep)
                    if ignored and any(os.sep.join(parts[:i]) in ignored for i in range(1, len(parts) + 1)):
                        standard.skip(lines, lang)
                    else:
                        standard.add([] if code.get("data_lines") else code["code"], lines, lang, ext,
                                     c == "generated")
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
                problem = f"{type(e).__name__}: {e}"
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
        problems.append(f"reading the version-control history: {type(e).__name__}: {e}")
    out = [f"Project: {only or os.path.basename(root)}"]
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
            problems.append(f"reporting {what}: {type(e).__name__}: {e}")
    if any(compiled for _, compiled, _ in dbcode.access):
        alerts.append("a compiled Access database (its VBA source is gone)")
    if any(got.get("how") is None for _, _, got in dbcode.access):
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
    if linked_dirs:
        out += ["", f"NOTE: Skipped {plural(linked_dirs, 'linked folder')} (symbolic links or junctions), so nothing is",
                "      counted twice. If one holds code that lives nowhere else, run this script on it too."]
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
        vss_out, combined = sourcesafe_lines(root, vss, git_h, histories, alerts)
        out += vss_out
    except Exception as e:
        problems.append(f"reading the SourceSafe history: {type(e).__name__}: {e}")
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
            problems.append(f"reading the engine's history: {type(e).__name__}: {e}")

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
            problems.append(f"reading the history of {rel}: {type(e).__name__}: {e}")
            continue
        out += ["", f"Repository inside this folder: {rel.replace(os.sep, '/')} ({', '.join(vcs) or 'unreadable'})"]
        for h in nested:
            out += [f"  History ({h['vcs']}):"] + history_lines(h, "  ")
            histories.append(h)
    if shown > 10:
        out.append(f"(and {shown - 10} more repositories inside this folder, not listed)")

    # ####################
    # Caveats about the history
    # ####################
    if histories or any("History (" in line for line in out):
        out += [""] + HISTORY_CAVEATS
    if missing:
        out += ["", "NOTE: This project is built with a custom Unreal Engine that isn't registered on this computer,",
                "      so the engine's own history and changes aren't included. Run this script on the engine's",
                "      folder too (the one that contains Engine/)."]

    # ####################
    # Standard measures
    # ####################
    standard_facts = None
    try:
        own_by_lang = Counter()
        for c in ("own", "test"):
            for lang, (_, n) in lines_by[c].items():
                own_by_lang[lang] += n
        database_lines = standard.add_uncounted(own_by_lang)
        kept = [os.path.relpath(p, root).replace(os.sep, "/") for p, c in marked.items() if c == "own"]
        left_out = left_out_paths(root, not_own_folders, not_own_files, kept)
        tools, missing, tool_reports = ({}, ["not run on a single file"], {}) if only else tool_measures(root, left_out)
        section, standard_facts = standard_measures_report(standard, histories, vcs_found, database_lines, tools,
                                                           missing, left_out)
        out += section
        if tool_reports and facts is not None:
            facts["tool_reports"] = tool_reports
    except Exception as e:   # a report section shouldn't cost the whole report
        problems.append(f"reporting the standard measures: {type(e).__name__}: {e}")

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
        rows, reviews = dict(histories[0]["rows"]), histories[0]["reviews"]
        unit = next(k for k, _ in histories[0]["rows"] if not k.startswith(" ") and "Epic" not in k)
        prs = max([v for k, v in reviews if isinstance(v, int) and "pull request" in k] or [0])
        people = rows["contributors"]
        count = rows[unit]
        unit_word = re.sub(r"s\b", "", unit, count=1) if count == 1 else unit   # "1 commit", "1 submitted changelist"
        summary.append(f"  History ({histories[0]['vcs']}): {fmt(count)} {unit_word} by {people:,}"
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
    if alerts:
        summary.append("  Check: " + "; ".join(alerts))
    out[1:1] = summary + [""]

    # ##############################
    # The numbers, for the machine-readable copy
    # ##############################
    if facts is not None:
        facts.update({
            "project": os.path.basename(root), "project_types": [[k, r.replace(os.sep, "/"), d] for k, r, d in projects],
            "lines": {c: {lang: {"files": f, "lines": n} for lang, (f, n) in lines_by[c].items()} for c in categories},
            "own_total": own_total, "duplicate_lines": duplicates[1], "untracked_lines": untracked[1],
            "console_lines": dict(console), "third_party_by_library": dict(libraries),
            "folders": [[k, n] for k, n in folder_breakdown(own_lines_by_dir)] if own_lines_by_dir else [],
            "visual_scripting": {row: {"files": f, "nodes": n} for row, (f, n) in graphs["own"].items()},
            "unreal_coverage": dict(coverage), "unreal_versions": dict(unreal_versions), "assets": dict(assets),
            "version_control": vcs_found,
            "histories": [{"vcs": h["vcs"], "rows": dict(h["rows"]), "reviews": dict(h["reviews"]),
                           "notes": h.get("notes", [])} for h in histories],
            "contributors": {"version_control": people_all if histories else None, "named_in_code": named},
            "dependencies_not_here": {"unknown": unknown_deps, "packages": {k: sorted(v) for k, v in deps.packages.items()},
                                      "missing_includes": dict(deps.missing_includes())},
            "precompiled_libraries": dict(binaries), "credentials": dict(secrets),
            "copyright_years": [min(copyright_years), max(copyright_years)] if copyright_years else None,
            "licence": licence, "public_repositories": public, "submodules": submodule_list,
            "alerts": alerts, "problems": problems, "standard_measures": standard_facts,
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


def save_report(report, name, here, facts=None):
    """Saves next to this script or, if that folder is read-only, in the current or home folder. The
    numbers go in a .json beside it too, for reading by machine, and scc's and jscpd's own reports
    (facts["tool_reports"], with --reports) beside that."""
    tool_reports = (facts or {}).pop("tool_reports", {})
    for folder in (here, os.getcwd(), os.path.expanduser("~")):
        out_path = os.path.join(folder, f"size_report_{name}.txt")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(report + "\n")
            if facts is not None:
                with open(os.path.join(folder, f"size_report_{name}.json"), "w", encoding="utf-8") as f:
                    json.dump(facts, f, indent=1, default=sorted)
            for tool, text in tool_reports.items():
                if text:
                    with open(os.path.join(folder, f"size_report_{name}_{tool}.json"), "w", encoding="utf-8") as f:
                        f.write(text)
            return out_path
        except OSError:
            continue
    return None


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
        print("Also saved beside it: scc's and jscpd's own reports (_scc.json, _jscpd.json). jscpd's holds copies of\n"
              "the duplicated code and the names of the files they're in: look it over before sending it.\n")


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
    global FETCH_TOOLS, KEEP_TOOL_REPORTS
    roots, args = [], sys.argv[1:]
    marks = {"--third-party": [], "--own": [], "--sql-server": [], "--sql-database": [], "--sourcesafe": [],
             "--code-ext": []}
    while args:
        arg = args.pop(0)
        if arg == "--no-download":
            FETCH_TOOLS = False
        elif arg == "--reports":
            KEEP_TOOL_REPORTS = True
        elif arg in marks and args:
            marks[arg].append(args.pop(0))
        else:
            roots.append(arg)
    sql_servers = [(server, marks["--sql-database"]) for server in marks["--sql-server"]]
    for spec in marks["--code-ext"]:
        try:
            add_code_extension(spec)
        except ValueError as e:
            print(e)
            sys.exit(2)

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
