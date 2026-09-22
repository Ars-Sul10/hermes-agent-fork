from __future__ import annotations

import os
import json
import time
import uuid
import logging
import asyncio
from typing import Any, Dict, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from .config import AgentCoreConfig

try:
    from integrations.aquera.client import AqueraClient
    from integrations.aquera.tools import AqueraTools
    from integrations.aquera.models import UserContext
    from hermes.registry import ToolRegistry
    from hermes.agent import HermesAgent
except (ImportError, ValueError):
    from hermes.integrations.aquera.client import AqueraClient
    from hermes.integrations.aquera.tools import AqueraTools
    from hermes.integrations.aquera.models import UserContext
    from hermes.hermes.registry import ToolRegistry
    from hermes.hermes.agent import HermesAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("agentcore.runtime")


def create_agent_system() -> tuple[HermesAgent, AqueraTools, ToolRegistry]:
    """Initialize Aquera client, tool registry, and Hermes reasoning agent."""
    config = AgentCoreConfig.from_env()

    client = AqueraClient(
        base_url=config.aquera_base_url,
        token=config.aquera_api_token,
        timeout=config.aquera_timeout_seconds,
        max_retries=config.aquera_max_retries,
    )
    tools = AqueraTools(client)
    registry = ToolRegistry()

    # Register all Aquera tool capabilities
    registry.register(tools.get_organization, name="get_organization", requires_context=True)
    registry.register(tools.get_members, name="get_members", requires_context=True)
    registry.register(tools.get_user_context, name="get_user_context", requires_context=True)
    registry.register(tools.get_ponds, name="get_ponds", requires_context=True)
    registry.register(tools.create_pond, name="create_pond", requires_context=True)
    registry.register(tools.get_cycles, name="get_cycles", requires_context=True)
    registry.register(tools.create_cycle, name="create_cycle", requires_context=True)
    registry.register(tools.get_samplings, name="get_samplings", requires_context=True)
    registry.register(tools.create_sampling, name="create_sampling", requires_context=True)
    registry.register(tools.get_harvests, name="get_harvests", requires_context=True)
    registry.register(tools.create_harvest, name="create_harvest", requires_context=True)
    registry.register(tools.get_summary, name="get_summary", requires_context=True)
    registry.register(tools.get_report, name="get_report", requires_context=True)

    agent = HermesAgent(
        registry=registry,
        model=config.llm_model,
        llm_api_key=config.openrouter_api_key,
        llm_base_url=config.openrouter_base_url,
    )

    return agent, tools, registry


class AgentCoreHTTPHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler implementing AWS Bedrock AgentCore Runtime Contract."""

    agent: Optional[HermesAgent] = None
    tools: Optional[AqueraTools] = None

    def log_message(self, format: str, *args: Any) -> None:
        # Structured log without leaking Authorization or secrets
        logger.info(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        if self.path == "/ping" or self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "agentcore-hermes"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))

    def do_POST(self) -> None:
        if self.path != "/invocations":
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            payload = json.loads(body) if body else {}
        except Exception:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON body"}).encode("utf-8"))
            return

        message = payload.get("message", "")
        session_id = payload.get("session_id", str(uuid.uuid4()))
        organization_id = (
            payload.get("organization_id")
            or self.headers.get("x-organization-id")
            or os.getenv("DEFAULT_ORGANIZATION_ID", "")
        )
        user_id = (
            payload.get("user_id")
            or self.headers.get("x-user-id")
            or None
        )
        role = payload.get("role", "viewer")

        if not message:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "'message' field is required"}).encode("utf-8"))
            return

        context = UserContext(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
            session_id=session_id,
        )

        req_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        logger.info(
            "AgentCore Invocation Received",
            extra={
                "request_id": req_id,
                "session_id": session_id,
                "user_id": user_id,
                "organization_id": organization_id,
                "role": role,
            },
        )

        try:
            # Run async agent loop inside event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text = loop.run_until_complete(
                self.agent.run(user_message=message, context=context)
            )
            loop.close()

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                "AgentCore Invocation Completed",
                extra={
                    "request_id": req_id,
                    "duration_ms": duration_ms,
                    "status": 200,
                },
            )

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("x-request-id", req_id)
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    "response": response_text,
                    "session_id": session_id,
                    "request_id": req_id,
                    "duration_ms": duration_ms,
                }).encode("utf-8")
            )

        except Exception as e:
            logger.exception("Error processing AgentCore invocation")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            # Do NOT expose stack traces to user / client
            self.wfile.write(
                json.dumps({
                    "error": "Internal AgentCore error occurred. Check server logs.",
                    "request_id": req_id,
                }).encode("utf-8")
            )


def run_server(host: Optional[str] = None, port: Optional[int] = None) -> None:
    config = AgentCoreConfig.from_env()
    server_host = host or config.host
    server_port = port or config.port

    agent, tools, _ = create_agent_system()
    AgentCoreHTTPHandler.agent = agent
    AgentCoreHTTPHandler.tools = tools

    httpd = HTTPServer((server_host, server_port), AgentCoreHTTPHandler)
    logger.info(f"AgentCore Runtime Server running on http://{server_host}:{server_port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down AgentCore server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
