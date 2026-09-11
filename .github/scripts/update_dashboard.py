import json
import os
import urllib.request
from datetime import date

OWNER = os.environ.get("GITHUB_OWNER", "MdTabish24")
REPO = os.environ.get("GITHUB_REPO", "MdTabish24")
TOKEN = os.environ.get("GITHUB_TOKEN")

SVG_PATH = "dashborad.svg"

GRAPHQL_URL = "https://api.github.com/graphql"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json",
    "User-Agent": "profile-dashboard-updater",
    "X-GitHub-Api-Version": "2022-11-28",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def github_rest(url):
    req = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def github_graphql(query, variables=None):
    payload = {
        "query": query,
        "variables": variables or {}
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        GRAPHQL_URL,
        data=data,
        headers=HEADERS,
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)

    if "errors" in result:
        raise RuntimeError(
            "GitHub GraphQL error: " + json.dumps(result["errors"])
        )

    return result["data"]


# ---------------------------------------------------------
# BASIC PROFILE DATA
# ---------------------------------------------------------

user = github_rest(
    f"https://api.github.com/users/{OWNER}"
)

repo = github_rest(
    f"https://api.github.com/repos/{OWNER}/{REPO}"
)


# ---------------------------------------------------------
# GITHUB GRAPHQL DATA
# ---------------------------------------------------------

query = """
query($login: String!) {
  user(login: $login) {

    name
    login
    bio
    location

    followers {
      totalCount
    }

    following {
      totalCount
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
        forkCount
        name
        primaryLanguage {
          name
        }
      }
    }

    contributionsCollection {

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

  }
}
"""

data = github_graphql(
    query,
    {"login": OWNER}
)

github_user = data["user"]

repositories = github_user["repositories"]

contributions = github_user["contributionsCollection"]

calendar = contributions["contributionCalendar"]


# ---------------------------------------------------------
# CALCULATE STARS
# ---------------------------------------------------------

total_stars = 0

for repository in repositories["nodes"]:
    total_stars += repository["stargazerCount"]


# ---------------------------------------------------------
# CALCULATE CURRENT STREAK
# ---------------------------------------------------------

days = []

for week in calendar["weeks"]:
    for contribution_day in week["contributionDays"]:
        days.append(contribution_day)

days.sort(key=lambda x: x["date"])


today = date.today()

current_streak = 0

for contribution_day in reversed(days):

    contribution_date = date.fromisoformat(
        contribution_day["date"]
    )

    if contribution_day["contributionCount"] > 0:

        current_streak += 1

    else:

        # Allow today to be zero without breaking
        # yesterday's streak.
        if contribution_date == today:
            continue

        break


# ---------------------------------------------------------
# PROFILE VALUES
# ---------------------------------------------------------

repo_count = repositories["totalCount"]

followers = github_user["followers"]["totalCount"]

following = github_user["following"]["totalCount"]

commits = contributions["totalCommitContributions"]

prs = contributions["totalPullRequestContributions"]

issues = contributions["totalIssueContributions"]

contribution_count = calendar["totalContributions"]


# ---------------------------------------------------------
# FORMAT NUMBERS
# ---------------------------------------------------------

def format_number(number):
    return f"{number:,}"


values = {

    # Basic
    "REPO_COUNT": format_number(repo_count),
    "FOLLOWERS": format_number(followers),
    "FOLLOWING": format_number(following),

    # GitHub stats
    "STARS": format_number(total_stars),
    "REPO_STARS": format_number(total_stars),

    "COMMITS": format_number(commits),

    "PRS": format_number(prs),

    "ISSUES": format_number(issues),

    "CONTRIBUTIONS": format_number(contribution_count),

    "STREAK": format_number(current_streak),

    # Profile
    "NAME": github_user["name"] or OWNER,

    "USERNAME": github_user["login"],

    "BIO": github_user["bio"] or "",

    "LOCATION": github_user["location"] or "",

}


# ---------------------------------------------------------
# READ SVG
# ---------------------------------------------------------

with open(
    SVG_PATH,
    "r",
    encoding="utf-8"
) as file:

    svg = file.read()


# ---------------------------------------------------------
# REPLACE PLACEHOLDERS
# ---------------------------------------------------------

for key, value in values.items():

    placeholder = "{{" + key + "}}"

    svg = svg.replace(
        placeholder,
        value
    )


# ---------------------------------------------------------
# WRITE SVG
# ---------------------------------------------------------

with open(
    SVG_PATH,
    "w",
    encoding="utf-8",
    newline=""
) as file:

    file.write(svg)


print("")
print("========================================")
print(" GitHub Dashboard Updated")
print("========================================")
print(f"Repositories : {repo_count}")
print(f"Stars        : {total_stars}")
print(f"Commits      : {commits}")
print(f"Pull Requests: {prs}")
print(f"Issues       : {issues}")
print(f"Contributions: {contribution_count}")
print(f"Streak       : {current_streak}")
print(f"Followers    : {followers}")
print("========================================")
