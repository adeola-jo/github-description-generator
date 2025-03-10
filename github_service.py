import os
import json
import urllib.request
import urllib.parse
from urllib.error import URLError

class GitHubService:
    def __init__(self):
        self.client_id = os.environ.get('GITHUB_CLIENT_ID')
        self.client_secret = os.environ.get('GITHUB_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('GITHUB_REDIRECT_URI')
        self.api_base = 'https://api.github.com'

    def get_auth_url(self):
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'repo'
        }
        return f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

    def get_access_token(self, code):
        data = urllib.parse.urlencode({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri
        }).encode()

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'GitHub-Description-Generator'
        }

        req = urllib.request.Request(
            'https://github.com/login/oauth/access_token',
            data=data,
            headers=headers
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                return result['access_token']
        except URLError as e:
            raise Exception(f"Failed to get access token: {str(e)}")

    def get_repositories(self, access_token):
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Description-Generator'
        }

        req = urllib.request.Request(
            f'{self.api_base}/user/repos?type=owner',
            headers=headers
        )

        try:
            with urllib.request.urlopen(req) as response:
                repos = json.loads(response.read().decode())
                return [{
                    'name': repo['full_name'].split('/')[1],
                    'description': repo.get('description', ''),
                    'url': repo['html_url'],
                    'language': repo.get('language', ''),
                    'stars': repo.get('stargazers_count', 0)
                } for repo in repos]
        except URLError as e:
            raise Exception(f"Failed to fetch repositories: {str(e)}")

    def get_repository_info(self, access_token, repo_name):
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Description-Generator'
        }

        # Get repository content
        repo_req = urllib.request.Request(
            f'{self.api_base}/repos/{repo_name}',
            headers=headers
        )

        # Get README content
        try:
            readme_req = urllib.request.Request(
                f'{self.api_base}/repos/{repo_name}/readme',
                headers=headers
            )
            with urllib.request.urlopen(readme_req) as response:
                readme_data = json.loads(response.read().decode())
                import base64
                readme = base64.b64decode(readme_data['content']).decode('utf-8')
        except URLError:
            readme = ''

        # Get repository content (files)
        try:
            content_req = urllib.request.Request(
                f'{self.api_base}/repos/{repo_name}/contents',
                headers=headers
            )
            with urllib.request.urlopen(content_req) as response:
                files = [item['name'] for item in json.loads(response.read().decode())]
        except URLError:
            files = []

        try:
            with urllib.request.urlopen(repo_req) as response:
                repo_data = json.loads(response.read().decode())
                return {
                    'content': {
                        'name': repo_data['name'],
                        'language': repo_data.get('language', ''),
                        'topics': repo_data.get('topics', []),
                        'files': files
                    },
                    'readme': readme
                }
        except URLError as e:
            raise Exception(f"Failed to fetch repository info: {str(e)}")

    def update_repository_description(self, access_token, repo_name, description):
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Description-Generator',
            'Content-Type': 'application/json'
        }

        data = json.dumps({'description': description}).encode()

        req = urllib.request.Request(
            f'{self.api_base}/repos/{repo_name}',
            data=data,
            headers=headers,
            method='PATCH'
        )

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except URLError as e:
            raise Exception(f"Failed to update repository description: {str(e)}")