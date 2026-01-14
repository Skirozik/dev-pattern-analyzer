import sys
import json
from git import Repo
import os
from openai import OpenAI



def analyze_repo(repo_path, target_author=None, top_n=5):
    repo = Repo(repo_path)
    commits = list(repo.iter_commits())

   
    if target_author:
        commits = [c for c in commits if str(c.author) == target_author]

    commit_data = []
    file_churn = {}
    fix_file_churn = {}  # filename -> times touched in "fix" commits
    fix_commit_count = 0
    hour_counts = {}
    weekday_counts = {}

                        

    for commit in commits:
        stats = commit.stats.total
        dt = commit.committed_datetime
        hour_counts[dt.hour] = hour_counts.get(dt.hour, 0) + 1
        weekday_counts[dt.weekday()] = weekday_counts.get(dt.weekday(), 0) + 1


        # Store commit-level stats
        commit_data.append({
            "hash": commit.hexsha[:7],
            "author": str(commit.author),
            "date": commit.committed_datetime,
            "message": commit.message.strip(),
            "files_changed": stats.get("files", 0),
            "lines_added": stats.get("insertions", 0),
            "lines_removed": stats.get("deletions", 0),
        })

        # Normal churn: count files touched in ANY commit
        for filename in commit.stats.files.keys():
            file_churn[filename] = file_churn.get(filename, 0) + 1

        # Fix churn: count files touched only in "fix-like" commits
        message_lower = commit.message.strip().lower()
        is_fix = any(word in message_lower for word in ["fix", "bug", "hotfix", "patch"])

        if is_fix:
            fix_commit_count += 1
            for filename in commit.stats.files.keys():
                fix_file_churn[filename] = fix_file_churn.get(filename, 0) + 1





    total_commits = len(commit_data)
    total_files_changed = sum(c["files_changed"] for c in commit_data)
    total_lines_added = sum(c["lines_added"] for c in commit_data)
    total_lines_removed = sum(c["lines_removed"] for c in commit_data)

    avg_files_per_commit = total_files_changed / total_commits if total_commits else 0
    avg_lines_added = total_lines_added / total_commits if total_commits else 0
    avg_lines_removed = total_lines_removed / total_commits if total_commits else 0

    top_files = sorted(file_churn.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_fix_files = sorted(fix_file_churn.items(), key=lambda x: x[1], reverse=True)[:top_n]

    all_files = set(file_churn.keys()) | set(fix_file_churn.keys())
    risk_rows = []
    for f in all_files:
        churn = file_churn.get(f, 0)
        fixes = fix_file_churn.get(f, 0)
        risk = churn + (3 * fixes)  # fixes weighted heavier than normal churn
        risk_rows.append({
            "file": f,
            "churn": churn,
            "fixes": fixes,
            "risk": risk
        })

    risk_rows.sort(key=lambda x: x["risk"], reverse=True)

    top_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    top_days = sorted(weekday_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    report = {
        "summary": {
            "commits_analyzed": total_commits,
            "total_files_changed": total_files_changed,
            "total_lines_added": total_lines_added,
            "total_lines_removed": total_lines_removed,
            "avg_files_changed": round(avg_files_per_commit, 2),
            "avg_lines_added": round(avg_lines_added, 2),
            "avg_lines_removed": round(avg_lines_removed, 2),
            "fix_like_commits": fix_commit_count,
            "fix_ratio_percent": round((fix_commit_count / total_commits) * 100, 1) if total_commits else 0.0,
        },
        "top_files_by_churn": [
            {"file": f, "commits_touched": n} for f, n in top_files
        ],
        "top_files_in_fixes": [
            {"file": f, "fix_commits": n} for f, n in top_fix_files
        ],
        "top_risk_files": risk_rows[:top_n],
        "time_patterns": {
            "top_hours": top_hours,
            "top_days": top_days,
        }
    }

    return report

def print_report(report):

    s = report["summary"]

    print("\n=== Developer Pattern Analyzer Report (MVP) ===")
    print(f"Commits analyzed:        {s['commits_analyzed']}")
    print(f"Total files changed:     {s['total_files_changed']}")
    print(f"Total lines added:       {s['total_lines_added']}")
    print(f"Total lines removed:     {s['total_lines_removed']}")

    print("\n--- Averages per commit ---")
    print(f"Avg files changed:       {s['avg_files_changed']:.2f}")
    print(f"Avg lines added:         {s['avg_lines_added']:.2f}")
    print(f"Avg lines removed:       {s['avg_lines_removed']:.2f}")

    print("\n--- Bug-fix stats ---")
    print(f"Fix-like commits found:  {s['fix_like_commits']}")
    print(f"Fix ratio:               {s['fix_ratio_percent']}%")

    print("\n--- Top files by churn (most frequently changed) ---")
    if not report["top_files_by_churn"]:
        print("No file churn data found.")
    else:
        for row in report["top_files_by_churn"]:
            print(f"{row['file']}  →  touched in {row['commits_touched']} commit(s)")

    print("\n--- Top files in fixes ---")
    if not report["top_files_in_fixes"]:
        print("No fix-related files detected yet.")
    else:
        for row in report["top_files_in_fixes"]:
            print(f"{row['file']}  →  involved in {row['fix_commits']} fix commit(s)")

    print("\n--- Risk score (churn + fix involvement) ---")
    for row in report["top_risk_files"]:
        print(f"{row['file']}  →  churn={row['churn']}, fixes={row['fixes']}, risk={row['risk']}")

    print("\n--- Time patterns ---")
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    top_hours = report["time_patterns"]["top_hours"]
    if top_hours:
        print("Most active hours: " + ", ".join([f"{h:02d}:00 ({c})" for h, c in top_hours]))
    else:
        print("Most active hours: N/A")

    top_days = report["time_patterns"]["top_days"]
    if top_days:
        print("Most active days:  " + ", ".join([f"{day_names[d]} ({c})" for d, c in top_days]))
    else:
        print("Most active days:  N/A")


def ai_explain(report):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️ AI explanation skipped (OPENAI_API_KEY not set)")
        return

    client = OpenAI(api_key=api_key)

    prompt = f"""
You are a senior software engineer analyzing a Git repository report.

Here is the analysis data (JSON):
{json.dumps(report, indent=2)}

Explain the following in clear, concise bullet points:
- What patterns stand out
- Which files look risky and why
- What the developer's working habits suggest
- Any high-level suggestions (no code)

Do NOT repeat raw numbers. Focus on insight.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You analyze developer behavior from git data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )

        explanation = response.choices[0].message.content

        print("\n=== AI Interpretation ===")
        print(explanation)

    except Exception as e:
        print("\n⚠️ AI explanation failed:", str(e))



def main():
    if len(sys.argv) < 3:
        print("Usage: python src/main.py analyze <repo_path> [--author NAME] [--top N] [--json OUT.json]")
        return

    command = sys.argv[1]
    repo_path = sys.argv[2]

    author = None
    top_n = 5
    json_out = None
    explain = False


    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--author":
            author = sys.argv[i + 1]
            i += 2
        elif arg == "--top":
            top_n = int(sys.argv[i + 1])
            i += 2
        elif arg == "--json":
            json_out = sys.argv[i + 1]
            i += 2
        elif arg == "--explain":
            explain = True
            i += 1
        else:
            print(f"Unknown flag: {arg}")
            print("Valid flags: --author NAME, --top N, --json OUT.json")
            return

    if command != "analyze":
        print("Unknown command. Supported command: analyze")
        return

    # ✅ RUN ANALYSIS ONCE
    report = analyze_repo(repo_path, author, top_n)

    # ✅ PRINT OUTPUT
    print_report(report)

    # ✅ OPTIONAL JSON EXPORT
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n✅ Wrote JSON report to: {json_out}")

    if explain:
        ai_explain(report)


if __name__ == "__main__":
    main()
