#############
Configuration
#############

The dashboard needs Jira connection information. Create a local Streamlit
secrets file from the template:

.. code-block:: bash

   mkdir -p .streamlit
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml

Edit ``.streamlit/secrets.toml`` with your Jira server, email, and API token:

.. code-block:: toml

   [jira]
   JIRA_SERVER = "https://your-jira-instance"
   JIRA_EMAIL = "user@example.com"
   JIRA_API_TOKEN = "<api_token>"

The real ``.streamlit/secrets.toml`` file is ignored by git and should never be
committed.

Project-specific fields
=======================

The current Rubin deployment is optimized for the OBS Jira project and uses
OBS-specific fields for hierarchy and time-loss analysis. The application can
still connect to other Jira projects, but views that depend on those custom
fields may show reduced information until the project-specific mapping is moved
into configuration.
