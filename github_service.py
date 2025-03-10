import os
import json
import urllib.request
import urllib.parse
import logging
from urllib.error import URLError

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        self.client_id = os.environ.get('GITHUB_CLIENT_ID')
        self.client_secret = os.environ.get('GITHUB_CLIENT_SECRET')
        self.redirect_uri = os.environ.get('GITHUB_REDIRECT_URI')
        self.api_base = 'https://api.github.com'

        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            logger.error("Missing GitHub OAuth credentials")
            raise ValueError("GitHub OAuth credentials not properly configured")

        logger.info(f"GitHub Service initialized with redirect URI: {self.redirect_uri}")

    def get_auth_url(self):
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'repo',
            'response_type': 'code'
        }
        auth_url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
        logger.debug(f"Generated GitHub auth URL with params: {params}")
        return auth_url

    def get_access_token(self, code):
        logger.debug("Attempting to get access token with code")
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

        try:
            req = urllib.request.Request(
                'https://github.com/login/oauth/access_token',
                data=data,
                headers=headers
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                if 'error' in result:
                    logger.error(f"GitHub OAuth error: {result.get('error_description', result['error'])}")
                    raise Exception(result.get('error_description', result['error']))
                logger.info("Successfully obtained GitHub access token")
                return result['access_token']
        except URLError as e:
            logger.error(f"Failed to get access token: {str(e)}")
            raise Exception(f"Failed to get access token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting access token: {str(e)}")
            raise

    def get_repositories(self, access_token):
        logger.debug("Fetching user repositories")
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Description-Generator'
        }

        req = urllib.request.Request(
            f'{self.api_base}/user/repos?type=owner&sort=updated',
            headers=headers
        )

        try:
            with urllib.request.urlopen(req) as response:
                repos = json.loads(response.read().decode())
                repos_data = [{
                    'name': repo['name'],
                    'full_name': repo['full_name'],
                    'description': repo.get('description', ''),
                    'url': repo['html_url'],
                    'language': repo.get('language', ''),
                    'stars': repo.get('stargazers_count', 0)
                } for repo in repos]
                logger.info(f"Successfully fetched {len(repos_data)} repositories")
                return repos_data
        except URLError as e:
            logger.error(f"Failed to fetch repositories: {str(e)}")
            raise Exception(f"Failed to fetch repositories: {str(e)}")

    def get_repository_info(self, access_token, repo_name):
        logger.debug(f"Fetching info for repository: {repo_name}")
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Description-Generator'
        }

        try:
            # Get repository metadata
            repo_url = f'{self.api_base}/repos/{repo_name}'
            repo_req = urllib.request.Request(repo_url, headers=headers)

            with urllib.request.urlopen(repo_req) as response:
                repo_data = json.loads(response.read().decode())

                # Get README content
                try:
                    readme_url = f'{repo_url}/readme'
                    readme_req = urllib.request.Request(readme_url, headers=headers)
                    with urllib.request.urlopen(readme_req) as readme_response:
                        readme_data = json.loads(readme_response.read().decode())
                        import base64
                        readme = base64.b64decode(readme_data['content']).decode('utf-8')
                except URLError:
                    logger.warning(f"README not found for {repo_name}")
                    readme = ''

                # Get repository contents
                try:
                    contents_url = f'{repo_url}/contents'
                    contents_req = urllib.request.Request(contents_url, headers=headers)
                    with urllib.request.urlopen(contents_req) as contents_response:
                        files = [item['name'] for item in json.loads(contents_response.read().decode())]
                except URLError:
                    logger.warning(f"Unable to fetch contents for {repo_name}")
                    files = []

                logger.info(f"Successfully fetched repository info for {repo_name}")
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
            logger.error(f"Failed to fetch repository info: {str(e)}")
            raise Exception(f"Failed to fetch repository info: {str(e)}")

    def update_repository_description(self, access_token, repo_name, description):
        logger.debug(f"Updating description for repository: {repo_name}")
        headers = {
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Description-Generator',
            'Content-Type': 'application/json'
        }

        data = json.dumps({'description': description}).encode()

        try:
            req = urllib.request.Request(
                f'{self.api_base}/repos/{repo_name}',
                data=data,
                headers=headers,
                method='PATCH'
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                logger.info(f"Successfully updated description for {repo_name}")
                return result
        except URLError as e:
            logger.error(f"Failed to update repository description: {str(e)}")
            raise Exception(f"Failed to update repository description: {str(e)}")