# size_codebase.py

This is an all-in-one inventory taker meant to deal with a large number of cases. It handles
codebases that are actually all in one file, such as those built with the Unity game engine or
with Microsoft Access, projects that have switched between multiple version control systems, and
codebases where libraries copied in from elsewhere sit among the owner's own code. It counts your
code by language and your version-control history (commits, contributors, pull requests), and
keeps engine code, plugins and third-party libraries out of your totals.

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

It only reads files and uploads nothing. The report holds counts and the names of folders,
languages and libraries: no source code and no author names. Please read it before you send it.
Point it at the real project, not a build or a ZIP download (a ZIP has no history), and if your
history is in Perforce, Plastic or SVN, run it inside your workspace while logged in so it can read
it. For code that mustn't leave your network, add `--offline`, which turns off every download and
server request.

For everything it handles and where it can go wrong, see [HOW_IT_WORKS.md](HOW_IT_WORKS.md). For
every connection it makes, every program it runs and how to verify your copy, see
[SECURITY.md](SECURITY.md).
