import requests
import json

# AWX credentials and URL
awx_url = 'https://aap-aap.apps.platform-sts.pcbk.p1.openshiftapps.com/'
awx_username = 'admin'
awx_password = 'qK8W2v8eudQopNDsFrqmwdGoTBou262y'

# Replace with your YAML file path, inventory ID, and project ID in AWX
yaml_file_path = 'test.yaml'
inventory_id = 4
project_id = 10

# Initialize session
session = requests.Session()
session.auth = (awx_username, awx_password)

# Step 1: Get CSRF token by making a request to /api/
csrf_response = session.get(f"{awx_url}/api/")
if 'csrftoken' in csrf_response.cookies:
    csrf_token = csrf_response.cookies['csrftoken']
    session.headers.update({
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token,
        'Referer': awx_url  # Required to pass CSRF verification
    })
else:
    print("Failed to retrieve CSRF token")
    exit(1)

# Step 2: Create Job Template
job_template_data = {
        "name": "new_mariadb_template",
        "description": "",
        "job_type": "run",
        "inventory": 3,
        "project": 10,
        "playbook": "playbooks/mysql_install_start.yaml",
        "scm_branch": "",
        "forks": 0,
        "limit": "",
        "verbosity": 0,
        "extra_vars": "---",
        "job_tags": "",
        "force_handlers": False,
        "skip_tags": "",
        "start_at_task": "",
        "timeout": 0,
        "use_fact_cache": False,
        "organization": 1,
        "execution_environment": None,
        "host_config_key": "",
        "ask_scm_branch_on_launch": False,
        "ask_diff_mode_on_launch": False,
        "ask_variables_on_launch": False,
        "ask_limit_on_launch": False,
        "ask_tags_on_launch": False,
        "ask_skip_tags_on_launch": False,
        "ask_job_type_on_launch": False,
        "ask_verbosity_on_launch": False,
        "ask_inventory_on_launch": False,
        "ask_credential_on_launch": False,
        "ask_execution_environment_on_launch": False,
        "ask_labels_on_launch": False,
        "ask_forks_on_launch": False,
        "ask_job_slice_count_on_launch": False,
        "ask_timeout_on_launch": False,
        "ask_instance_groups_on_launch": False,
        "survey_enabled": False,
        "become_enabled": True,
        "diff_mode": False,
        "allow_simultaneous": False,
        "custom_virtualenv": None,
        "job_slice_count": 1,
        "webhook_service": "",
        "webhook_credential": None,
        "prevent_instance_group_fallback": False,
        "credentials": [4]
    }
response = session.post(f"{awx_url}/api/v2/job_templates/", data=json.dumps(job_template_data))
if response.status_code == 201:
    job_template = response.json()
    print("Job Template created:", job_template)
else:
    print("Failed to create Job Template:", response.status_code, response.text)