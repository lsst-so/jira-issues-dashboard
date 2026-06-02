###########
Development
###########

Synchronize the development environment with:

.. code-block:: bash

   uv sync --extra dev

Run the test suite with:

.. code-block:: bash

   uv run pytest

Run linting and formatting tools with:

.. code-block:: bash

   uv run ruff check .
   uv run black --check .

Build the documentation locally with:

.. code-block:: bash

   uv run sphinx-build -b html doc doc/_build/html

If Sphinx reports an unsupported local locale setting, run the same command
with a neutral locale:

.. code-block:: bash

   LC_ALL=C LANG=C uv run sphinx-build -b html doc doc/_build/html

Packaging notes
===============

This repository is maintained as a uv-first Streamlit application. The initial
Squarebot-generated UPS/SCons scaffold has been removed because the intended
local user workflow is based on ``uv sync`` and ``uv run`` rather than
``setup`` through EUPS.
