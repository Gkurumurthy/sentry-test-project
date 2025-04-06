import os
import sys
import json
import base64
import logging
import requests
import argparse
from datetime import datetime, timedelta
from github import Github
import google.generativeai as genai
from typing import Dict, List, Optional, Tuple, Union, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sentry_agent.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("sentry_agent")

# Simple configuration helpers
def save_last_run_time(file_path="last_run.txt"):
    """Save the current time to a file"""
    try:
        with open(file_path, 'w') as f:
            f.write(datetime.now().isoformat())
        return True
    except Exception as e:
        logger.error(f"Error saving last run time: {e}")
        return False

def get_last_run_time(file_path="last_run.txt") -> Optional[datetime]:
    """Get the last run time from file if it exists"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                timestamp = f.read().strip()
                return datetime.fromisoformat(timestamp)
        return None
    except Exception as e:
        logger.error(f"Error reading last run time: {e}")
        return None

def load_config(config_file=None) -> Dict:
    """Load configuration from environment variables and optional config file"""
    config = {}
    
    # Load from config file if provided
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Environment variables take precedence
    config['SENTRY_TOKEN'] = os.environ.get("SENTRY_TOKEN", config.get('SENTRY_TOKEN', ''))
    config['SENTRY_ORG'] = os.environ.get("SENTRY_ORG", config.get('SENTRY_ORG', ''))
    config['SENTRY_PROJECT'] = os.environ.get("SENTRY_PROJECT", config.get('SENTRY_PROJECT', ''))
    config['GITHUB_TOKEN'] = os.environ.get("GITHUB_TOKEN", config.get('GITHUB_TOKEN', ''))
    config['GITHUB_REPO'] = os.environ.get("GITHUB_REPO", config.get('GITHUB_REPO', ''))
    config['GEMINI_API_KEY'] = os.environ.get("GEMINI_API_KEY", config.get('GEMINI_API_KEY', ''))
    
    return config

def validate_config(config: Dict) -> bool:
    """Validate that all required configuration values are set"""
    required_keys = ['SENTRY_TOKEN', 'SENTRY_ORG', 'SENTRY_PROJECT', 
                     'GITHUB_TOKEN', 'GITHUB_REPO', 'GEMINI_API_KEY']
    
    missing = [key for key in required_keys if not config.get(key)]
    
    if missing:
        logger.error(f"Missing required configuration values: {', '.join(missing)}")
        return False
    
    return True

class SentryClient:
    """Client for interacting with the Sentry API"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.base_url = "https://sentry.io/api/0"
        self.headers = {
            "Authorization": f"Bearer {config.get('SENTRY_TOKEN')}",
            "Content-Type": "application/json"
        }
    
    def get_recent_issues(self, limit: int = 10, since: Optional[datetime] = None) -> List[Dict]:
        """Fetch recent unresolved issues from Sentry without 'ai-fix-pr-raised' tag"""
        url = f"{self.base_url}/projects/{self.config.get('SENTRY_ORG')}/{self.config.get('SENTRY_PROJECT')}/issues/"
        
        # Only fetch issues that don't have our AI fix tag
        query = "is:unresolved !tags:ai-fix-pr-raised"
        
        params = {
            "query": query,
            "limit": limit
        }
        
        # Add time filter if 'since' is provided
        if since:
            # Format as ISO 8601
            params["start"] = since.isoformat()
        
        logger.info(f"Fetching issues from Sentry with params: {params}")
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            issues = response.json()
            logger.info(f"Fetched {len(issues)} issues from Sentry")
            return issues
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching issues from Sentry: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise
    
    def get_issue_details(self, issue_id: str) -> Dict:
        """Get detailed information about a specific issue"""
        url = f"{self.base_url}/issues/{issue_id}/events/latest/"
        
        try:
            logger.info(f"Fetching details for issue {issue_id}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching issue details: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise
    
    def add_comment(self, issue_id: str, comment: str) -> Dict:
        """Add a comment to an issue"""
        url = f"{self.base_url}/issues/{issue_id}/comments/"
        
        data = {
            "text": comment
        }
        
        try:
            logger.info(f"Adding comment to issue {issue_id}")
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding comment: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise
    
    def add_tag_to_issue(self, issue_id: str, tag_name: str, tag_value: str) -> bool:
        """Add a tag to an issue"""
        url = f"{self.base_url}/issues/{issue_id}/tags/"
        
        data = {
            "key": tag_name,
            "value": tag_value
        }
        
        try:
            logger.info(f"Adding tag {tag_name}:{tag_value} to issue {issue_id}")
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 204:  # No content response
                logger.info(f"Successfully added tag to issue {issue_id}")
                return True
            
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding tag to issue: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return False

class GitHubClient:
    """Client for interacting with the GitHub API"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.client = Github(config.get('GITHUB_TOKEN'))
        self.repo = self.client.get_repo(config.get('GITHUB_REPO'))
    
    def get_file_content(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Get the content of a file from GitHub"""
        try:
            logger.info(f"Fetching content for file {file_path}")
            file_content = self.repo.get_contents(file_path)
            content = base64.b64decode(file_content.content).decode('utf-8')
            return content, file_content.sha
        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return None, None
    
    def create_pull_request(self, file_path: str, content_sha: str, fixed_code: str, 
                           issue_details: Dict, explanation: str) -> str:
        """Create a GitHub PR with the fix"""
        try:
            # Create a new branch
            base_branch = self.repo.default_branch
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_branch_name = f"fix/sentry-{issue_details['id']}-{timestamp}"
            
            logger.info(f"Creating new branch {new_branch_name}")
            
            # Get the reference to the default branch
            ref = self.repo.get_git_ref(f"heads/{base_branch}")
            
            # Create new branch
            self.repo.create_git_ref(f"refs/heads/{new_branch_name}", ref.object.sha)
            
            # Update file in the new branch
            commit_message = f"Fix: {issue_details['title']} (Sentry ID: {issue_details['id']})"
            
            logger.info(f"Updating file {file_path} in branch {new_branch_name}")
            self.repo.update_file(
                path=file_path,
                message=commit_message,
                content=fixed_code,
                sha=content_sha,
                branch=new_branch_name
            )
            
            # Create pull request
            pr_title = f"🤖 [AI Fix] {issue_details['title']}"
            pr_body = f"""
## Automated fix for Sentry issue #{issue_details['id']}

### Issue Details
- **Error:** {issue_details['title']}
- **Sentry Link:** {issue_details['permalink']}
- **File:** {file_path}

### AI Explanation
{explanation}

---
*This PR was automatically generated by the Sentry AI Fix Agent*
            """
            
            logger.info(f"Creating pull request for branch {new_branch_name}")
            pr = self.repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=new_branch_name,
                base=base_branch
            )
            
            logger.info(f"Created PR: {pr.html_url}")
            return pr.html_url
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            raise

