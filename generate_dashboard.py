import os
import json
import urllib.request
import datetime
from collections import defaultdict, Counter
import math

def fetch_graphql(query, token):
    url = 'https://api.github.com/graphql'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = json.dumps({'query': query}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def fetch_rest(endpoint, token):
    url = f'https://api.github.com{endpoint}'
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def generate_svg():
    token = os.environ.get('GH_TOKEN')
    if not token:
        print("GH_TOKEN environment variable not set.")
        return

    query = """
    query {
      user(login: "MdTabish24") {
        name
        followers { totalCount }
        createdAt
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          totalCount
          nodes {
            stargazerCount
            primaryLanguage { name }
            languages(first: 10) { edges { size, node { name, color } } }
          }
        }
        pullRequests(first: 1) { totalCount }
        issues(first: 1) { totalCount }
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { contributionCount, date } }
          }
          totalCommitContributions
        }
      }
    }
    """
    
    print("Fetching data from GitHub API...")
    data = fetch_graphql(query, token)['data']['user']
    
    # We can fetch events for hourly commits
    print("Fetching events...")
    events = fetch_rest('/users/MdTabish24/events?per_page=100', token)
    
    # Basic Stats
    total_stars = sum(r['stargazerCount'] for r in data['repositories']['nodes'])
    total_commits = data['contributionsCollection']['totalCommitContributions']
    prs = data['pullRequests']['totalCount']
    issues = data['issues']['totalCount']
    total_contributions = data['contributionsCollection']['contributionCalendar']['totalContributions']
    public_repos = data['repositories']['totalCount']
    
    # Dates
    created_at = datetime.datetime.strptime(data['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
    now = datetime.datetime.now()
    delta = now - created_at
    years = delta.days // 365
    joined_str = f"Joined GitHub {delta.days // 30} months ago" if years == 0 else (f"Joined GitHub 1 year ago" if years == 1 else f"Joined GitHub {years} years ago")
    current_year = now.year

    # Streak Calculation
    weeks = data['contributionsCollection']['contributionCalendar']['weeks']
    days = [day for week in weeks for day in week['contributionDays']]
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    for day in days:
        if day['contributionCount'] > 0:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            if day['date'] == today:
                break
            temp_streak = 0
    
    current_streak = 0
    for day in reversed(days):
        if day['date'] > today:
            continue
        if day['contributionCount'] > 0:
            current_streak += 1
        else:
            if day['date'] != today:
                break

    # Languages processing
    lang_repo = defaultdict(int)
    lang_size = defaultdict(int)
    lang_color = {}
    for r in data['repositories']['nodes']:
        if r['primaryLanguage']:
            name = r['primaryLanguage']['name']
            lang_repo[name] += 1
            if name not in lang_color: lang_color[name] = "#00d4ff" # default fallback
        for edge in r['languages']['edges']:
            name = edge['node']['name']
            lang_size[name] += edge['size']
            lang_color[name] = edge['node']['color'] or "#00d4ff"
            
    # Normalize colors for known languages if missing
    default_colors = {"Python": "#0ea5e9", "HTML": "#f97316", "TypeScript": "#38bdf8", "JavaScript": "#eab308", "Java": "#b07219", "C": "#9ca3af", "Jupyter Notebook": "#ea580c"}
    for k, v in default_colors.items():
        if k not in lang_color: lang_color[k] = v

    top_repo = dict(sorted(lang_repo.items(), key=lambda x: -x[1])[:5])
    top_size = dict(sorted(lang_size.items(), key=lambda x: -x[1])[:5])

    # 1. Top Languages Bar (Middle Panel)
    top_lang_bars_svg = ""
    y_text = 55
    y_rect = 45
    if top_size:
        max_size = list(top_size.values())[0]
        for lang, size in list(top_size.items())[:4]:
            width = int((size / max_size) * 150)
            color = lang_color.get(lang, '#ffffff')
            top_lang_bars_svg += f'''
            <text x="0" y="{y_text}" font-family="Inter, sans-serif" font-size="14" fill="#ffffff">{lang}</text>
            <rect x="100" y="{y_rect}" width="150" height="10" rx="5" fill="#2a313c"/>
            <rect x="100" y="{y_rect}" width="{width}" height="10" rx="5" fill="{color}"/>
            '''
            y_text += 40
            y_rect += 40

    def generate_donut(data_dict, title):
        svg = f'<text x="0" y="0" font-family="Inter, sans-serif" font-size="20" font-weight="600" fill="#61afef">{title}</text>\n'
        total = sum(data_dict.values())
        if total == 0: total = 1
        y_leg = 30
        dash_offset = 0
        circles_svg = ""
        for lang, count in data_dict.items():
            color = lang_color.get(lang, '#ffffff')
            # Legend
            svg += f'''
            <rect x="0" y="{y_leg}" width="12" height="12" fill="{color}"/>
            <text x="20" y="{y_leg+11}" font-family="Inter, sans-serif" font-size="12" fill="#00d4ff">{lang}</text>
            '''
            y_leg += 25
            
            # Circle
            pct = count / total
            dash = pct * 282.7
            circles_svg += f'<circle cx="0" cy="0" r="45" fill="none" stroke="{color}" stroke-width="25" stroke-dasharray="{dash} 282.7" stroke-dashoffset="{dash_offset}"/>\n'
            dash_offset -= dash
            
        svg += f'<g transform="translate(180, 100) rotate(-90)">\n{circles_svg}</g>'
        return svg

    donut_repo_svg = generate_donut(top_repo, "Top Languages by Repo")
    donut_size_svg = generate_donut(top_size, "Top Languages by Size")

    # Hourly Commits
    hours_counter = Counter()
    for event in events:
        if event['type'] == 'PushEvent':
            dt = datetime.datetime.strptime(event['created_at'], "%Y-%m-%dT%H:%M:%SZ")
            dt = dt + datetime.timedelta(hours=5, minutes=30)
            hours_counter[dt.hour] += 1
            
    max_commits = max(hours_counter.values()) if hours_counter else 1
    if max_commits < 10: max_commits = 10
    
    hourly_commits_svg = f'''
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="20" font-weight="600" fill="#61afef">Commits (UTC +5.50)</text>
    <line x1="15" y1="30" x2="15" y2="160" stroke="#00d4ff" stroke-width="1" opacity="0.5"/>
    <line x1="15" y1="160" x2="290" y2="160" stroke="#00d4ff" stroke-width="1" opacity="0.5"/>
    <text x="25" y="175" font-family="Fira Code, monospace" font-size="10" fill="#00d4ff" text-anchor="middle">0</text>
    <text x="85" y="175" font-family="Fira Code, monospace" font-size="10" fill="#00d4ff" text-anchor="middle">6</text>
    <text x="150" y="175" font-family="Fira Code, monospace" font-size="10" fill="#00d4ff" text-anchor="middle">12</text>
    <text x="215" y="175" font-family="Fira Code, monospace" font-size="10" fill="#00d4ff" text-anchor="middle">18</text>
    <text x="275" y="175" font-family="Fira Code, monospace" font-size="10" fill="#00d4ff" text-anchor="middle">23</text>
    <text x="280" y="195" font-family="Inter, sans-serif" font-size="10" fill="#00d4ff" text-anchor="end">per day hour</text>
    '''
    
    # Y-axis labels
    for i in range(6):
        val = int(max_commits * (5 - i) / 5)
        y_pos = 30 + i * 26
        hourly_commits_svg += f'<text x="10" y="{y_pos+5}" font-family="Fira Code, monospace" font-size="10" fill="#00d4ff" text-anchor="end">{val}</text>\n'

    hourly_commits_svg += '<g fill="#c678dd">\n'
    for h in range(24):
        val = hours_counter.get(h, 0)
        height = (val / max_commits) * 130
        if height < 1 and val > 0: height = 2
        y = 160 - height
        x = 20 + h * 11
        if height > 0:
            hourly_commits_svg += f'<rect x="{x}" y="{y}" width="8" height="{height}"/>\n'
    hourly_commits_svg += '</g>'

    # Area Chart
    weekly_contribs = [sum(d['contributionCount'] for d in w['contributionDays']) for w in weeks]
    max_weekly = max(weekly_contribs) if weekly_contribs else 1
    if max_weekly < 10: max_weekly = 10
    
    area_chart_svg = f'''
    <text x="450" y="20" font-family="Inter, sans-serif" font-size="12" fill="#00d4ff" text-anchor="end">contributions in the last year</text>
    <line x1="0" y1="210" x2="520" y2="210" stroke="#374151" stroke-width="2"/>
    <line x1="520" y1="30" x2="520" y2="210" stroke="#374151" stroke-width="2"/>
    '''
    
    # Y-axis labels
    for i in range(5):
        val = int(max_weekly * (4 - i) / 4)
        y_pos = 40 + i * 42.5
        area_chart_svg += f'<text x="530" y="{y_pos}" font-family="Fira Code, monospace" font-size="11" fill="#00d4ff">{val}</text>\n'

    # X-axis labels (months)
    num_weeks = len(weekly_contribs)
    # just plot ~7 labels
    for i in range(7):
        week_idx = int(i * (num_weeks - 1) / 6)
        x_pos = int(week_idx * (520 / (num_weeks - 1)))
        try:
            date_str = weeks[week_idx]['contributionDays'][0]['date']
            d_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            label = d_obj.strftime("%d/%m")
            area_chart_svg += f'<text x="{x_pos}" y="230" font-family="Fira Code, monospace" font-size="11" fill="#00d4ff" text-anchor="middle">{label}</text>\n'
        except IndexError:
            pass

    # Path generation
    points = []
    for i, val in enumerate(weekly_contribs):
        x = i * (520 / (num_weeks - 1))
        y = 210 - ((val / max_weekly) * 180)
        points.append((x, y))
        
    path_d = f"M {points[0][0]} {points[0][1]}"
    for i in range(1, len(points)):
        x0, y0 = points[i-1]
        x1, y1 = points[i]
        path_d += f" C {x0 + (x1-x0)/2} {y0}, {x1 - (x1-x0)/2} {y1}, {x1} {y1}"
        
    area_chart_svg += f'''
    <path d="{path_d} L 520 210 L 0 210 Z" fill="url(#purpleArea)"/>
    <path d="{path_d}" fill="none" stroke="#c678dd" stroke-width="3" stroke-linecap="round"/>
    '''

    # Load template and replace
    with open('dashboard_template.svg', 'r', encoding='utf-8') as f:
        svg_content = f.read()

    replacements = {
        '{{TOTAL_STARS}}': str(total_stars),
        '{{TOTAL_COMMITS}}': str(total_commits),
        '{{TOTAL_PRS}}': str(prs),
        '{{TOTAL_ISSUES}}': str(issues),
        '{{CURRENT_STREAK}}': str(current_streak),
        '{{LONGEST_STREAK}}': str(longest_streak),
        '{{TOTAL_CONTRIBUTIONS}}': f"{total_contributions:,}",
        '{{PUBLIC_REPOS}}': str(public_repos),
        '{{JOINED_GITHUB}}': joined_str,
        '{{CURRENT_YEAR}}': str(current_year),
        '{{TOP_LANGUAGES_BARS}}': top_lang_bars_svg,
        '{{DONUT_REPO}}': donut_repo_svg,
        '{{DONUT_SIZE}}': donut_size_svg,
        '{{HOURLY_COMMITS}}': hourly_commits_svg,
        '{{AREA_CHART}}': area_chart_svg
    }

    for k, v in replacements.items():
        svg_content = svg_content.replace(k, v)

    with open('dashborad.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
        
    print("dashborad.svg successfully generated!")

if __name__ == '__main__':
    generate_svg()
