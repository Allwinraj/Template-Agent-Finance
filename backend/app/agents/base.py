"""
BaseAgent — the contract every capability agent implements.

Agents are configuration-driven: run(config, payload) where config comes
from the workflow definition (editable in the UI). Agents communicate only
through the Orchestrator via structured JSON payloads.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone


class BaseAgent(ABC):
    """Common agent contract with capability card + audit hooks."""

    id: str = "A?"
    name: str = "Base"
    description: str = ""
    version: str = "v1"

    def card(self) -> dict:
        """A2A-style capability card."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "config_schema": self.config_schema(),
        }

    def config_schema(self) -> dict:
        """Describe the configuration keys this agent accepts (for the UI)."""
        return {}

    @abstractmethod
    def run(self, config: dict, payload: dict, context: dict) -> dict:
        """
        Execute the agent step.

        config : workflow configuration for this agent (from registry)
        payload: structured input from the previous agent / orchestrator
        context: run context (run_id, workflow_id, shared state)
        returns: structured output dict passed to the next agent
        """

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()