class GeminiClient:
    """Client for interacting with the Gemini API"""
    
    def __init__(self, config: Dict):
        self.config = config
        genai.configure(api_key=config.get('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
    
    def generate_fix(self, error_message: str, file_content: str, context_info: Dict) -> Dict:
        """Use Gemini to generate a fix"""
        if not context_info or not file_content:
            logger.warning("Missing context info or file content for generating fix")
            return None
        
        # Pre-join the context lines
        pre_context_text = "\n".join(context_info.get('pre_context', []))
        post_context_text = "\n".join(context_info.get('post_context', []))
        
        # Enhanced prompt with more context about the code base
        prompt = f"""
        You are an expert Python developer tasked with fixing a bug in a Django codebase.
        
        ERROR MESSAGE:
        {error_message}
        
        FILE: {context_info.get('file_path', 'unknown')}
        FUNCTION: {context_info.get('function', 'unknown')}
        LINE NUMBER: {context_info.get('line_number', 'unknown')}
        
        Here's the context of the error:
        
        Pre-context lines:
        ```python
        {pre_context_text}
        ```
        
        Line with error:
        ```python
        {context_info.get('context_line', '')}
        ```
        
        Post-context lines:
        ```python
        {post_context_text}
        ```
        
        Here's the full file content:
        ```python
        {file_content}
        ```
        
        Please provide a fix for this issue that is minimal and focused on the specific error.
        Explain what's causing the error and provide the corrected code.
        
        Return your response in the following format:
        
        EXPLANATION:
        [Explanation of the issue and your fix]
        
        FIXED_CODE:
        [The entire fixed file with your changes]
        """
        
        try:
            logger.info("Generating fix with Gemini")
            response = self.model.generate_content(prompt)
            ai_response = response.text
            
            # Extract the explanation and fixed code from the AI response
            try:
                explanation = ai_response.split("EXPLANATION:")[1].split("FIXED_CODE:")[0].strip()
                fixed_code = ai_response.split("FIXED_CODE:")[1].strip()
                
                # Remove the code block markers if present
                if fixed_code.startswith("```python"):
                    fixed_code = fixed_code[10:].strip()
                elif fixed_code.startswith("```"):
                    fixed_code = fixed_code[3:].strip()
                
                if fixed_code.endswith("```"):
                    fixed_code = fixed_code[:-3].strip()
                
                logger.info("Successfully generated fix")
                return {
                    "explanation": explanation,
                    "fixed_code": fixed_code
                }
            except Exception as e:
                logger.error(f"Error parsing AI response: {e}")
                logger.debug(f"Raw AI response: {ai_response}")
                return None
        except Exception as e:
            logger.error(f"Error generating AI fix: {e}")
            return None

def extract_stack_context(event_data: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Extract relevant code context from the stack trace"""
    try:
        # Extract the exception entry
        entries = event_data.get('entries', [])
        exception_entries = [e for e in entries if e.get('type') == 'exception']
        
        if not exception_entries:
            logger.warning("No exception entries found in event data")
            return None, None
        
        exception_entry = exception_entries[0]
        exception_values = exception_entry.get('data', {}).get('values', [])
        
        if not exception_values:
            logger.warning("No exception values found in event data")
            return None, None
        
        # Get the first exception (usually the one we care about)
        exception = exception_values[0]
        frames = exception.get('stacktrace', {}).get('frames', [])
        
        if not frames:
            logger.warning("No stack frames found in event data")
            return None, None
        
        # Find the frame where the exception occurred
        # We prioritize frames with 'in_app' flag set to True
        in_app_frames = [f for f in frames if f.get('in_app')]
        
        if in_app_frames:
            # Use the last in_app frame as it's typically the one that caused the error
            relevant_frame = in_app_frames[-1]
        else:
            # Fall back to the last frame if no in_app frames are found
            relevant_frame = frames[-1]
        
        file_path = relevant_frame.get('filename')
        line_number = relevant_frame.get('lineno')
        
        # Get context lines if available
        context_line = relevant_frame.get('context_line', '')
        pre_context = relevant_frame.get('pre_context', [])
        post_context = relevant_frame.get('post_context', [])
        
        return {
            'file_path': file_path,
            'line_number': line_number,
            'context_line': context_line,
            'pre_context': pre_context,
            'post_context': post_context,
            'function': relevant_frame.get('function', '')
        }, file_path
    except Exception as e:
        logger.error(f"Error extracting stack context: {e}")
        return None, None

def process_issue(issue: Dict, sentry_client: SentryClient, github_client: GitHubClient, 
                 gemini_client: GeminiClient) -> bool:
    """Process a single issue"""
    issue_id = issue['id']
    issue_title = issue['title']
    
    logger.info(f"Processing issue {issue_id}: {issue_title}")
    
    try:
        # Get detailed information about the issue
        issue_details = sentry_client.get_issue_details(issue_id)
        
        # Extract context information from the stack trace
        context_info, file_path = extract_stack_context(issue_details)
        
        if not context_info or not file_path:
            logger.warning(f"Could not extract context for issue {issue_id}")
            return False
        
        # Get the file content from GitHub
        file_content, content_sha = github_client.get_file_content(file_path)
        
        if not file_content:
            logger.warning(f"Could not get file content for {file_path}")
            return False
        
        # Generate a fix using AI
        fix_result = gemini_client.generate_fix(issue_title, file_content, context_info)
        
        if not fix_result:
            logger.warning(f"Could not generate fix for issue {issue_id}")
            return False
        
        # Create a PR with the fix
        try:
            pr_url = github_client.create_pull_request(
                file_path, 
                content_sha, 
                fix_result["fixed_code"], 
                {
                    "id": issue_id,
                    "title": issue_title,
                    "permalink": issue['permalink']
                }, 
                fix_result["explanation"]
            )
            
            logger.info(f"Created PR for issue {issue_id}: {pr_url}")
            
            # Add a comment to the Sentry issue
            comment = f"I've created a PR with a potential fix: {pr_url}"
            sentry_client.add_comment(issue_id, comment)
            
            # Add a tag to the issue in Sentry
            sentry_client.add_tag_to_issue(issue_id, "ai-fix-pr-raised", "true")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating PR for issue {issue_id}: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing issue {issue_id}: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Sentry AI Fix Agent")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of issues to process")
    parser.add_argument("--all", action="store_true", help="Process all unresolved issues")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    if not validate_config(config):
        logger.error("Invalid configuration")
        return 1
    
    # Get last run time (if not processing all issues)
    last_run = None if args.all else get_last_run_time()
    
    if last_run:
        logger.info(f"Processing issues since {last_run}")
    else:
        logger.info("Processing all unresolved issues")
    
    # Initialize clients
    sentry_client = SentryClient(config)
    github_client = GitHubClient(config)  
    gemini_client = GeminiClient(config)
    
    # Get recent issues
    try:
        issues = sentry_client.get_recent_issues(limit=args.limit, since=last_run)
    except Exception as e:
        logger.error(f"Failed to fetch issues: {e}")
        return 1
    
    if not issues:
        logger.info("No issues to process")
        return 0
    
    # Process each issue
    success_count = 0
    for issue in issues:
        if process_issue(issue, sentry_client, github_client, gemini_client):
            success_count += 1
    
    # Save the current time as the last run time
    save_last_run_time()
    
    logger.info(f"Processed {len(issues)} issues, {success_count} successful")
    return 0
