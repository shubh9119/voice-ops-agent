"""
Allow running the agent worker via ``python -m voiceagent``.

Delegates to ``cli.run_app`` which handles the ``dev``, ``start``, and
``download-files`` sub-commands.
"""

from .main import server
from livekit.agents import cli

cli.run_app(server)
