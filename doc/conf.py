"""Sphinx configuration for the Jira Issues Dashboard documentation."""

project = "jira-issues-dashboard"
html_title = project
html_short_title = project

extensions = []
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
