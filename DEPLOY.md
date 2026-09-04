# Putting Class Act online

For one teacher, on her own laptop, through a browser. Free.

Everything below is done in a browser. Nothing here needs a database — saving
is written and deliberately switched off, so there is no account to create and
nothing to pay for.

---

## Before you start

Nothing. The code is on GitHub already (`github.com/grafa166/class-act`),
uploaded 4 September 2026, and it is the current work rather than an old
version. You only need the GitHub account that owns it.

## 1. Create the app

1. Go to **share.streamlit.io** and sign in with the GitHub account that owns
   the repository.
2. **Create app** → **Deploy a public app from GitHub**.
3. Repository: `grafa166/class-act`. Branch: **`plan-mode`** — it will offer
   `main` by default, and `main` is the old version without the lesson
   planner, so you have to change this one. Main file path: **`app.py`**.
4. Don't click Deploy yet — open **Advanced settings** first and do step 2.

## 2. Put in the three settings

In **Advanced settings → Secrets**, paste these three lines, filling in your
own values:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
APP_PASSWORD = "something-you-give-only-to-her"
DAILY_WORKSHEET_LIMIT = "100"
```

What each one does:

| Setting | What it does | If you leave it out |
|---|---|---|
| `ANTHROPIC_API_KEY` | Pays for the AI that writes the lessons and worksheets | Nothing can be generated at all |
| `APP_PASSWORD` | The door. Nobody without it gets in | ⚠️ **The app is open to anyone with the link, and every visitor spends your money** |
| `DAILY_WORKSHEET_LIMIT` | The ceiling on worksheets per day | Defaults to 100 a day |

⚠️ **Set the password.** The address is public even though the app is not
listed anywhere, and without a password a stranger finding it can run up your
AI bill. This is the one setting that is not optional.

The daily ceiling is a cost guard rail, not an accounting record: it is held in
memory and starts again if the host restarts. That is deliberate.

## 3. Deploy

Click **Deploy**. First build takes a few minutes while it installs.

Then check three things yourself before sending her the link:

1. The password screen appears, and the password works.
2. Plan a short unit — two lessons is enough — and make a worksheet.
3. **Download the lesson plan, the worksheet and the answers**, and open them.
   That is the part that has never been checked on a Windows machine with real
   Word, and it is the thing she will actually use.

## 4. Send it to her

She needs the web address and the password. Nothing to install.

---

## Changing it later

Every push to the branch redeploys automatically, within a minute or two. The
settings above survive a redeploy; you only set them once.

## Things worth knowing

- **Nothing she makes is stored.** She plans a unit and downloads the files. If
  she closes the tab before downloading, that unit is gone. This was a decision,
  not an oversight — see the handover. If she asks for her units to be kept,
  saving is already written and tested and can be turned on.
- **No pupil data is held anywhere**, and there is nowhere in the app to put
  any.
- **The app sleeps when unused** and wakes on the next visit, which takes a few
  seconds. Streamlit's own behaviour; nothing to fix.
