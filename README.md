# size_codebase.py

This is an all-in-one inventory taker meant to deal with a large number of cases. It handles
codebases that are actually all in one file, such as those built with the Unity game engine or
with Microsoft Access, projects that have switched between multiple version control systems, and
codebases where libraries copied in from elsewhere sit among the owner's own code. It counts your
code by language and your version-control history (commits, contributors, pull requests, reviews),
and keeps engine code, plugins and third-party libraries out of your totals. For a game, it also
says what the assets are (characters, items, props, levels in the build), which online services
the game uses, and whether there are automated tests and build automation.

## Running it

1. Install Python 3.8 or newer if you don't have it: https://www.python.org/downloads/ (Macs and
   Linux usually have it already).
2. Download [size_codebase.py](https://raw.githubusercontent.com/patinasource/size-codebase/main/size_codebase.py)
   and run it on your project folder:
   - Windows: double-click it, drag the project folder into the window that opens, and press
     Enter. Or, in Command Prompt: `py size_codebase.py "C:\path\to\your\project"`
   - macOS / Linux: `python3 size_codebase.py "/path/to/your/project"`
3. It saves `size_report_<folder>.txt` and `size_report_<folder>.json` next to the script. Send
   both to whoever asked you to run it.

It only reads files, uploads nothing and downloads nothing. The report holds counts and the names of folders,
languages and libraries (and of the online services and tools it recognises): no source code, no
author names, no file or class names and no web addresses. Please read it before you send it.
Point it at the real project, not a build or a ZIP download (a ZIP has no history), and if your
history is in Perforce, Plastic or SVN, run it inside your workspace while logged in so it can read
it. If your tests measure code coverage, run them with coverage turned on first: the script reads
the report they leave (it never runs your tests itself).

## Options

Most projects need none. The ones people reach for:

- **`--history "<folder or file>"`**: older history kept somewhere else, if the project moved
  between version-control systems (an old SVN dump or server folder, a mirror of a Bitbucket
  repository, a GitLab export, an old Perforce workspace). Give it once per place, or put them all
  in one folder and name that. Every history is put together with the project's, counting each
  change once however many times the project moved:

  ```
  python3 size_codebase.py "/path/to/project" --history "/path/to/old svn.dump" --history "/path/to/old-git-mirror"
  ```

- **`--third-party <folder>`** and **`--own <folder>`**: correct what it counts as someone
  else's code, or as yours.
- **`--offline`**: connect to no other computer at all.

[MANUAL.md](MANUAL.md) explains every option, with examples, and what the script saves and
connects to.

## More

For everything it handles and where it can go wrong, see [HOW_IT_WORKS.md](HOW_IT_WORKS.md). For
every connection it makes, every program it runs and how to verify your copy, see
[SECURITY.md](SECURITY.md). An AI security report is
[here](https://chatgpt.com/share/6ae6985c-c480-83e8-9194-97f42bfd1344) (GPT 6, Pro effort level, on
commit 2255998d, Oct 31st 2026).
