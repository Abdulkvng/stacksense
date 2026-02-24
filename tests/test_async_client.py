import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from stacksense.utils.helpers import AsyncClientProxy

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_async_client_proxy_tracking():
    mock_tracker = MagicMock()
    mock_client = AsyncMock()
    # Mock chat.completions.create method
    mock_chat = AsyncMock()
    mock_client.chat = mock_chat
    mock_completions = AsyncMock()
    mock_chat.completions = mock_completions
    
    # Setup response
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_completions.create.return_value = mock_response

    proxy = AsyncClientProxy(mock_client, mock_tracker, "openai")
    
    result = await proxy.chat.completions.create(model="gpt-4", messages=[])
    
    assert result == mock_response
    mock_tracker.track_call.assert_called_once()
    call_args = mock_tracker.track_call.call_args[1]
    
    assert call_args["provider"] == "openai"
    assert call_args["model"] == "gpt-4"
    assert call_args["tokens"] == {"input": 10, "output": 20}
    assert call_args["success"] is True
    assert "latency" in call_args
