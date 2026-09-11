import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone

OWNER = os.environ.get("GITHUB_OWNER", "MdTabish24")
REPO = os.environ.get("GITHUB_REPO", "MdTabish24")
TOKEN = os.environ.get("GITHUB_TOKEN")
SVG_PATH = "dashborad.svg"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json",
    "User-Agent": "profile-dashboard-updater",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body, headers=HEADERS, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.load(r)
    if result.get("errors"):
        raise RuntimeError(json.dumps(result["errors"]))
    return result["data"]

def fmt(n):
    return f"{n:,}"

now = datetime.now(timezone.utc)
start = now - timedelta(days=365)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    login
    name
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes { stargazerCount }
    }
  }
}
"""

data = graphql(query, {
    "login": OWNER,
    "from": start.isoformat(),
    "to": now.isoformat(),
})["user"]

collection = data["contributionsCollection"]
calendar = collection["contributionCalendar"]
days = [d for w in calendar["weeks"] for d in w["contributionDays"]]
days.sort(key=lambda d: d["date"])

# Current streak. Today can be zero while yesterday's streak is still active.
current_streak = 0
for d in reversed(days):
    if d["contributionCount"] > 0:
        current_streak += 1
    elif d["date"] == date.today().isoformat():
        continue
    else:
        break

# Longest streak.
longest_streak = 0
running = 0
for d in days:
    if d["contributionCount"] > 0:
        running += 1
        longest_streak = max(longest_streak, running)
    else:
        running = 0

stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])

values = {
    "STARS": fmt(stars),
    "COMMITS": fmt(collection["totalCommitContributions"]),
    "PRS": fmt(collection["totalPullRequestContributions"]),
    "ISSUES": fmt(collection["totalIssueContributions"]),
    "CURRENT_STREAK": fmt(current_streak),
    "LONGEST_STREAK": fmt(longest_streak),
    "CONTRIBUTIONS": fmt(calendar["totalContributions"]),
    "REPO_COUNT": fmt(data["repositories"]["totalCount"]),
    "USERNAME": data["login"],
}

with open(SVG_PATH, "r", encoding="utf-8") as f:
    svg = f.read()

for key, value in values.items():
    svg = svg.replace("{{" + key + "}}", value)

with open(SVG_PATH, "w", encoding="utf-8", newline="") as f:
    f.write(svg)

print("Dashboard refreshed:")
for key, value in values.items():
    print(f"  {key}={value}")
