"""Setup routes: provider and channel configuration."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["setup"])


def _mask_key(key: str) -> str:
    """Mask an API key for display, showing only last 4 chars."""
    if not key or len(key) < 8:
        return "****" if key else ""
    return "****" + key[-4:]


class ProviderUpdate(BaseModel):
    name: str  # e.g. "anthropic", "openai"
    api_key: str = ""
    api_base: str | None = None
    model: str | None = None


class ChannelUpdate(BaseModel):
    enabled: bool = False
    token: str = ""
    extra: dict = {}


@router.get("/setup/status")
async def get_setup_status(request: Request):
    """Get the current configuration status for onboarding."""
    from finclaw.config.loader import load_config
    from finclaw.providers.registry import PROVIDERS

    config = load_config()

    # Provider status
    providers = []
    for spec in PROVIDERS:
        p = getattr(config.providers, spec.name, None)
        has_key = bool(p and p.api_key)
        providers.append({
            "name": spec.name,
            "display_name": spec.display_name,
            "has_key": has_key,
            "masked_key": _mask_key(p.api_key) if p else "",
            "is_gateway": spec.is_gateway,
        })

    # Current model
    current_model = config.agents.defaults.model
    active_provider = config.get_provider_name() or "none"

    # Channel status
    channels = {}
    for ch_name in ["telegram", "whatsapp", "slack", "discord"]:
        ch_config = getattr(config.channels, ch_name, None)
        if ch_config:
            channels[ch_name] = {
                "enabled": ch_config.enabled,
                "configured": bool(getattr(ch_config, "token", "") or getattr(ch_config, "bot_token", "")),
            }

    return {
        "providers": providers,
        "current_model": current_model,
        "active_provider": active_provider,
        "channels": channels,
        "has_provider": active_provider != "none",
    }


@router.post("/setup/provider")
async def update_provider(update: ProviderUpdate, request: Request):
    """Update an AI provider configuration."""
    from finclaw.config.loader import load_config, save_config

    config = load_config()
    provider_config = getattr(config.providers, update.name, None)
    if provider_config is None:
        return {"error": f"Unknown provider: {update.name}"}

    if update.api_key:
        provider_config.api_key = update.api_key
    if update.api_base is not None:
        provider_config.api_base = update.api_base
    if update.model:
        config.agents.defaults.model = update.model

    save_config(config)

    # Update live config
    request.app.state.config = config

    return {"status": "ok", "provider": update.name}


@router.post("/setup/channel/{channel_name}")
async def update_channel(channel_name: str, update: ChannelUpdate, request: Request):
    """Update a messaging channel configuration."""
    from finclaw.config.loader import load_config, save_config

    config = load_config()
    ch_config = getattr(config.channels, channel_name, None)
    if ch_config is None:
        return {"error": f"Unknown channel: {channel_name}"}

    ch_config.enabled = update.enabled

    # Set token based on channel type
    if hasattr(ch_config, "token") and update.token:
        ch_config.token = update.token
    elif hasattr(ch_config, "bot_token") and update.token:
        ch_config.bot_token = update.token

    # Apply extra fields
    for key, value in update.extra.items():
        if hasattr(ch_config, key):
            setattr(ch_config, key, value)

    save_config(config)
    request.app.state.config = config

    return {"status": "ok", "channel": channel_name, "enabled": update.enabled}
