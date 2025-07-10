from github import Auth
from github import Github
from github import GithubIntegration
from urllib3.util.retry import Retry

class Repository:
  def authenticate(self, credentials):
    app_id = credentials.get('github_app_id', '')
    installation_id = credentials.get('github_app_installation_id', '')
    private_key = credentials.get('github_app_private_key', '')
    
    # Configure a retry strategy that respects GitHub's rate-limiting headers.
    # This will automatically wait and retry when a rate limit is encountered,
    # making the script robust against hitting the API limits.
    retry_strategy = Retry(
        total=10,
        backoff_factor=1,
        status_forcelist=[403, 500, 502, 503, 504],
        respect_retry_after_header=True
    )

    ## Use the Github personal access token for authentication
    ## Otherwise, use GitHub App authentication
    ## This is just a personal preference, either is fine.
    if 'github_token' in credentials and credentials['github_token']:
      return Github(credentials['github_token'], retry=retry_strategy)
    auth = Auth.AppAuth(app_id, private_key)
    gi = GithubIntegration(auth=auth)
    access_token = gi.get_access_token(installation_id).token
    return Github(access_token, retry=retry_strategy)

  def get_repos(self, credentials):
    g = self.authenticate(credentials)
    org_name = credentials.get('github_org')
    print(f"Fetching repository list for organization '{org_name}'... (This may take a moment)")
    org = g.get_organization(org_name)
    # Return the PaginatedList iterator directly. This defers the API calls
    # until the list is iterated over, preventing a large upfront burst of requests.
    paginated_repos = org.get_repos(type='all')
    # The .totalCount attribute gives the total number efficiently without fetching all objects.
    print(f"Found {paginated_repos.totalCount} repositories.")
    return paginated_repos
