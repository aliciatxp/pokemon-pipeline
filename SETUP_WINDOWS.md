# Pokemon Card Pipeline — Windows Setup Guide

This guide walks you through setting up the pipeline on Windows.
You'll need about 20–30 minutes and a stable internet connection.

---

## What You'll Need (from the project owner)

Before starting, make sure you have these from the person who set up the project:

- [ ] Access to the GitHub repository
- [ ] A `credentials.json` file (Google service account key)
- [ ] The Google Sheet ID
- [ ] The Google Sheet tab name
- [ ] A Google AI Studio API key — or they may share theirs

---

## Step 1: Install Git

1. Go to https://git-scm.com/download/win
2. Download the installer and run it
3. Click **Next** through all steps — defaults are fine
4. Open **Command Prompt** (press `Win + R`, type `cmd`, press Enter)
5. Verify it worked:
   ```
   git --version
   ```
   You should see something like `git version 2.x.x`

---

## Step 2: Install Anaconda (Python + package manager)

1. Go to https://www.anaconda.com/download
2. Download the **Windows** installer (64-bit)
3. Run the installer → click through with defaults
4. ⚠️ When you see **"Add Anaconda to my PATH"** — check this box
5. Finish the installation
6. Close and reopen Command Prompt
7. Verify it worked:
   ```
   conda --version
   ```
   You should see something like `conda 24.x.x`

---

## Step 3: Clone the Repository

In Command Prompt, navigate to where you want the project to live.
For example, your Documents folder:

```
cd %USERPROFILE%\Documents
```

Then clone the repo (replace the URL with the one the owner gives you):

```
git clone https://github.com/OWNER_USERNAME/REPO_NAME.git
cd REPO_NAME
```

---

## Step 4: Create the Conda Environment

This installs Python and all required packages into an isolated environment:

```
conda create -n pokemon-pipeline python=3.11
conda activate pokemon-pipeline
pip install -r requirements.txt
```

You should see packages installing. This may take a few minutes.

> ⚠️ Every time you open a new Command Prompt to run the script,
> you need to run `conda activate pokemon-pipeline` first.

---

## Step 5: Add Your Secret Files

**credentials.json**
1. Take the `credentials.json` file the owner gave you
2. Copy it into the repo folder you just cloned (same folder as `main.py`)

**Create your .env file**
1. In the repo folder, find the file called `.env.example`
2. Make a copy of it and rename the copy to `.env`
   - In File Explorer: right-click → Copy → Paste → rename to `.env`
   - ⚠️ Windows may warn you about changing the file extension — click Yes
   - ⚠️ If you can't see file extensions: in File Explorer → View → check **File name extensions**, then rename
3. Open `.env` with Notepad (right-click → Open with → Notepad)
4. Fill in your values:

```
GOOGLE_AI_API_KEY=AIzaSy-your-key-here
GOOGLE_SHEET_ID=your_spreadsheet_id_here
GOOGLE_SHEET_TAB=Japan singles
GOOGLE_CREDENTIALS_FILE=credentials.json
```

5. Save and close Notepad

> 💡 The Sheet ID is the long string in the Google Sheet URL — just this part:
> `https://docs.google.com/spreadsheets/d/THIS_PART_HERE/edit`
> Do not include anything after the ID (no `/edit`, no `?gid=...`)

---

## Step 6: Test It (Dry Run)

A dry run parses and prints everything without writing anything to the sheet.
Always do this first to check everything looks right.

In Command Prompt (make sure you're in the repo folder):

```
conda activate pokemon-pipeline
python main.py "https://torecacamp-pokemon.com/.../orders/..." --dry-run
```

Replace the URL with a real order receipt URL.

You should see output like:
```
📦 Step 1: Scraping receipt...
   Found 27 row(s) → 25 card(s), 2 non-card row(s) skipped
💱 Step 2: Fetching Mastercard JPY→SGD rate (incl. 3.25% bank fee)...
🃏 Step 3: Parsing cards...
   [1] Pikachu ex | SV1a 025/078 | ¥680 → S$5.48
   ...
🧪 Dry run — skipping Google Sheets write.
```

---

## Step 7: Full Run

Once the dry run looks correct, run without `--dry-run` to write to the sheet:

```
python main.py "https://torecacamp-pokemon.com/.../orders/..."
```

---

## Choosing Visa or Mastercard Rate

By default the script uses the Mastercard exchange rate. To use Visa instead:

```
python main.py "https://torecacamp-pokemon.com/.../orders/..." --card visa
```

Both rates include a fixed 3.25% bank fee on top of the network rate.

---

## Day-to-Day Usage

Every time you want to use the script:

1. Open **Command Prompt**
2. Navigate to the project folder:
   ```
   cd %USERPROFILE%\Documents\REPO_NAME
   ```
3. Activate the environment:
   ```
   conda activate pokemon-pipeline
   ```
4. Dry run first:
   ```
   python main.py "YOUR_ORDER_URL_HERE" --dry-run
   ```
5. If it looks good, run without `--dry-run`

---

## Keeping Up to Date

When the owner pushes updates to the repo, pull them down with:

```
cd %USERPROFILE%\Documents\REPO_NAME
git pull
```

Your `.env` and `credentials.json` won't be affected — they're ignored by git.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `conda` is not recognized | Restart Command Prompt after installing Anaconda |
| `conda activate` doesn't work | Run `conda init cmd.exe` then restart Command Prompt |
| `No module named X` | Make sure you ran `conda activate pokemon-pipeline` before running the script |
| `credentials.json not found` | Make sure the file is in the same folder as `main.py` |
| `GOOGLE_AI_API_KEY not set` | Check your `.env` file — make sure it's named `.env` not `.env.txt` |
| `.env` won't rename properly | In File Explorer → View → check **File name extensions**, then rename |
| `403 Google Sheets` | Ask the project owner to reshare the sheet with the service account email |
| `No items found on receipt page` | You may need to be logged in to torecacamp — ask the owner for cookie instructions |
| Mastercard rate shows as Frankfurter fallback | Normal — Mastercard publishes rates with a 1–2 day lag |
