"""Routes: agent capability cards, health, single-agent run."""
from fastapi import APIRouter

from app.services.orchestrator import AGENT_REGISTRY

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/")
def list_agents():
    """List all six capability agents with their A2A-style capability cards."""
    return [agent.card() for agent in AGENT_REGISTRY.values()]


@router.get("/{agent_id}/card")
def agent_card(agent_id: str):
    """A2A-style capability card for one agent."""
    agent = AGENT_REGISTRY.get(agent_id)
    if not agent:
        return {"error": f"unknown agent {agent_id}"}
    return agent.card()


@router.get("/{agent_id}/health")
def agent_health(agent_id: str):
    agent = AGENT_REGISTRY.get(agent_id)
    if not agent:
        return {"error": f"unknown agent {agent_id}"}
    return {"agent_id": agent_id, "status": "healthy", "version": agent.version}
