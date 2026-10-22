"""
Allow running the agent worker via ``python -m voiceagent`` or ``python -m voiceagent.main``.

Delegates to ``cli.run_app`` which handles the ``dev``, ``start``, and
``download-files`` sub-commands.
"""

from .main import entrypoint, prewarm, settings
from livekit.agents import cli
from livekit.agents.worker import WorkerOptions

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name=settings.agent_name,
        )
    )
