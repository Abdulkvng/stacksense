import pytest
from unittest.mock import MagicMock

from stacksense.utils.helpers import ClientProxy

def test_streaming_client_proxy():
    mock_tracker = MagicMock()
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chat = mock_chat
    mock_completions = MagicMock()
    mock_chat.completions = mock_completions
    
    # Mock chunks
    chunk1 = MagicMock()
    chunk2 = MagicMock()
    chunk3 = MagicMock()
    # Mock OpenAI streaming usage
    chunk3.usage.prompt_tokens = 5
    chunk3.usage.completion_tokens = 15
    
    def mock_generator():
        yield chunk1
        yield chunk2
        yield chunk3
        
    mock_completions.create.return_value = mock_generator()

    proxy = ClientProxy(mock_client, mock_tracker, "openai")
    
    stream = proxy.chat.completions.create(model="gpt-4", stream=True, stream_options={"include_usage": True})
    
    # At this point, generator is returned, but tracker.track_call should NOT be called yet
    mock_tracker.track_call.assert_not_called()
    
    # Consume stream
    chunks = list(stream)
    
    assert len(chunks) == 3
    assert chunks[0] == chunk1
    
    # Now it should be called
    mock_tracker.track_call.assert_called_once()
    call_args = mock_tracker.track_call.call_args[1]
    
    assert call_args["provider"] == "openai"
    assert call_args["model"] == "gpt-4"
    assert call_args["tokens"] == {"input": 5, "output": 15}
    assert call_args["metadata"]["stream"] is True
    assert call_args["success"] is True
