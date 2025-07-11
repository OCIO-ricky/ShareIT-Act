import os
from dotenv import load_dotenv

load_dotenv()

class GitlabConfig:
    def get_app_config(self):
        """Returns application-specific configurations for GitLab."""
        return {
            'AGENCY_NAME': os.environ.get('AGENCY_NAME', 'CDC'),
            'DEFAULT_CONTACT_EMAIL': os.environ.get('DEFAULT_CONTACT_EMAIL', 'cdcinfo@cdc.gov'),
            'PRIVATE_REPO_CONTACT_EMAIL': os.environ.get('PRIVATE_REPO_CONTACT_EMAIL', 'shareit@cdc.gov'),
            'EXEMPTED_NOTICE_PDF_URL': os.environ.get(
                'EXEMPTED_NOTICE_PDF_URL',
                'https://cdcgov.github.io/ShareIT-Act/assets/files/code_exempted.pdf'
            ),
            'INSTRUCTIONS_PDF_URL': os.environ.get(
                'INSTRUCTIONS_PDF_URL',
                'https://cdcgov.github.io/ShareIT-Act/assets/files/instructions.pdf'
            ),
            'NON_CODE_LANGUAGES': [
                'markdown', 'text', 'html', 'css', 'shell', 'dockerfile', 'powershell'
            ],
            'ORG_ACRONYMS': {
                "od": "Office of the Director",
                "om": "Office of Mission Support", "ocoo": "Office of the Chief Operating Officer",
                "oadc": "Office of the Associate Directory of Communications",
                "ocio": "Office of the Chief Information Officer",
                "oed": "Office of Equal Employment Opportunity and Workplace Equity",
                "oga": "Office of Global Affairs", "ohs": "Office of Health Equity",
                "opa": "Office of Policy, Performance, and Evaluation",
                "ostlts": "Office of State, Tribal, Local and Territorial Support",
                "owcd": "Office of Women's Health and Health Equity",
                "cSELS": "Center for Surveillance, Epidemiology, and Laboratory Services",
                "csels": "Center for Surveillance, Epidemiology, and Laboratory Services",
                "ddphss": "Deputy Director for Public Health Science and Surveillance",
                "cgH": "Center for Global Health", "cgh": "Center for Global Health",
                "cid": "Center for Preparedness and Response", "cpr": "Center for Preparedness and Response",
                "ncezid": "National Center for Emerging and Zoonotic Infectious Diseases",
                "ncird": "National Center for Immunization and Respiratory Diseases",
                "nchhstp": "National Center for HIV, Viral Hepatitis, STD, and TB Prevention",
                "nccdphp": "National Center for Chronic Disease Prevention and Health Promotion",
                "nceh": "National Center for Environmental Health",
                "atsdr": "Agency for Toxic Substances and Disease Registry",
                "ncipc": "National Center for Injury Prevention and Control",
                "ncbddd": "National Center on Birth Defects and Developmental Disabilities",
                "nchs": "National Center for Health Statistics",
                "niosh": "National Institute for Occupational Safety and Health",
                "ddid": "Deputy Director for Infectious Diseases",
                "ddnidd": "Deputy Director for Non-Infectious Diseases",
                "cfa": "Center for Forecasting and Outbreak Analytics",
                "ophdst": "Office of Public Health Data, Surveillance, and Technology",
                "amd": "Office of Advanced Molecular Detection", 
                "oamd": "Office of Advanced Molecular Detection",  
                'cdc': 'Centers for Disease Control and Prevention',
            }
        }

    def _get_credentials_from_env(self, gitlab_url=None, group_id=None):
        """Get GitLab credentials from environment variables."""
        # Use GitLab URL domain as prefix for environment variables
        prefix = ""
        if gitlab_url:
            domain = gitlab_url.replace("https://", "").replace("http://", "").replace("/", "").replace(".", "_").upper()
            prefix = f"{domain}_"

        return {
            'raw_data_dir': os.environ.get('RAW_DATA_DIR', 'data/raw'),
            'gitlab_url': gitlab_url or os.environ.get('GL_URL', 'https://gitlab.com'),
            'gitlab_group_id': group_id or os.environ.get('GL_GROUP_ID'),
            'gitlab_token': os.environ.get(f'{prefix}GL_TOKEN', os.environ.get('GL_TOKEN', '')),
            'socks_proxy': os.environ.get('SOCKS_PROXY', ''),
            'verify_ssl': os.environ.get('VERIFY_SSL', 'true').lower() == 'true'
        }

    def _validate_credentials(self, creds):
        """Validates the provided GitLab credentials and returns a list of errors."""
        errors = []
        
        if not creds.get('gitlab_url'):
            errors.append("GitLab URL is not specified")
        
        if not creds.get('gitlab_token'):
            errors.append("GitLab token is required. Set GL_TOKEN environment variable")
        elif not creds['gitlab_token'].startswith(('glpat-', 'gldt-', 'glrt-')):
            errors.append("GitLab token appears to be invalid (should start with 'glpat-', 'gldt-', or 'glrt-')")

        return errors

    def get_and_verify_credentials(self, gitlab_url=None, group_id=None):
        """
        Gets and validates credentials for GitLab instance.
        Returns a tuple of (credentials, errors).
        """
        creds = self._get_credentials_from_env(gitlab_url, group_id)
        errors = self._validate_credentials(creds)
        return creds, errors
