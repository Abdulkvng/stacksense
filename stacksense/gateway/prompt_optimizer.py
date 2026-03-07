"""
Prompt Optimizer - Token Efficiency Engine

Optimizes prompts to reduce token usage while maintaining quality:
- Remove redundant words and phrases
- Compress verbose instructions
- Optimize system prompts
- Smart truncation of long contexts
"""

from typing import Dict, Any, List, Optional
import re

from stacksense.logger.logger import get_logger

logger = get_logger(__name__)


class PromptOptimizer:
    """
    Optimizes prompts for token efficiency.

    Techniques:
    - Remove filler words and redundancy
    - Compress verbose instructions
    - Truncate low-value content
    - Preserve semantic meaning
    """

    def __init__(self, aggressive_mode: bool = False):
        self.aggressive_mode = aggressive_mode

        # Common filler words to remove
        self.filler_words = {
            "actually",
            "basically",
            "essentially",
            "literally",
            "really",
            "very",
            "quite",
            "just",
            "simply",
            "merely",
            "rather",
            "somewhat",
            "pretty",
            "fairly",
            "relatively",
        }

        # Compression patterns (verbose → concise)
        self.compression_patterns = [
            (r"in order to", "to"),
            (r"due to the fact that", "because"),
            (r"at this point in time", "now"),
            (r"for the purpose of", "for"),
            (r"in the event that", "if"),
            (r"with regard to", "about"),
            (r"a large number of", "many"),
            (r"a majority of", "most"),
            (r"in spite of the fact that", "although"),
            (r"take into consideration", "consider"),
        ]

        logger.info(f"Prompt Optimizer initialized (aggressive={aggressive_mode})")

    def optimize(
        self,
        messages: List[Dict[str, str]],
        model: str,
        target_reduction: float = 0.15,  # 15% reduction target
    ) -> Dict[str, Any]:
        """
        Optimize messages for token efficiency.

        Args:
            messages: Chat messages to optimize
            model: Model being used (affects optimization strategy)
            target_reduction: Target token reduction percentage

        Returns:
            dict: {
                "messages": optimized messages,
                "optimized": bool,
                "original_tokens": int,
                "optimized_tokens": int,
                "savings_percent": float
            }
        """
        original_messages = messages.copy()
        original_tokens = self._estimate_tokens(messages)

        optimized_messages = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            # System prompts: moderate optimization (preserve instructions)
            if role == "system":
                optimized_content = self._optimize_system_prompt(content)

            # User prompts: aggressive optimization (reduce verbosity)
            elif role == "user":
                optimized_content = self._optimize_user_prompt(content)

            # Assistant prompts: light optimization (preserve response quality)
            else:
                optimized_content = self._optimize_assistant_prompt(content)

            optimized_messages.append({"role": role, "content": optimized_content})

        optimized_tokens = self._estimate_tokens(optimized_messages)

        # Calculate savings
        tokens_saved = original_tokens - optimized_tokens
        savings_percent = (tokens_saved / original_tokens * 100) if original_tokens > 0 else 0

        # Only apply if we hit target reduction
        if savings_percent >= (target_reduction * 100):
            logger.info(
                f"Prompt optimized: {original_tokens} → {optimized_tokens} tokens "
                f"({savings_percent:.1f}% reduction)"
            )
            return {
                "messages": optimized_messages,
                "optimized": True,
                "original_tokens": original_tokens,
                "optimized_tokens": optimized_tokens,
                "savings_percent": savings_percent,
            }
        else:
            # Insufficient savings, return original
            return {
                "messages": original_messages,
                "optimized": False,
                "original_tokens": original_tokens,
                "optimized_tokens": original_tokens,
                "savings_percent": 0.0,
            }

    def _optimize_system_prompt(self, content: str) -> str:
        """Optimize system prompt (moderate optimization)."""
        # Remove extra whitespace
        content = re.sub(r"\s+", " ", content).strip()

        # Apply compression patterns
        for pattern, replacement in self.compression_patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        # Remove filler words
        if self.aggressive_mode:
            words = content.split()
            words = [w for w in words if w.lower() not in self.filler_words]
            content = " ".join(words)

        return content

    def _optimize_user_prompt(self, content: str) -> str:
        """Optimize user prompt (aggressive optimization)."""
        # Remove extra whitespace
        content = re.sub(r"\s+", " ", content).strip()

        # Apply compression patterns
        for pattern, replacement in self.compression_patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        # Remove filler words
        words = content.split()
        words = [w for w in words if w.lower() not in self.filler_words]
        content = " ".join(words)

        # Remove redundant punctuation
        content = re.sub(r"\.{2,}", ".", content)
        content = re.sub(r"\?{2,}", "?", content)
        content = re.sub(r"!{2,}", "!", content)

        # Compress common phrases
        content = re.sub(r"please\s+", "", content, flags=re.IGNORECASE)
        content = re.sub(r"could you\s+", "", content, flags=re.IGNORECASE)
        content = re.sub(r"would you\s+", "", content, flags=re.IGNORECASE)
        content = re.sub(r"can you\s+", "", content, flags=re.IGNORECASE)

        return content

    def _optimize_assistant_prompt(self, content: str) -> str:
        """Optimize assistant prompt (light optimization)."""
        # Just remove extra whitespace for assistant messages
        # Preserve response quality
        content = re.sub(r"\s+", " ", content).strip()
        return content

    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count for messages.

        Simple heuristic: ~4 characters per token.
        In production, use tiktoken for accurate counting.
        """
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4

    def compress_context(
        self, messages: List[Dict[str, str]], max_tokens: int
    ) -> List[Dict[str, str]]:
        """
        Compress conversation history to fit within token limit.

        Strategy:
        1. Keep system prompt (always)
        2. Keep most recent user message (always)
        3. Truncate middle messages if needed
        4. Preserve message alternation (user/assistant)

        Args:
            messages: Conversation history
            max_tokens: Maximum token limit

        Returns:
            Compressed messages list
        """
        if not messages:
            return messages

        current_tokens = self._estimate_tokens(messages)

        if current_tokens <= max_tokens:
            return messages

        # Separate system, recent, and middle messages
        system_messages = [m for m in messages if m.get("role") == "system"]
        other_messages = [m for m in messages if m.get("role") != "system"]

        if not other_messages:
            return messages

        # Always keep last message (most recent user input)
        last_message = other_messages[-1]
        middle_messages = other_messages[:-1]

        # Calculate available tokens
        system_tokens = self._estimate_tokens(system_messages)
        last_tokens = self._estimate_tokens([last_message])
        available_tokens = max_tokens - system_tokens - last_tokens

        # Truncate middle messages from the beginning
        compressed_middle = []
        running_tokens = 0

        for message in reversed(middle_messages):
            message_tokens = self._estimate_tokens([message])

            if running_tokens + message_tokens <= available_tokens:
                compressed_middle.insert(0, message)
                running_tokens += message_tokens
            else:
                break

        # Reconstruct compressed messages
        result = system_messages + compressed_middle + [last_message]

        logger.info(
            f"Context compressed: {len(messages)} → {len(result)} messages, "
            f"{current_tokens} → {self._estimate_tokens(result)} tokens"
        )

        return result
