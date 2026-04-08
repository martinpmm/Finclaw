"""FastAPI application for the Finclaw web platform."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger


def _make_provider(config):
    """Create the appropriate LLM provider from config (mirrors CLI helper)."""
    from finclaw.providers.custom_provider import CustomProvider
    from finclaw.providers.litellm_provider import LiteLLMProvider
    from finclaw.providers.openai_codex_provider import OpenAICodexProvider

    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)
    p = config.get_provider(model)

    if provider_name == "openai_codex" or model.startswith("openai-codex/"):
        return OpenAICodexProvider(default_model=model)

    if provider_name == "custom":
        return CustomProvider(
            api_key=p.api_key if p else "no-key",
            api_base=config.get_api_base(model) or "http://localhost:8000/v1",
            default_model=model,
        )

    return LiteLLMProvider(
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(model),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=provider_name,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the agent loop and web channel on startup, clean up on shutdown."""
    from finclaw.agent.loop import AgentLoop
    from finclaw.bus.queue import MessageBus
    from finclaw.config.loader import load_config
    from finclaw.session.manager import SessionManager
    from finclaw.utils.helpers import sync_workspace_templates
    from finclaw.web.channel import WebChannel

    config = load_config()
    sync_workspace_templates(config.workspace_path)

    bus = MessageBus()
    provider = _make_provider(config)
    session_manager = SessionManager(config.workspace_path)

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=config.agents.defaults.max_tool_iterations,
        memory_window=config.agents.defaults.memory_window,
        reasoning_effort=config.agents.defaults.reasoning_effort,
        brave_api_key=config.tools.web.search.api_key or None,
        web_proxy=config.tools.web.proxy or None,
        exec_config=config.tools.exec,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        session_manager=session_manager,
        mcp_servers=config.tools.mcp_servers,
        channels_config=config.channels,
        fred_api_key=config.tools.financial_data.fred_api_key or None,
        reddit_config={
            "client_id": config.tools.financial_data.reddit_client_id,
            "client_secret": config.tools.financial_data.reddit_client_secret,
            "user_agent": config.tools.financial_data.reddit_user_agent,
        },
        alpaca_api_key=config.tools.financial_data.alpaca_api_key or None,
        alpaca_secret_key=config.tools.financial_data.alpaca_secret_key or None,
    )

    web_channel = WebChannel(bus)

    # Store shared state
    app.state.config = config
    app.state.bus = bus
    app.state.agent = agent
    app.state.session_manager = session_manager
    app.state.web_channel = web_channel
    app.state.workspace = config.workspace_path

    # Start agent loop and web channel dispatcher as background tasks
    agent_task = asyncio.create_task(agent.run())
    dispatch_task = asyncio.create_task(web_channel.dispatch_outbound())

    logger.info("Finclaw web platform started")
    yield

    # Shutdown
    agent.stop()
    dispatch_task.cancel()
    agent_task.cancel()
    try:
        await agent.close_mcp()
    except Exception:
        pass
    logger.info("Finclaw web platform stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from finclaw.web.routes.chat import router as chat_router
    from finclaw.web.routes.companies import router as companies_router
    from finclaw.web.routes.documents import router as documents_router
    from finclaw.web.routes.setup import router as setup_router

    app = FastAPI(
        title="Finclaw",
        description="AI-powered financial analysis platform",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(chat_router, prefix="/api")
    app.include_router(companies_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(setup_router, prefix="/api")

    # Serve built frontend static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and (static_dir / "index.html").exists():
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve the SPA — return index.html for all non-API routes."""
            file_path = static_dir / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))
            return FileResponse(str(static_dir / "index.html"))
    else:
        @app.get("/")
        async def no_frontend():
            return {
                "message": "Finclaw API is running. Frontend not built yet.",
                "hint": "Run 'cd web && npm install && npm run build' to build the frontend.",
            }

    return app
