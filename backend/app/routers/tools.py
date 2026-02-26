"""Financial tools API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Any
from app.models.user import User
from app.api.dependencies import get_current_user
from app.services.tools import execute_tool, execute_custom_calculation, AVAILABLE_TOOLS

router = APIRouter(prefix="/tools", tags=["Financial Tools"])


class ToolRequest(BaseModel):
    tool_name: str
    parameters: dict[str, Any]


class CalculationRequest(BaseModel):
    code: str
    variables: Optional[dict[str, Any]] = None


@router.get("/")
async def list_tools(current_user: User = Depends(get_current_user)):
    """List all available financial tools."""
    tools = []
    for name, info in AVAILABLE_TOOLS.items():
        tools.append({
            "name": name,
            "description": info["description"],
            "parameters": info["parameters"],
        })
    return {"tools": tools}


@router.post("/execute")
async def run_tool(
    request: ToolRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute a specific financial tool."""
    result = execute_tool(request.tool_name, request.parameters)
    return result


@router.post("/calculate")
async def custom_calculation(
    request: CalculationRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute a custom sandboxed calculation."""
    result = execute_custom_calculation(request.code, request.variables)
    return result
