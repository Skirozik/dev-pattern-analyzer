# dev-pattern-analyzer

A CLI tool that quantifies developer behavior from Git history — commit cadence, file churn, bug-fix concentration, and risk scoring.

## What it produces

- **Commit statistics** — files changed, lines added/removed, averages per commit
- **File churn ranking** — which files get touched most across the repo's lifetime
- **Fix-commit concentration** — which files appear most in `fix`/`bug`/`hotfix` commits (high signal for fragile code)
- **Risk score** — composite score weighting fix involvement 3x heavier than general churn
- **Time patterns** — most active hours and days of the week
- **AI interpretation** — optional GPT-4o-mini summary that reads the numbers and explains what they mean

## Example output

```
=== Developer Pattern Analyzer Report ===
Commits analyzed:        84
Total lines added:       12,430
Total lines removed:     4,891
Avg files changed:       2.14
Fix-like commits found:  11
Fix ratio:               13.1%

--- Risk score (churn + fix involvement) ---
src/auth/session.py  → churn=9, fixes=4, risk=21
src/api/routes.py    → churn=14, fixes=2, risk=20
db/migrations/       → churn=6, fixes=3, risk=15

--- Time patterns ---
Most active hours: 22:00 (18), 23:00 (14), 20:00 (11)
Most active days:  Sun (22), Sat (19), Mon (13)
```

## Usage

```bash
# Basic analysis
python src/main.py analyze /path/to/repo

# Filter to a specific author
python src/main.py analyze /path/to/repo --author "Jane Doe"

# Show top 10 files instead of 5
python src/main.py analyze /path/to/repo --top 10

# Export raw data as JSON
python src/main.py analyze /path/to/repo --json report.json

# Add AI interpretation (requires OPENAI_API_KEY)
python src/main.py analyze /path/to/repo --explain
```

## Setup

```bash
git clone https://github.com/Skirozik/dev-pattern-analyzer.git
cd dev-pattern-analyzer
pip install -r requirements.txt
```

For AI interpretation, set your OpenAI key:

```bash
cp .env.example .env
# add: OPENAI_API_KEY=your_key_here
```

## Risk scoring

Files are scored as:

```
risk = churn + (3 × fix_commits)
```

Fix-commit involvement is weighted 3x because repeated fixes to the same file are a stronger signal of instability than general edits. Files with high churn but low fix involvement are likely active development; files with high fix involvement relative to churn are candidates for refactoring.

## Dependencies

- `gitpython` — Git repository traversal
- `openai` — Optional AI interpretation
- `python-dotenv` — Environment variable loading

## License

MIT
