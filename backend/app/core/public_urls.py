from urllib.parse import urlencode

from app.core.config import settings


def build_public_web_url(path: str, query: dict[str, str] | None = None) -> str:
    """Build an external URL on the configured public frontend origin."""
    url = f"{settings.public_web_url}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return url
