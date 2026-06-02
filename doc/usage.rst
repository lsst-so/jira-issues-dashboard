#####
Usage
#####

Start the application with:

.. code-block:: bash

   uv run streamlit run run_dashboard.py

The main pages are:

``Setup / Connection``
   Connects the dashboard to Jira and initializes the issue service.

``Activity Overview``
   Shows activity, aging, trends, top tickets, and operational groupings for the
   selected date range and filters.

``Personal View``
   Summarizes workload for a selected user, including assigned and reported
   issues and OBS hierarchy distributions when available.

``Assignee | Reporter Insights``
   Provides people-oriented summaries for assignee and reporter activity.

``Stale Tickets``
   Highlights unresolved tickets that have not been updated within the selected
   threshold.
