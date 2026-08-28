import urllib.request
import urllib.parse
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout


class SourcingEngine:
    @staticmethod
    def _fetch_user_detail(item, title, skills, location):
        """Fetch a single GitHub user's detail. Returns a candidate dict or None."""
        try:
            user_url = item['url']
            user_req = urllib.request.Request(
                user_url,
                headers={'User-Agent': 'Protingent-ATS/2.0'}
            )
            user_resp = urllib.request.urlopen(user_req, timeout=4)
            user_data = json.loads(user_resp.read().decode('utf-8'))

            real_name = user_data.get('name') or item['login']
            company = (user_data.get('company') or 'Independent Developer').strip('@')
            loc = user_data.get('location') or location or 'Remote'
            bio = user_data.get('bio') or f'Experienced {title} developer.'

            # Years of experience from account creation date
            yrs_exp = 3
            created_at_str = user_data.get('created_at', '')
            if created_at_str:
                try:
                    created_year = int(created_at_str[:4])
                    yrs_exp = max(1, datetime.now().year - created_year)
                except Exception:
                    pass

            # Score based on real signals
            score = 70
            bio_lower = bio.lower()
            if any(s.lower() in bio_lower for s in skills):
                score += 12
            if title.lower().split()[0] in bio_lower:
                score += 5
            if len(bio) > 60:
                score += 5
            if user_data.get('public_repos', 0) > 10:
                score += 4
            if user_data.get('followers', 0) > 20:
                score += 4
            score = min(score, 99)

            email = user_data.get('email') or f"{item['login']}@github.local"
            hireable = user_data.get('hireable')
            avail = 'Open to offers' if hireable is None else ('Actively looking' if hireable else 'Not stated')

            return {
                'name': real_name,
                'title': title,
                'company': company,
                'loc': loc,
                'yrs': yrs_exp,
                'level': 'senior' if yrs_exp >= 6 else ('mid' if yrs_exp >= 3 else 'entry'),
                'avail': avail,
                'skills': skills[:6] if skills else ['Software Development'],
                'score': score,
                'email': email,
                'li': item['html_url'],
                'edu': 'See GitHub Profile',
                'about': bio[:300] if bio else f'GitHub developer with {user_data.get("public_repos", 0)} public repos.',
                'source': 'GitHub'
            }
        except Exception:
            return None

    @staticmethod
    def source_candidates(title, skills, location='Remote', num_results=12):
        """
        Source REAL candidates from GitHub API using parallel requests.
        Returns up to num_results real human profiles.
        """
        candidates = []

        # Pick best skill for GitHub search
        gh_skill_map = {
            'python': 'python', 'javascript': 'javascript', 'react': 'javascript',
            'node': 'javascript', 'java': 'java', 'go': 'go', 'ruby': 'ruby',
            'c++': 'cpp', 'rust': 'rust', 'typescript': 'typescript',
            'swift': 'swift', 'kotlin': 'kotlin', 'php': 'php',
            'aws': 'python', 'docker': 'python', 'kubernetes': 'go',
            'machine learning': 'python', 'data science': 'python',
            'devops': 'go', 'sql': 'python', 'mongodb': 'javascript',
        }

        lang = 'python'  # default
        title_lower = title.lower()
        for kw, mapped_lang in gh_skill_map.items():
            if kw in title_lower:
                lang = mapped_lang
                break
        for s in skills:
            s_lower = s.lower()
            if s_lower in gh_skill_map:
                lang = gh_skill_map[s_lower]
                break

        query = f'language:{lang} followers:>5'
        if location and location.lower() not in ['remote', 'any', '']:
            query += f' location:{urllib.parse.quote(location)}'

        url = (
            f'https://api.github.com/search/users'
            f'?q={urllib.parse.quote(query)}'
            f'&per_page={min(num_results + 8, 30)}'
            f'&sort=followers'
        )

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Protingent-ATS/2.0'})
            resp = urllib.request.urlopen(req, timeout=8)
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('items', [])
        except Exception as e:
            print(f'[SourcingEngine] GitHub search error: {e}')
            return []

        # Fetch user details in parallel for speed
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(SourcingEngine._fetch_user_detail, item, title, skills, location): item
                for item in items[:num_results + 5]
            }
            for future in as_completed(futures, timeout=12):
                if len(candidates) >= num_results:
                    break
                try:
                    result = future.result(timeout=5)
                    if result:
                        candidates.append(result)
                except Exception:
                    continue

        return candidates[:num_results]
