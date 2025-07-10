from src.config import Config
from src.repository import Repository
from src.sanitize import Sanitizer

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys
import os
import json
import argparse

###############################################################
## The intention is to provide a simple interface to update
## us with existing repositories in a Github organization, and
## then sanitize the data to a common format such as code.json
## to provide the user with all of the known repositories.
###############################################################
def main():
  parser = argparse.ArgumentParser(description='Process GitHub organization')
  parser.add_argument('--output', help='Output directory path')
  parser.add_argument('--org', help='The GitHub organization to scan (overrides GH_ORG in .env)')
  parser.add_argument('--limit', type=int, help='Limit the number of repositories to process for testing')
  parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers to process repositories')
  args = parser.parse_args()

  now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
  print(f"Process starting: {now}", flush=True)

  config = Config()
  # Determine the target organization from the --org flag or the .env file
  org_name = args.org or os.environ.get('GH_ORG')
  if not org_name:
    print("Exiting: No GitHub organization specified. Use the --org flag or set GH_ORG in your .env file.", flush=True)
    sys.exit(1)

  credentials, errors = config.get_and_verify_credentials(org_name)
  if errors:
    print(f"Exiting due to configuration errors for organization '{org_name}':\n- " + "\n- ".join(errors), flush=True)
    sys.exit(1)

  print(f'Targeting GitHub organization: https://github.com/{org_name}', flush=True)
  if args.output:
    credentials['raw_data_dir'] = args.output
  elif credentials.get('raw_data_dir') == 'data/raw':
    credentials['raw_data_dir'] = str(Path(__file__).parent.absolute() / 'data/raw')
  print(f'Raw data directory: {credentials["raw_data_dir"]}', flush=True)
  repos = Repository().get_repos(credentials)

  repos_to_process = repos
  if args.limit:
    repos_to_process = repos[:args.limit]
    print(f"Limiting processing to the first {len(repos_to_process)} repositories.", flush=True)

  sanitizer = Sanitizer()
  sanitized_data = []

  print(f"Processing {len(repos_to_process)} repositories with up to {args.workers} workers...", flush=True)
  with ThreadPoolExecutor(max_workers=args.workers) as executor:
    future_to_repo = {executor.submit(sanitizer.get_repository_metadata, repo): repo for repo in repos_to_process}

    processed_count = 0
    total_repos = len(repos_to_process)
    for future in as_completed(future_to_repo):
      repo = future_to_repo[future]
      processed_count += 1
      try:
        data = future.result()
        if data:
          sanitized_data.append(data)
        print(f"[{processed_count}/{total_repos}] Successfully processed: {repo.full_name}")
      except Exception as exc:
        print(f"[{processed_count}/{total_repos}] Error processing {repo.full_name}: {exc}")

  output_dir = Path(credentials["raw_data_dir"])
  output_dir.mkdir(parents=True, exist_ok=True)
  output_file = output_dir / f"repo-{org_name}.json"
  print(f"\nWriting {len(sanitized_data)} processed repository records to {output_file}...")
  with open(output_file, 'w') as f:
    json.dump(sanitized_data, f, indent=2)
  print(f"Data saved to {output_file}")

  now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
  print(f"Completed processing at {now}")

if __name__ == "__main__":
  main()
