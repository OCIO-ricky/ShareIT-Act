import gitlab
import requests
from urllib3.util.retry import Retry

class GitlabRepository:
    def authenticate(self, credentials):
        """Authenticate with GitLab using the provided credentials."""
        gitlab_url = credentials.get('gitlab_url', 'https://gitlab.com')
        token = credentials.get('gitlab_token')
        socks_proxy = credentials.get('socks_proxy')
        verify_ssl = credentials.get('verify_ssl', True)
        
        # Set up session with proxy if needed
        session = None
        if socks_proxy:
            session = requests.Session()
            session.proxies = {
                'http': socks_proxy,
                'https': socks_proxy
            }
            session.verify = verify_ssl

            # Suppress InsecureRequestWarning if SSL verification is disabled
            if not verify_ssl:
                import urllib3
                urllib3.disable_warnings()

        # Create GitLab client
        gl = gitlab.Gitlab(gitlab_url, private_token=token, session=session, ssl_verify=verify_ssl)
        
        return gl

    def get_repos(self, credentials):
        """Get repositories from GitLab instance or group."""
        gl = self.authenticate(credentials)
        group_id = credentials.get('gitlab_group_id')
        
        if group_id:
            print(f"Fetching repository list for GitLab group ID '{group_id}'...")
            try:
                group = gl.groups.get(group_id)
                print(f"Found group: {group.name}")
                # Get all projects in the group including subgroups
                projects = group.projects.list(all=True, include_subgroups=True)
                print(f"Found {len(projects)} repositories in group.")
                return projects
            except Exception as e:
                print(f"Error fetching group {group_id}: {e}")
                return []
        else:
            print("Fetching all accessible repositories...")
            try:
                # Get all projects accessible to the user
                projects = gl.projects.list(all=True, membership=True)
                print(f"Found {len(projects)} accessible repositories.")
                return projects
            except Exception as e:
                print(f"Error fetching all repositories: {e}")
                return []
