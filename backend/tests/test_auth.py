import pytest
from fastapi import HTTPException
from backend.utils.auth import verify_api_key
from backend.config import settings as settings_module


@pytest.fixture(autouse=True)
def _reset_api_key():
    """Ensures each test starts from a known API_KEY state and restores it after."""
    original = settings_module.settings.API_KEY
    yield
    settings_module.settings.API_KEY = original


class TestVerifyApiKey:
    @pytest.mark.asyncio
    async def test_passes_through_when_unconfigured(self):
        settings_module.settings.API_KEY = ""
        # Should not raise, regardless of what header (or lack of one) is sent
        await verify_api_key(x_api_key=None)
        await verify_api_key(x_api_key="anything")

    @pytest.mark.asyncio
    async def test_accepts_correct_key(self):
        settings_module.settings.API_KEY = "real-secret-123"
        await verify_api_key(x_api_key="real-secret-123")  # should not raise

    @pytest.mark.asyncio
    async def test_rejects_wrong_key(self):
        settings_module.settings.API_KEY = "real-secret-123"
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(x_api_key="wrong-key")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_missing_key_when_configured(self):
        settings_module.settings.API_KEY = "real-secret-123"
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(x_api_key=None)
        assert exc_info.value.status_code == 401
