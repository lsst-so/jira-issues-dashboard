#####################
jira-issues-dashboard
#####################

``jira-issues-dashboard`` is a Streamlit application for Jira issue triage and operational awareness.
It was developed for Rubin Observatory Observing Operations workflows and is being migrated into
``lsst-so`` as the official home for the project.

The current application provides views for issue activity, aging and stale tickets, workload by
assignee or reporter, and OBS hierarchy drilldowns when the corresponding Jira fields are available.
The application can be run locally from source or through the existing Dockerfile.

This repository import intentionally preserves the Rubin package scaffold. Follow-up work will
modernize the local installation path, including uv-based setup instructions, and clarify the
long-term packaging/deployment model.

Running locally
===============

Create a local Streamlit secrets file using the provided template::

   mkdir -p .streamlit
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml

Then edit ``.streamlit/secrets.toml`` with your Jira server, email, and API token. The real
``secrets.toml`` file is ignored by git.

For the current source-based workflow::

   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   streamlit run run_dashboard.py

Running with Docker
===================

The Dockerfile can be used to build and run the dashboard locally without installing the
application dependencies directly on your host machine.

First, create a local secrets file outside the repository or in the ignored local Streamlit
directory. For example::

   mkdir -p ~/.jira-issues-dashboard/.streamlit
   cp .streamlit/secrets.toml.example ~/.jira-issues-dashboard/.streamlit/secrets.toml

Then edit ``~/.jira-issues-dashboard/.streamlit/secrets.toml`` with your Jira server, email,
and API token.

Build the local runtime image from the repository root::

   docker build -t jira-issues-dashboard:latest .

Run the dashboard in the foreground::

   docker run --rm -p 8501:8501 \
     -v "$HOME/.jira-issues-dashboard/.streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro" \
     jira-issues-dashboard:latest

After a few seconds, open ``http://localhost:8501``. To stop the application, press
``Ctrl+C`` in the terminal where the container is running.

Alternatively, run the container in the background::

   docker run -d --name jira-dashboard -p 8501:8501 \
     -v "$HOME/.jira-issues-dashboard/.streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro" \
     jira-issues-dashboard:latest

Stop and remove the background container with::

   docker stop jira-dashboard
   docker rm jira-dashboard

When the code changes, rebuild the local image and restart the container. This repository does
not currently define an official published container image.

Development
===========

Run the tests with::

   pytest
