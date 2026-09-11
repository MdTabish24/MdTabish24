import json
import os
import re
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
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL error: " + json.dumps(result["errors"]))
    return result["data"]


def fmt(number):
    return f"{number:,}"


def replace_once(text, pattern, replacement, label):
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"Could not update SVG field: {label}")
    return updated


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
    repositories(
      first: 100
      ownerAffiliations: OWNER
      privacy: PUBLIC
      isFork: false
    ) {
      totalCount
      nodes {
        stargazerCount
      }
    }
  }
}
"""

data = graphql(
    query,
    {
        "login": OWNER,
        "from": start.isoformat(),
        "to": now.isoformat(),
    },
)["user"]

collection = data["contributionsCollection"]
calendar = collection["contributionCalendar"]
days = [
    day
    for week in calendar["weeks"]
    for day in week["contributionDays"]
]
days.sort(key=lambda day: day["date"])

# Current streak: today may be zero while yesterday's streak is still active.
current_streak = 0
for day in reversed(days):
    if day["contributionCount"] > 0:
        current_streak += 1
    elif day["date"] == date.today().isoformat():
        continue
    else:
        break

# Longest streak in the fetched one-year contribution calendar.
longest_streak = 0
running = 0
for day in days:
    if day["contributionCount"] > 0:
        running += 1
        longest_streak = max(longest_streak, running)
    else:
        running = 0

stars = sum(repo["stargazerCount"] for repo in data["repositories"]["nodes"])

values = {
    "STARS": fmt(stars),
    "COMMITS": fmt(collection["totalCommitContributions"]),
    "PRS": fmt(collection["totalPullRequestContributions"]),
    "ISSUES": fmt(collection["totalIssueContributions"]),
    "CURRENT_STREAK": fmt(current_streak),
    "LONGEST_STREAK": fmt(longest_streak),
    "CONTRIBUTIONS": fmt(calendar["totalContributions"]),
    "REPO_COUNT": fmt(data["repositories"]["totalCount"]),
}

with open(SVG_PATH, "r", encoding="utf-8") as file:
    svg = file.read()

# These patterns target the labeled fields in the existing SVG, so unrelated
# numbers inside the embedded images, charts, paths, and icons are untouched.
svg = replace_once(
    svg,
    r'(Total Stars Earned</text>\s*<text[^>]*>)[^<]*(</text>)',
    rf'\g<1>{values["STARS"]}\g<2>',
    "stars",
)
svg = replace_once(
    svg,
    r'(Total Commits \(2025\)</text>\s*<text[^>]*>)[^<]*(</text>)',
    rf'\g<1>{values["COMMITS"]}\g<2>',
    "commits",
)
svg = replace_once(
    svg,
    r'(Total PRs</text>\s*<text[^>]*>)[^<]*(</text>)',
    rf'\g<1>{values["PRS"]}\g<2>',
    "pull requests",
)
svg = replace_once(
    svg,
    r'(Issues Contributed</text>\s*<text[^>]*>)[^<]*(</text>)',
    rf'\g<1>{values["ISSUES"]}\g<2>',
    "issues",
)
svg = replace_once(
    svg,
    r'(CONTRIBUTION STREAK</text>.*?<text[^>]*text-anchor="middle">)[^<]*(</text>\s*<text[^>]*>Current</text>)',
    rf'\g<1>{values["CURRENT_STREAK"]}\g<2>',
    "current streak",
)
svg = replace_once(
    svg,
    r'(CONTRIBUTION STREAK</text>.*?<text[^>]*text-anchor="middle">[^<]*</text>\s*<text[^>]*>Current</text>.*?<text[^>]*text-anchor="middle">)[^<]*(</text>\s*<text[^>]*>Longest</text>)',
    rf'\g<1>{values["LONGEST_STREAK"]}\g<2>',
    "longest streak",
)
svg = replace_once(
    svg,
    r'(GitHub Contributions.*?<text[^>]*>)[^<]*( Contributions on GitHub</text>)',
    rf'\g<1>{values["CONTRIBUTIONS"]}\g<2>',
    "contributions",
)
svg = replace_once(
    svg,
    r'(Public Repos</text>)',
    lambda m: m.group(1),
    "repo marker",
)
# Replace the number immediately before the existing "Public Repos" label.
svg, count = re.subn(
    r'(<text[^>]*>)[^<]*( Public Repos</text>)',
    rf'\g<1>{values["REPO_COUNT"]}\g<2>',
    svg,
    count=1,
)
if count != 1:
    raise RuntimeError("Could not update SVG field: public repositories")

with open(SVG_PATH, "w", encoding="utf-8", newline="") as file:
    file.write(svg)

print("Dashboard refreshed successfully")
for key, value in values.items():
    print(f"  {key}={value}")
