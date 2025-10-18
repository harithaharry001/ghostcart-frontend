"""
AWS Bedrock Service for Claude Model Invocation

Provides streaming and non-streaming interfaces to Claude Sonnet 4.5
via AWS Bedrock for agent reasoning.

AP2 Compliance: Agents use Claude for autonomous decision-making in
HNP flows and intelligent routing.
"""
import json
import boto3
from typing import Dict, Any, AsyncIterator, Optional
import logging
from botocore.exceptions import ClientError, BotoCoreError

from ..config import settings


logger = logging.getLogger(__name__)


class BedrockService:
    """
    AWS Bedrock client wrapper for Claude model invocation.

    Provides both streaming and non-streaming inference capabilities
    with error handling and response parsing.
    """

    def __init__(self):
        """
        Initialize Bedrock client with configured region and model.

        Raises:
            RuntimeError: If client initialization fails
        """
        try:
            self.client = boto3.client(
                service_name='bedrock-runtime',
                region_name=settings.aws_region
            )
            self.model_id = settings.aws_bedrock_model_id
            logger.info(f"Bedrock client initialized: region={settings.aws_region}, model={self.model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise RuntimeError(f"Bedrock initialization failed: {e}")

    def invoke_model(
        self,
        messages: list[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Invoke Claude model with non-streaming request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Model response dict with 'content', 'stop_reason', 'usage'

        Raises:
            RuntimeError: If invocation fails
        """
        try:
            # Build request body per Bedrock Claude API format
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            if system:
                body["system"] = system

            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            return {
                "content": response_body.get("content", []),
                "stop_reason": response_body.get("stop_reason"),
                "usage": response_body.get("usage", {}),
            }

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Bedrock ClientError: {error_code} - {error_message}")
            raise RuntimeError(f"Model invocation failed: {error_code} - {error_message}")

        except BotoCoreError as e:
            logger.error(f"Bedrock BotoCoreError: {e}")
            raise RuntimeError(f"Bedrock communication error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in invoke_model: {e}")
            raise RuntimeError(f"Model invocation failed: {e}")

    async def invoke_claude(
        self,
        messages: list[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Async wrapper for invoke_model with system_prompt parameter name.

        This method provides an async interface compatible with agent usage patterns.
        Uses asyncio to run the synchronous boto3 call in a thread pool with timeout.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt (alias for system parameter)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Model response dict with 'content', 'stop_reason', 'usage'

        Raises:
            RuntimeError: If invocation fails or times out
        """
        import asyncio

        # Run synchronous invoke_model in thread pool with timeout
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.invoke_model(
                        messages=messages,
                        system=system_prompt,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                ),
                timeout=30.0  # 30 second timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.error("Bedrock invocation timed out after 30 seconds")
            raise RuntimeError("Bedrock API call timed out. Check AWS credentials and network connectivity.")

    async def invoke_model_with_response_stream(
        self,
        messages: list[Dict[str, Any]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Invoke Claude model with streaming response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Yields:
            Parsed event dicts from the stream:
            - {"type": "message_start", "message": {...}}
            - {"type": "content_block_delta", "delta": {"text": "..."}}
            - {"type": "message_stop"}

        Raises:
            RuntimeError: If streaming fails
        """
        try:
            # Build request body
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            if system:
                body["system"] = system

            # Invoke with streaming
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            # Process stream
            stream = response.get('body')
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_data = json.loads(chunk.get('bytes').decode())
                        yield chunk_data

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Bedrock streaming ClientError: {error_code} - {error_message}")
            raise RuntimeError(f"Streaming invocation failed: {error_code} - {error_message}")

        except BotoCoreError as e:
            logger.error(f"Bedrock streaming BotoCoreError: {e}")
            raise RuntimeError(f"Bedrock streaming error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in streaming invocation: {e}")
            raise RuntimeError(f"Streaming failed: {e}")

    def extract_text_from_content(self, content: list[Dict[str, Any]]) -> str:
        """
        Extract text from Claude's content blocks.

        Args:
            content: List of content blocks from Claude response

        Returns:
            Concatenated text from all text blocks
        """
        text_parts = []
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "".join(text_parts)


# Global service instance
_bedrock_service: Optional[BedrockService] = None


def get_bedrock_service() -> BedrockService:
    """
    Get or create global Bedrock service instance.

    Returns:
        BedrockService singleton

    Raises:
        RuntimeError: If initialization fails
    """
    global _bedrock_service
    if _bedrock_service is None:
        _bedrock_service = BedrockService()
    return _bedrock_service
