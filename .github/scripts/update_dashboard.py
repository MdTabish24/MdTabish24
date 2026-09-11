import json
import os
import re
import urllib.request

OWNER = os.environ.get("GITHUB_OWNER", "MdTabish24")
REPO = os.environ.get("GITHUB_REPO", "MdTabish24")
TOKEN = os.environ.get("GITHUB_TOKEN")
SVG_PATH = "dashborad.svg"

API = f"https://api.github.com/repos/{OWNER}/{REPO}"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "profile-dashboard-updater",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def get_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


repo = get_json(API)
user = get_json(f"https://api.github.com/users/{OWNER}")

values = {
    "REPO_COUNT": str(user.get("public_repos", 0)),
    "FOLLOWERS": str(user.get("followers", 0)),
    "FOLLOWING": str(user.get("following", 0)),
    "BIO": user.get("bio") or "",
    "LOCATION": user.get("location") or "",
    "REPO_STARS": str(repo.get("stargazers_count", 0)),
    "PROFILE_UPDATED": user.get("updated_at", ""),
}

with open(SVG_PATH, "r", encoding="utf-8") as f:
    svg = f.read()

# Replace explicit dynamic tokens such as {{FOLLOWERS}} in the SVG.
for key, value in values.items():
    svg = svg.replace("{{" + key + "}}", value)

with open(SVG_PATH, "w", encoding="utf-8", newline="") as f:
    f.write(svg)

print("Dashboard values refreshed:", ", ".join(f"{k}={v}" for k, v in values.items()))
