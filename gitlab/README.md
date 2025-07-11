# GitLab Processing

This directory contains the GitLab equivalent of the GitHub repository processing functionality. It reads GitLab repositories and generates code.json files following the same format as the GitHub processing.

## Files

- `main.py` - Main entry point for GitLab processing (equivalent to `/main.py` for GitHub)
- `../src/gitlab/config.py` - Configuration management for GitLab credentials and settings
- `../src/gitlab/repository.py` - GitLab API authentication and repository fetching
- `../src/gitlab/sanitize.py` - Data sanitization and transformation to code.json format
- `../src/gitlab/client.py` - Legacy GitLab client (pre-existing)
- `../src/gitlab/cli.py` - Legacy CLI interface (pre-existing)

## Usage

### Environment Variables

Set these environment variables for GitLab processing:

```bash
# GitLab instance URL (optional, defaults to https://gitlab.com)
GL_URL=https://gitlab.com

# GitLab access token (required)
GL_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# GitLab group ID (optional, if not specified, fetches all accessible repos)
GL_GROUP_ID=12345

# Optional: SOCKS proxy for corporate networks
SOCKS_PROXY=socks5h://127.0.0.1:1080

# Optional: SSL verification (defaults to true)
VERIFY_SSL=true

# Output directory (optional, defaults to data/raw)
RAW_DATA_DIR=data/raw
```

### Command Line Usage

```bash
# From the /gitlab directory:

# Process all accessible repositories from GitLab.com
python main.py

# Process repositories from a specific GitLab group
python main.py --group-id 12345

# Process repositories from a custom GitLab instance
python main.py --url https://git.cdc.gov --group-id 456

# Use a SOCKS proxy for corporate networks
python main.py --socks-proxy socks5h://127.0.0.1:1080

# Disable SSL verification (for internal instances with self-signed certs)
python main.py --no-verify-ssl

# Limit processing for testing
python main.py --limit 10

# Specify output directory
python main.py --output /path/to/output

# Use more workers for faster processing
python main.py --workers 20
```

### Token Requirements

GitLab tokens should start with:
- `glpat-` (Personal Access Token)
- `gldt-` (Deploy Token)
- `glrt-` (Runner Token)

The token needs at least `read_repository` and `read_api` scopes.

## Features

- **Multi-instance support**: Works with GitLab.com, GitLab CE/EE, and corporate instances
- **Group-based processing**: Can process all repos in a specific group/subgroup
- **Proxy support**: Supports SOCKS proxies for corporate networks
- **SSL flexibility**: Can disable SSL verification for internal instances
- **Parallel processing**: Configurable number of worker threads
- **Data sanitization**: Follows the same business rules as GitHub processing
- **Error handling**: Robust error handling with detailed logging

## Output Format

The output follows the same code.json format as the GitHub processing, ensuring compatibility with existing analysis tools and dashboards.

## Migration from Legacy GitLab Code

The new GitLab processing (`main.py`) replaces the legacy `../src/gitlab/cli.py` and provides:

- Better error handling and logging
- Consistent structure with GitHub processing
- More configuration options
- Parallel processing capabilities
- Improved data sanitization

## Running from Different Locations

To run the GitLab processing from the project root:
```bash
python gitlab/main.py [arguments]
```

To run from within the gitlab directory:
```bash
cd gitlab
python main.py [arguments]
```

The script automatically adjusts the Python path to import the required modules from the `src/gitlab/` directory.
