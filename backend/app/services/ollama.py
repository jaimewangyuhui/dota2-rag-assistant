from typing import Optional

import httpx

from app.db.session import ServiceStatus


async def check_ollama(
    base_url: str,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> ServiceStatus:
    try:
        async with httpx.AsyncClient(
            base_url=str(base_url).rstrip("/"),
            timeout=2.0,
            transport=transport,
        ) as client:
            response = await client.get("/api/version")
            response.raise_for_status()
            version = response.json().get("version", "ready")
        return ServiceStatus(name="ollama", ok=True, detail=str(version))
    except Exception as exc:
        return ServiceStatus(name="ollama", ok=False, detail=str(exc))
