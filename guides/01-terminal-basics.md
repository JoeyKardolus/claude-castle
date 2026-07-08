# Guide 01: Terminal basics

The terminal is a window where you type instructions to your computer instead of clicking. It looks intimidating. It is actually just a chat box for your computer, and Claude will be doing most of the typing anyway. You only need to know how to open it and six small things.

## Opening a terminal

### On a Mac

1. Press `Cmd + Space` to open Spotlight search.
2. Type `Terminal` and press Enter.

**You should see:** a window with some text and a blinking cursor, ending in something like `yourname@MacBook ~ %`. That line is called the prompt. It means "I am ready, type something."

### On Windows

Windows needs one extra step: we install a small Linux system inside Windows called WSL (Windows Subsystem for Linux). All the tools in this kit run best there.

1. Click the Start button, type `PowerShell`, right-click **Windows PowerShell**, choose **Run as administrator**. Click Yes if Windows asks for permission.
2. Copy this line, paste it into the blue window (right-click pastes), and press Enter:

```
wsl --install
```

3. Wait. It downloads Ubuntu (a version of Linux). This can take several minutes.
4. **Restart your computer** when it asks.
5. After the restart, a window called **Ubuntu** opens on its own (if not: Start menu, type `Ubuntu`, press Enter).
6. It asks you to create a username and password. Pick something short you will remember. **The password stays invisible while you type. That is normal. Type it and press Enter.**

**You should see:** a prompt ending in `$`, something like `dad@laptop:~$`.

From now on, "open a terminal" means: Mac people open Terminal, Windows people open Ubuntu.

## The six things you need to know

Try each one now. It helps to have done them once.

**1. `pwd` shows where you are.** Folders in a terminal are like folders in Finder or Explorer, you are always "in" one. Type `pwd` and press Enter. You should see a path like `/home/dad` or `/Users/dad`.

**2. `ls` lists what is here.** Type `ls` and press Enter. You should see the names of files and folders in your current folder (possibly nothing, if the folder is empty).

**3. `cd` moves you into a folder.** Type `cd Documents` to go into Documents, `cd ..` to go back up one level. Try `cd ..` then `pwd`: the path should be one step shorter.

**4. `Ctrl + C` is the emergency stop.** If something is running and you want it to stop, press `Ctrl` and `C` together. You get your prompt back. This never breaks anything.

**5. Up-arrow repeats.** Press the up-arrow key. Your previous command appears, ready to run again with Enter. Press up more times to go further back.

**6. Tab completes.** Type `cd Doc` and press the Tab key. The terminal finishes it to `cd Documents/` for you. If nothing happens, press Tab twice to see the options. Use this constantly, it prevents typos.

That is genuinely all. You do not need to memorise commands, Claude runs them for you. These six just let you look around and stay in control.

Next: [guide 02, install the tools](02-install-the-tools.md).
