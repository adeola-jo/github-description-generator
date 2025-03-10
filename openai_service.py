import os
import logging
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            logger.error("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")
            raise ValueError("OpenAI API key is not set")

        try:
            self.client = OpenAI(api_key=self.api_key)
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            self.model = "gpt-4o"
        except OpenAIError as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise

    def generate_description(self, repo_name, repo_info, readme):
        prompt = f"""Given the following GitHub repository information, generate a clear and concise description (max 160 characters):

Repository Name: {repo_name}
Primary Language: {repo_info['language']}
Topics: {', '.join(repo_info['topics'])}
Files: {', '.join(repo_info['files'])}

README excerpt:
{readme[:1000] if readme else 'No README available'}

Please provide a JSON response in the format:
{{"description": "your generated description"}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a technical writer specializing in creating concise and informative GitHub repository descriptions."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=100
            )

            result = response.choices[0].message.content
            return result['description']

        except OpenAIError as e:
            logger.error(f"Failed to generate description for {repo_name}: {str(e)}")
            raise Exception(f"Failed to generate description: {str(e)}")