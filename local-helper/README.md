# VisionCore Local Helper

A browser can't silently write files to `C:\`, and for most setups VisionCore's
backend runs on a server, not on your PC — so neither side of the app can save
a workbook to your local disk on its own. This is the small piece that closes
that gap: a tiny local program you run once, which the VisionCore web page
then talks to (over `127.0.0.1` only) whenever it wants to save a workbook to
your machine.

It is entirely optional. If it isn't running, VisionCore works exactly as
before — upload, extraction, editing, and the manual **Download** buttons are
completely unaffected either way.

## What it does

Once running, every tag automatically gets its own folder:

```
C:\Asset photo data capturing tool\<TAG NUMBER>-<DESCRIPTION>\
    AI Output.xlsx
    Template Output.xlsx
    Template Output Revision 1.xlsx
    Template Output Revision 2.xlsx
    ...
```

- Right after a tag's extraction finishes, `AI Output.xlsx` and
  `Template Output.xlsx` are saved once. Neither is ever overwritten.
- Every time you edit that tag and save it in VisionCore, a new
  `Template Output Revision N.xlsx` is added. Existing revisions are never
  touched — the full edit history stays on disk.

## Requirements

- Windows PC.
- [Python 3](https://www.python.org/downloads/) installed (the helper uses
  only Python's standard library — nothing to `pip install`).

## Running it

Double-click **`start_helper.bat`** in this folder. Leave the window open
while you use VisionCore — closing it just stops future auto-saves; nothing
else in the app is affected.

Or from a terminal:

```
python visioncore_local_helper.py
```

You should see:

```
VisionCore Local Helper listening on http://127.0.0.1:5577
Saving workbooks under: C:\Asset photo data capturing tool
```

### Run it automatically at Windows startup (optional)

Press `Win+R`, type `shell:startup`, press Enter, and drop a shortcut to
`start_helper.bat` into the folder that opens. It'll now start quietly each
time you log in.

## Configuration

All optional — set these as environment variables before launching if you
need to change them:

| Variable | Default | What it controls |
|---|---|---|
| `VISIONCORE_SAVE_ROOT` | `C:\Asset photo data capturing tool` | Where tag folders are created |
| `VISIONCORE_HELPER_PORT` | `5577` | The local port it listens on |
| `VISIONCORE_HELPER_TOKEN` | `visioncore-local-helper` | Shared secret the web page must present |

If you change `VISIONCORE_HELPER_TOKEN` or `VISIONCORE_HELPER_PORT`, update
the matching constants at the top of
`frontend/src/services/localHelper.ts` to match, and rebuild the frontend —
otherwise the web page won't be able to reach the helper anymore.

## Security notes

- The helper only listens on `127.0.0.1` (this machine), never your network —
  no other computer can reach it.
- Every request must carry the shared token above; requests without it are
  rejected.
- It only ever writes inside `VISIONCORE_SAVE_ROOT`, under a sanitised
  per-tag folder name — it cannot be made to write anywhere else on disk.
- It never overwrites `AI Output.xlsx`, `Template Output.xlsx`, or any
  existing `Template Output Revision N.xlsx` — only ever adds new files.
