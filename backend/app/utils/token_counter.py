# backend/app/utils/token_counter.py

from typing import Optional, List
from loguru import logger

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available - falling back to character estimation for token counting")


class TokenCounter:
    """Accurate token counting using tiktoken."""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """Initialize token counter with encoding for specified model.

        Args:
            model_name: Model name to determine encoding. Defaults to gpt-3.5-turbo.
                       For local models, we use cl100k_base encoding (GPT-3.5/GPT-4 compatible).
        """
        self.model_name = model_name
        self.encoding = None

        if TIKTOKEN_AVAILABLE:
            try:
                # Try to get encoding for model
                self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except KeyError:
                # Fall back to cl100k_base encoding (used by GPT-3.5/GPT-4)
                # This is a good general-purpose encoding for most LLMs
                try:
                    self.encoding = tiktoken.get_encoding("cl100k_base")
                    logger.info(f"Using cl100k_base encoding for token counting")
                except Exception as e:
                    logger.error(f"Failed to load tiktoken encoding: {e}")
                    self.encoding = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens (approximate if tiktoken unavailable)
        """
        if self.encoding is not None:
            try:
                return len(self.encoding.encode(text))
            except Exception as e:
                logger.error(f"Error counting tokens with tiktoken: {e}")

        # Fallback: character-based estimation (1 token ≈ 4 characters)
        # This is very rough but better than nothing
        return len(text) // 4

    def count_tokens_for_messages(self, messages: List[dict]) -> int:
        """Count tokens for a list of messages (OpenAI chat format).

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Total token count including formatting overhead
        """
        if self.encoding is None:
            # Fallback estimation
            total = 0
            for msg in messages:
                total += len(msg.get('content', '')) // 4 + 4  # +4 for role/formatting
            return total

        try:
            # Accurate counting based on OpenAI's token counting logic
            # Each message has overhead: <|start|>{role/name}\n{content}<|end|>\n
            tokens = 0

            for message in messages:
                tokens += 4  # Every message has overhead tokens
                for key, value in message.items():
                    tokens += len(self.encoding.encode(str(value)))

            tokens += 2  # Every reply is primed with <|start|>assistant
            return tokens

        except Exception as e:
            logger.error(f"Error counting message tokens: {e}")
            # Fallback
            total = 0
            for msg in messages:
                total += len(msg.get('content', '')) // 4 + 4
            return total


# Global instance for easy access
_global_counter: Optional[TokenCounter] = None


def get_token_counter(model_name: str = "gpt-3.5-turbo") -> TokenCounter:
    """Get or create global token counter instance."""
    global _global_counter
    if _global_counter is None:
        _global_counter = TokenCounter(model_name)
    return _global_counter


def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    """Convenience function to count tokens in text."""
    counter = get_token_counter(model_name)
    return counter.count_tokens(text)
