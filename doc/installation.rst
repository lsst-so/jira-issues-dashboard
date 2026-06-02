############
Installation
############

The recommended local workflow uses uv to create and maintain the project
environment from ``pyproject.toml`` and ``uv.lock``.

Install uv by following the upstream instructions at https://docs.astral.sh/uv/.
Then clone the repository and synchronize the environment:

.. code-block:: bash

   git clone https://github.com/lsst-so/jira-issues-dashboard.git
   cd jira-issues-dashboard
   uv sync

Run the dashboard with:

.. code-block:: bash

   uv run streamlit run run_dashboard.py

Open http://localhost:8501 after Streamlit starts.

Docker
======

The repository also includes a Dockerfile for local container builds. Build and
run a local image with:

.. code-block:: bash

   docker build -t jira-issues-dashboard:latest .
   docker run --rm -p 8501:8501 \
     -v "$HOME/.jira-issues-dashboard/.streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro" \
     jira-issues-dashboard:latest

The repository does not currently define an official published container image.
