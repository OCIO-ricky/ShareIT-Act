import sys
import os
# Add the parent directory to Python path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.gitlab.config import GitlabConfig
from src.gitlab.repository import GitlabRepository
from src.gitlab.sanitize import GitlabSanitizer

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import itertools
from pathlib import Path
import json
import argparse

###############################################################
## The intention is to provide a simple interface to update
## us with existing repositories in a GitLab instance/group, and
## then sanitize the data to a common format such as code.json
## to provide the user with all of the known repositories.
###############################################################
def main():
    parser = argparse.ArgumentParser(description='Process GitLab instance/group')
    parser.add_argument('--output', help='Output directory path')
    parser.add_argument('--url', help='GitLab instance URL (overrides GL_URL in .env)', default='https://gitlab.com')
    parser.add_argument('--group-id', help='GitLab group ID (overrides GL_GROUP_ID in .env)')
    parser.add_argument('--limit', type=int, help='Limit the number of repositories to process for testing')
    parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers to process repositories')
    parser.add_argument('--socks-proxy', help='SOCKS proxy URL (e.g., socks5h://127.0.0.1:1080)')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    args = parser.parse_args()

    now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    print(f"GitLab process starting: {now}", flush=True)

    config = GitlabConfig()
    
    # Determine the target GitLab URL and group from args or env
    gitlab_url = args.url or os.environ.get('GL_URL', 'https://gitlab.com')
    group_id = args.group_id or os.environ.get('GL_GROUP_ID')

    credentials, errors = config.get_and_verify_credentials(gitlab_url, group_id)
    if errors:
        print(f"Exiting due to configuration errors for GitLab instance '{gitlab_url}':\n- " + "\n- ".join(errors), flush=True)
        sys.exit(1)

    # Add proxy and SSL settings from args
    if args.socks_proxy:
        credentials['socks_proxy'] = args.socks_proxy
    if args.no_verify_ssl:
        credentials['verify_ssl'] = False

    print(f'Targeting GitLab instance: {gitlab_url}', flush=True)
    if group_id:
        print(f'Targeting GitLab group ID: {group_id}', flush=True)
    else:
        print('Fetching all accessible repositories', flush=True)

    if args.output:
        credentials['raw_data_dir'] = args.output
    elif credentials.get('raw_data_dir') == 'data/raw':
        credentials['raw_data_dir'] = str(Path(__file__).parent.parent.parent.absolute() / 'data/raw')
    print(f'Raw data directory: {credentials["raw_data_dir"]}', flush=True)

    # Get repos from GitLab
    repos_list = GitlabRepository().get_repos(credentials)
    
    repos_to_process = repos_list
    total_repos_to_process = len(repos_list)
    
    if args.limit:
        repos_to_process = repos_list[:args.limit]
        total_repos_to_process = len(repos_to_process)
        print(f"Limiting processing to the first {total_repos_to_process} repositories.", flush=True)

    sanitizer = GitlabSanitizer()
    sanitized_data = []

    print(f"Processing {total_repos_to_process} repositories with up to {args.workers} workers...", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_repo = {executor.submit(sanitizer.get_repository_metadata, repo): repo for repo in repos_to_process}

        processed_count = 0
        total_repos = total_repos_to_process
        for future in as_completed(future_to_repo):
            repo = future_to_repo[future]
            processed_count += 1
            try:
                data = future.result()
                if data:
                    sanitized_data.append(data)
                repo_name = getattr(repo, 'path_with_namespace', f'ID-{getattr(repo, "id", "unknown")}')
                print(f"[{processed_count}/{total_repos}] Successfully processed: {repo_name}")
            except Exception as exc:
                repo_name = getattr(repo, 'path_with_namespace', f'ID-{getattr(repo, "id", "unknown")}')
                print(f"[{processed_count}/{total_repos}] Error processing {repo_name}: {exc}")

    output_dir = Path(credentials["raw_data_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create output filename based on GitLab URL and group
    safe_url = gitlab_url.replace("https://", "").replace("http://", "").replace("/", "-")
    if group_id:
        output_file = output_dir / f"repo-gitlab-{safe_url}-group-{group_id}.json"
    else:
        output_file = output_dir / f"repo-gitlab-{safe_url}.json"
    
    print(f"\nWriting {len(sanitized_data)} processed repository records to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(sanitized_data, f, indent=2)
    print(f"Data saved to {output_file}")

    now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    print(f"GitLab processing completed at {now}")

if __name__ == "__main__":
    main()
