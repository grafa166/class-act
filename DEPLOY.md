# Putting Class Act online

For one teacher, on her own laptop, through a browser. Free.

Everything below is done in a browser. Nothing here needs a database — saving
is written and deliberately switched off, so there is no account to create and
nothing to pay for.

---

## Before you start

Nothing. The code is on GitHub already (`github.com/grafa166/class-act`), on
the ordinary `main` branch as of 4 September 2026, and it is the current work
rather than an old version.

⚠️ **There may already be a Class Act app in your account.** A note in this
repository from 31 August refers to a live address, `class-act.streamlit.app`.
Whether it is still there cannot be checked from outside — an app name that
has never existed responds identically — so **look at your workspace first**:

- **If an app is already listed**, you do not need section 1 at all. It reads
  from `main`, so it will pick the lesson planner up on its own within a
  minute or two. Go straight to section 2 and check its settings, because a
  password set for the old worksheet-only version may not exist at all.
- **If there is no app**, start at section 1.

## 1. Create the app

1. Go to **share.streamlit.io** and sign in. **Continue with Google** using
   `grafa16@gmail.com` is fine — it does not have to be GitHub.
2. Whichever way you sign in, it will ask to **connect your GitHub account**
   before it can see the repository. That step is required even for people who
   signed in with GitHub in the first place, so it is not a sign anything has
   gone wrong. The repository is public, so it only asks for ordinary access —
   it does not need the permissions a private repository would.
3. **Create app** → **Deploy a public app from GitHub**.
4. Repository: `grafa166/class-act`. Branch: **`main`** — which is what it
   offers by default, so there is nothing to change. Main file path:
   **`app.py`**.
5. Don't click Deploy yet — open **Advanced settings** first and do section 2.

⚠️ **The branch is not a setting you can edit later.** Streamlit identifies an
app by its owner, repository, branch and file, and changing any of them means
deleting the app and building it again. Worse, renaming or deleting the branch
*without* deleting the app first permanently costs you the ability to
administer or even delete it. This is why the work was put on `main`: it is
the one branch that is never going to move.

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
AI bill. This is the one setting that is not optional. The app itself has no
accounts and no email — one shared password is the whole door, so it is the
only thing standing between a passer-by and your bill.

⚠️ **The password is not written down in here, and must not be.** This
repository is public, so anything in it is readable by anyone. The password
was given to you separately; keep it somewhere private and paste it straight
into the Secrets box. Same for the API key.

It is compared exactly, so it is case-sensitive and spaces count. Paste it
rather than retyping it, both here and when you give it to her.

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
