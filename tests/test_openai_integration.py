"""Optional live integration test for OpenAI.

This test only runs when both:
- `OPENAI_API_KEY` is set
- `RUN_LIVE_OPENAI_TESTS=1`
"""

import os

import pytest

from stacksense import StackSense


@pytest.mark.integration
def test_openai_integration_smoke(monkeypatch):
    """Run a minimal end-to-end monitored OpenAI call when explicitly enabled."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY is not set")

    if os.getenv("RUN_LIVE_OPENAI_TESTS") != "1":
        pytest.skip("Set RUN_LIVE_OPENAI_TESTS=1 to enable live OpenAI integration tests")

    openai = pytest.importorskip("openai")

    monkeypatch.setenv("STACKSENSE_ENABLE_DB", "false")
    ss = StackSense(project_id="openai-test", environment="development", debug=True)
    client = ss.monitor(openai.OpenAI(api_key=api_key))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say hello in exactly 5 words"}],
        max_tokens=50,
    )

    assert response is not None
    assert response.choices
    assert response.choices[0].message.content

    metrics = ss.get_metrics()
    assert metrics["total_calls"] >= 1
