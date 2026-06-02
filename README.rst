#####################
jira-issues-dashboard
#####################

``jira-issues-dashboard`` is a Streamlit application for Jira issue triage and
operational awareness. It was developed for Rubin Observatory Observing
Operations workflows and is maintained in ``lsst-so`` as a uv-first Python
project.

The current application provides views for issue activity, aging and stale
tickets, personal workload, assignee and reporter patterns, and OBS hierarchy
drilldowns when the corresponding Jira fields are available.

Project structure and portability
=================================

The repository is organized so that Jira access, data preparation, analytics,
and Streamlit presentation can evolve separately:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Repository element
     - Role
   * - ``jira_app/core/``
     - Jira access, configuration, field mapping, normalization, enrichment,
       and workflow-status handling.
   * - ``jira_app/analytics/``
     - Reusable activity, aging, status-flow, hierarchy, assignee/reporter,
       and segment metrics.
   * - ``jira_app/features/``
     - View-specific context builders for pages such as Activity Overview and
       Personal View.
   * - ``jira_app/pages/``
     - Streamlit pages that present the operational views.
   * - ``jira_app/visual/`` and ``jira_app/columns.yaml``
     - Shared charts, tables, leaderboard components, column metadata, and
       display-column configuration.
   * - Streamlit secrets and setup page
     - Local Jira credentials and connection settings. Credentials are user
       supplied and are not stored in the repository.

The app is currently configured primarily for Rubin OBS workflows. Some
Rubin/OBS-specific field mappings, labels, and workflow assumptions still live
in the implementation. When adding support for another Jira project, prefer
placing project-specific behavior in configuration or mapping code rather than
embedding it directly in Streamlit pages. Future work should introduce explicit
project profiles or configuration files for these assumptions. Once that
profile system exists, this section should be updated with the supported
profile layout and the steps required to add a new Jira project.

Quick start
===========

Install uv by following the upstream instructions at https://docs.astral.sh/uv/.
Then clone the repository and create the local environment:

.. code-block:: bash

   git clone https://github.com/lsst-so/jira-issues-dashboard.git
   cd jira-issues-dashboard
   uv sync

Create a local Streamlit secrets file from the provided template:

.. code-block:: bash

   mkdir -p .streamlit
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml

Edit ``.streamlit/secrets.toml`` with your Jira server, email, and API token.
The real ``secrets.toml`` file is ignored by git.

Run the dashboard:

.. code-block:: bash

   uv run streamlit run run_dashboard.py

After Streamlit starts, open ``http://localhost:8501``.

Running with Docker
===================

The Dockerfile can be used to build and run the dashboard locally without
installing the application dependencies directly on your host machine.

First, create a local secrets file outside the repository:

.. code-block:: bash

   mkdir -p ~/.jira-issues-dashboard/.streamlit
   cp .streamlit/secrets.toml.example ~/.jira-issues-dashboard/.streamlit/secrets.toml

Then edit ``~/.jira-issues-dashboard/.streamlit/secrets.toml`` with your Jira
server, email, and API token.

Build the local runtime image from the repository root:

.. code-block:: bash

   docker build -t jira-issues-dashboard:latest .

Run the dashboard in the foreground:

.. code-block:: bash

   docker run --rm -p 8501:8501 \
     -v "$HOME/.jira-issues-dashboard/.streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro" \
     jira-issues-dashboard:latest

To stop the application, press ``Ctrl+C`` in the terminal where the container
is running.

Alternatively, run the container in the background:

.. code-block:: bash

   docker run -d --name jira-dashboard -p 8501:8501 \
     -v "$HOME/.jira-issues-dashboard/.streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro" \
     jira-issues-dashboard:latest

Stop and remove the background container with:

.. code-block:: bash

   docker stop jira-dashboard
   docker rm jira-dashboard

When the code changes, rebuild the local image and restart the container. This
repository does not currently define an official published container image.

Development
===========

Install development dependencies:

.. code-block:: bash

   uv sync --extra dev

Run the test suite:

.. code-block:: bash

   uv run pytest

More documentation is available under ``doc/``.
