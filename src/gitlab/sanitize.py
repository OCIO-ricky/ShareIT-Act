import base64
import re
import gitlab
from datetime import datetime, timezone
from gitlab.exceptions import GitlabGetError
from packaging.version import parse as parse_version, InvalidVersion

from src.gitlab.config import GitlabConfig

class GitlabSanitizer:
    """
    Sanitizes raw GitLab repository data into the code.json format
    by applying a set of business rules.
    """

    # --- Define Exemption Codes as Constants ---
    EXEMPT_BY_LAW = "exemptByLaw"
    EXEMPT_BY_NATIONAL_SECURITY = "exemptByNationalSecurity"
    EXEMPT_BY_AGENCY_SYSTEM = "exemptByAgencySystem"
    EXEMPT_BY_MISSION_SYSTEM = "exemptByMissionSystem"
    EXEMPT_BY_CIO = "exemptByCIO"

    VALID_EXEMPTION_CODES = [
        EXEMPT_BY_LAW, EXEMPT_BY_NATIONAL_SECURITY, EXEMPT_BY_AGENCY_SYSTEM,
        EXEMPT_BY_MISSION_SYSTEM, EXEMPT_BY_CIO,
    ]

    # --- Define Non-Code Languages ---
    NON_CODE_LANGUAGES = [
        'markdown', 'text', 'html', 'css', 'xml', 'yaml', 'json',
        'shell', 'batchfile', 'powershell', 'dockerfile', 'makefile', 'cmake',
        'tex', 'roff', 'csv', 'tsv'
    ]

    def __init__(self):
        """Initializes the Sanitizer with configuration and regex patterns."""
        self.config = GitlabConfig().get_app_config()
        self.email_regex = re.compile(r'[\w.+-]+@cdc\.gov')
        self.marker_regex_template = r'(?i)^\s*(?:{}):\s*(.*)$'

    def _get_gitlab_client(self, project):
        """Get GitLab client from project object."""
        return project.manager.gitlab

    def _get_file_content(self, project, file_path):
        """
        Fetches and decodes the content of a file from the GitLab repository.
        """
        try:
            file_obj = project.files.get(file_path=file_path, ref=project.default_branch)
            return base64.b64decode(file_obj.content).decode('utf-8', errors='ignore')
        except GitlabGetError:
            return None  # File not found is normal
        except Exception as e:
            print(f"Error fetching '{file_path}' for {project.path_with_namespace}: {e}")
            return None

    def _parse_marker(self, content, key):
        """Parse a text block for a specific "Key: Value" marker."""
        if not content:
            return None
        regex = re.compile(self.marker_regex_template.format(key), re.MULTILINE)
        match = regex.search(content)
        return match.group(1).strip() if match else None

    def _infer_organization(self, project, readme_content, tags):
        """Infer the organization based on README markers, tags, and project info."""
        # 1. README Marker (highest priority)
        org_from_marker = self._parse_marker(readme_content, 'Organization|Org')
        if org_from_marker:
            return org_from_marker

        org_acronyms = self.config.get('ORG_ACRONYMS', {})
        if not org_acronyms:
            return self.config.get('AGENCY_NAME', 'CDC')

        # 2. Search for acronyms in project topics/tags
        if tags:
            tags_lower = {tag.lower() for tag in tags}
            for acronym, full_name in org_acronyms.items():
                if acronym.lower() in tags_lower:
                    return acronym

        # 3. Search for acronyms in README content
        if readme_content:
            readme_lower = readme_content.lower()
            for acronym, full_name in org_acronyms.items():
                if re.search(r'\b' + re.escape(acronym.lower()) + r'\b', readme_lower):
                    return acronym

        # 4. Check project name and URL
        search_string = f"{project.name} {project.web_url} {project.path_with_namespace}".lower()
        for acronym, full_name in org_acronyms.items():
            acronym_lower = acronym.lower()
            if (f"{acronym_lower}-" in search_string or
                f"-{acronym_lower}" in search_string or
                f"/{acronym_lower}/" in search_string or
                search_string.endswith(f"/{acronym_lower}")):
                return acronym

        # 5. Default to agency name
        return self.config.get('AGENCY_NAME', 'CDC')

    def _infer_contact_email(self, project, readme_content, codeowners_content):
        """Infer contact email based on visibility, README, and CODEOWNERS."""
        if project.visibility == 'private':
            return self.config.get('PRIVATE_REPO_CONTACT_EMAIL', 'shareit@cdc.gov')

        # Public repository logic
        # 1. README Marker
        emails_from_marker_str = self._parse_marker(readme_content, 'Contact email')
        if emails_from_marker_str:
            emails = self.email_regex.findall(emails_from_marker_str)
            if emails:
                return ";".join(sorted(list(set(emails))))

        # 2. CODEOWNERS file
        if codeowners_content:
            emails = self.email_regex.findall(codeowners_content)
            if emails:
                return ";".join(sorted(list(set(emails))))

        # 3. Anywhere else in README
        if readme_content:
            emails = self.email_regex.findall(readme_content)
            if emails:
                return ";".join(sorted(list(set(emails))))

        # 4. Default
        return self.config.get('DEFAULT_CONTACT_EMAIL', 'cdcinfo@cdc.gov')

    def _infer_status(self, project, readme_content):
        """Infer the repository status."""
        # 1. Archived status from GitLab
        if project.archived:
            return "archived"

        # 2. Status marker in README
        status_from_readme = self._parse_marker(readme_content, 'Status')
        if status_from_readme:
            return status_from_readme.lower()

        # 3. Inactive check (no activity for over 2 years)
        if project.last_activity_at:
            try:
                from dateutil.parser import parse as parse_date
                last_activity = parse_date(project.last_activity_at)
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                if (now - last_activity).days > 730:
                    return "inactive"
            except Exception:
                pass

        # 4. Default status
        return "development"

    def _infer_version(self, project, readme_content):
        """Infer version from GitLab tags or README marker."""
        # 1. Scan tags for latest semantic version
        latest_version = None
        try:
            tags = project.tags.list(all=True)
            for tag in tags:
                try:
                    version_str = tag.name.lstrip('vV')
                    current_version = parse_version(version_str)
                    if not current_version.is_prerelease:
                        if latest_version is None or current_version > latest_version:
                            latest_version = current_version
                except InvalidVersion:
                    continue
        except Exception:
            pass

        if latest_version:
            return str(latest_version)

        # 2. README marker
        version_from_readme = self._parse_marker(readme_content, 'Version')
        if version_from_readme:
            return version_from_readme

        # 3. Default
        return "N/A"

    def _infer_usage_and_url(self, project, readme_content, languages):
        """Determine usageType, exemptionText, and repositoryURL."""
        # Public repositories
        if project.visibility == 'public':
            has_license = hasattr(project, 'license') and project.license
            usage_type = "openSource" if has_license else "governmentWideReuse"
            return usage_type, None, project.web_url

        # Private repositories
        # 1. Manual README marker
        exemption_type_from_marker = self._parse_marker(readme_content, 'Exemption')
        if exemption_type_from_marker and exemption_type_from_marker in self.VALID_EXEMPTION_CODES:
            justification = self._parse_marker(readme_content, 'Exemption justification')
            url = self.config.get('EXEMPTED_NOTICE_PDF_URL')
            return exemption_type_from_marker, justification, url

        # 2. Non-code check
        if not languages or all(lang.lower() in self.NON_CODE_LANGUAGES for lang in languages if lang):
            usage_type = self.EXEMPT_BY_CIO
            justification = "Repository contains no code or only non-code assets like documentation and configuration."
            url = self.config.get('EXEMPTED_NOTICE_PDF_URL')
            return usage_type, justification, url

        # 3. Default for private repos
        usage_type = "governmentWideReuse"
        url = self.config.get('INSTRUCTIONS_PDF_URL')
        return usage_type, None, url

    def _infer_description(self, project, readme_content):
        """Infer repository description."""
        # 1. Use GitLab description
        if project.description:
            return project.description.strip()

        # 2. Extract from README
        if readme_content:
            paragraphs = [p.strip() for p in readme_content.strip().split('\n\n') if p.strip()]
            if paragraphs:
                first_paragraph = re.sub(r'^\s*#+\s*', '', paragraphs[0])
                summary = ' '.join(first_paragraph.splitlines()).strip()
                return (summary[:250] + '...') if len(summary) > 253 else summary

        # 3. Default
        return ""

    def _get_private_id_prefix(self, project):
        """Get private ID prefix based on GitLab instance."""
        url = project.web_url.lower()
        if 'git.biotech.cdc.gov' in url:
            return 'gitlab-biotech'
        elif 'git.cdc.gov' in url:
            return 'gitlab-cdc'
        else:
            return 'gitlab'

    def get_repository_metadata(self, project_ref):
        """
        Process a GitLab project and return sanitized metadata.
        """
        try:
            # Get full project details
            if hasattr(project_ref, 'manager'):
                project = project_ref.manager.gitlab.projects.get(project_ref.id, lazy=False)
            else:
                project = project_ref
            
            # Skip forks if desired
            if hasattr(project, 'forked_from_project') and project.forked_from_project:
                print(f"Skipping forked repository: {project.path_with_namespace}")
                return None

            # Skip empty repositories
            if not hasattr(project, 'repository_tree'):
                print(f"Skipping repository without tree access: {project.path_with_namespace}")
                return None

            # Fetch file contents
            readme_content = self._get_file_content(project, 'README.md')
            if not readme_content:
                # Try other README variations
                for readme_name in ['README.rst', 'README.txt', 'README']:
                    readme_content = self._get_file_content(project, readme_name)
                    if readme_content:
                        break

            # Try to get CODEOWNERS
            codeowners_content = None
            for codeowners_path in ['CODEOWNERS', '.gitlab/CODEOWNERS', '.github/CODEOWNERS', 'docs/CODEOWNERS']:
                codeowners_content = self._get_file_content(project, codeowners_path)
                if codeowners_content:
                    break

            # Get languages
            languages = []
            try:
                lang_dict = project.languages()
                languages = list(lang_dict.keys()) if lang_dict else []
            except Exception:
                pass

            # Get topics/tags
            tags = getattr(project, 'topics', []) or []

            # Perform inferences
            description = self._infer_description(project, readme_content)
            usage_type, exemption_text, repository_url = self._infer_usage_and_url(project, readme_content, languages)
            status = self._infer_status(project, readme_content)
            organization = self._infer_organization(project, readme_content, tags)
            contact_email = self._infer_contact_email(project, readme_content, codeowners_content)
            version = self._infer_version(project, readme_content)

            # Assemble metadata
            metadata = {
                "name": project.name,
                "organization": organization,
                "description": description,
                "version": version,
                "status": status,
                "vcs": "git",
                "homepageURL": getattr(project, 'web_url', ''),
                "repositoryURL": repository_url,
                "repositoryVisibility": "private" if project.visibility == 'private' else "public",
                "languages": languages,
                "tags": tags,
                "contact": {
                    "email": contact_email
                },
                "date": {
                    "created": project.created_at if hasattr(project, 'created_at') else None,
                    "lastModified": project.last_activity_at if hasattr(project, 'last_activity_at') else None,
                    "metadataLastUpdated": datetime.now(timezone.utc).isoformat()
                },
                "permissions": {
                    "usageType": usage_type,
                    "licenses": []
                }
            }

            # Add license info if available
            if hasattr(project, 'license') and project.license:
                metadata["permissions"]["licenses"] = [{"name": project.license.get("name", "Unknown")}]

            # Add exemption text if present
            if exemption_text:
                metadata["permissions"]["exemptionText"] = exemption_text

            # Add private ID for private repos
            if project.visibility == 'private':
                prefix = self._get_private_id_prefix(project)
                metadata["privateID"] = f"{prefix}_{project.id}"

            return metadata

        except Exception as e:
            project_name = getattr(project_ref, 'path_with_namespace', f'ID-{getattr(project_ref, "id", "unknown")}')
            print(f"Failed processing GitLab repository {project_name}: {e}")
            import traceback
            traceback.print_exc()
            return None
