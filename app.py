import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash
from github_service import GitHubService
from openai_service import OpenAIService

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Get the Replit URL for OAuth callback
REPLIT_URL = f"https://{os.environ.get('REPL_SLUG')}.{os.environ.get('REPL_OWNER')}.repl.co"
logger.info(f"Application URL: {REPLIT_URL}")

# Initialize services
github_service = GitHubService()
openai_service = OpenAIService()

@app.route('/')
def index():
    logger.debug("Accessing index route")
    return render_template('index.html')

@app.route('/auth/github')
def github_auth():
    logger.debug("Starting GitHub authentication")
    auth_url = github_service.get_auth_url()
    return redirect(auth_url)

@app.route('/callback')
def github_callback():
    logger.debug("Received GitHub callback")
    error = request.args.get('error')
    if error:
        error_description = request.args.get('error_description', 'Unknown error')
        logger.error(f"GitHub OAuth error: {error} - {error_description}")
        flash(f"GitHub authentication failed: {error_description}", 'danger')
        return redirect(url_for('index'))

    code = request.args.get('code')
    if not code:
        logger.error("No authorization code received from GitHub")
        flash('No authorization code received from GitHub', 'danger')
        return redirect(url_for('index'))

    try:
        logger.debug(f"Attempting to get access token with code: {code[:5]}...")
        access_token = github_service.get_access_token(code)
        session['github_token'] = access_token
        flash('Successfully authenticated with GitHub!', 'success')
        return redirect(url_for('repositories'))
    except Exception as e:
        logger.error(f"GitHub authentication error: {str(e)}")
        flash(f'Failed to authenticate with GitHub: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/repositories')
def repositories():
    if 'github_token' not in session:
        return redirect(url_for('index'))

    try:
        repos = github_service.get_repositories(session['github_token'])
        return render_template('repositories.html', repositories=repos)
    except Exception as e:
        logger.error(f"Error fetching repositories: {str(e)}")
        flash('Failed to fetch repositories', 'danger')
        return redirect(url_for('index'))

@app.route('/generate-descriptions', methods=['POST'])
def generate_descriptions():
    if 'github_token' not in session:
        return redirect(url_for('index'))

    try:
        selected_repos = request.form.getlist('repos')
        results = []

        for repo_name in selected_repos:
            repo_info = github_service.get_repository_info(session['github_token'], repo_name)
            description = openai_service.generate_description(
                repo_name,
                repo_info['content'],
                repo_info['readme']
            )
            github_service.update_repository_description(
                session['github_token'],
                repo_name,
                description
            )
            results.append({
                'name': repo_name,
                'description': description,
                'status': 'success'
            })

        flash('Successfully updated repository descriptions!', 'success')
        return render_template('repositories.html', 
                             repositories=github_service.get_repositories(session['github_token']),
                             results=results)

    except Exception as e:
        logger.error(f"Error generating descriptions: {str(e)}")
        flash('Failed to generate descriptions', 'danger')
        return redirect(url_for('repositories'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))