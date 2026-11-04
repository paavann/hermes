import json
import logging
import os

import litellm
from langfuse import get_client, observe
from litellm.router import Router
from litellm.types.router import DeploymentTypedDict
from pydantic import BaseModel, ValidationError

from hermes_ai.core.config import AiConfig
from hermes_ai.exceptions import (
    ConfigurationError,
    ModelExecutionError,
    SchemaValidationError,
)
from hermes_ai.utils.rate_limiter import TbRateLimiter


logger = logging.getLogger(__name__)


def _clean_json_str(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()

    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned


class LlmService:
    def __init__(self, config: AiConfig) -> None:
        self._config = config
        if not config.primary_api_key or not config.primary_model:
            logger.error("primary llm api key or model is missing.")
            raise ConfigurationError("primary_api_key and primary_model are required.")

        model_list: list[DeploymentTypedDict] = [
            {
                "model_name": "primary-extractor",
                "litellm_params": {
                    "model": config.primary_model,
                    "api_key": config.primary_api_key,
                },
            }
        ]
        fallbacks: list[dict[str, list[str]]] = []
        if config.fallback_model and config.fallback_api_key:
            model_list.append(
                {
                    "model_name": "fallback-extractor",
                    "litellm_params": {
                        "model": config.fallback_model,
                        "api_key": config.fallback_api_key,
                    },
                }
            )
            fallbacks = [{"primary-extractor": ["fallback-extractor"]}]

        self._router = Router(
            model_list=model_list,
            fallbacks=fallbacks,
            num_retries=config.num_retries,
            cooldown_time=config.cooldown_time,
            retry_after=config.retry_after,
        )
        self._rate_limiter = (
            TbRateLimiter(config.rpm_limit) if config.rpm_limit else None
        )
        self._embed_rate_limiter = (
            TbRateLimiter(config.embed_rpm_limit) if config.embed_rpm_limit else None
        )

        if config.tracing_enabled:
            if config.langfuse_public_key:
                os.environ["LANGFUSE_PUBLIC_KEY"] = config.langfuse_public_key
            if config.langfuse_secret_key:
                os.environ["LANGFUSE_SECRET_KEY"] = config.langfuse_secret_key
            if config.langfuse_host:
                os.environ["LANGFUSE_HOST"] = config.langfuse_host

            litellm.callbacks = ["langfuse_otel"]
            logger.info("langfuse tracing enabled via langfuse_otel callback.")

        logger.info(
            "llm service initialized. primary=%s, fallback=%s via litellm router.",
            config.primary_model,
            config.fallback_model if fallbacks else "none",
        )

    @property
    def router(self) -> Router:
        return self._router

    @property
    def rate_limiter(self) -> TbRateLimiter | None:
        return self._rate_limiter

    @property
    def embed_rate_limiter(self) -> TbRateLimiter | None:
        return self._embed_rate_limiter

    async def _invoke_and_parse[T: BaseModel](
        self,
        model_name: str,
        sys_prompt: str,
        user_prompt: str,
        res_model: type[T],
        schema_name: str,
    ) -> T:
        if self._rate_limiter:
            await self._rate_limiter.acquire()

        res = await self._router.acompletion(
            model=model_name,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": res_model.model_json_schema(),
                },
            },
        )
        content = res.choices[0].message.content
        if not content:
            logger.warning("llm returned empty content for %s.", schema_name)
            raise ValueError(f"empty content from {model_name} for {schema_name}.")
        return res_model.model_validate_json(_clean_json_str(content))

    @observe(as_type="generation", capture_input=False, capture_output=False)
    async def call_llm[T: BaseModel](
        self,
        sys_prompt: str,
        user_prompt: str,
        res_model: type[T],
        schema_name: str,
    ) -> T:
        lf = get_client()
        lf.update_current_span(
            name=schema_name,
            input=user_prompt,
            metadata={"schema": schema_name, "tags": self._config.tracing_tags},
        )
        try:
            result = await self._invoke_and_parse(
                "primary-extractor",
                sys_prompt,
                user_prompt,
                res_model,
                schema_name,
            )
            lf.update_current_span(output=result.model_dump())
            return result
        except (ValidationError, ValueError, json.JSONDecodeError) as val_err:
            logger.warning(
                "primary llm output validation failed for %s: %s. attempting fallback if available.",
                schema_name,
                val_err,
            )
            if self._config.fallback_model and self._config.fallback_api_key:
                try:
                    parsed = await self._invoke_and_parse(
                        "fallback-extractor",
                        sys_prompt,
                        user_prompt,
                        res_model,
                        schema_name,
                    )
                    logger.info("fallback extractor succeeded for %s.", schema_name)
                    lf.update_current_span(
                        output=parsed.model_dump(),
                        metadata={
                            "schema": schema_name,
                            "tags": self._config.tracing_tags,
                            "used_fallback": True,
                        },
                    )
                    return parsed
                except (
                    ValidationError,
                    ValueError,
                    json.JSONDecodeError,
                ) as fb_val_err:
                    logger.error(
                        "fallback llm output validation failed for %s: %s.",
                        schema_name,
                        fb_val_err,
                    )
                    lf.update_current_span(
                        level="ERROR",
                        status_message=f"primary + fallback validation failed: {fb_val_err}",
                    )
                    raise SchemaValidationError(
                        f"output validation failed across primary and fallback models for {schema_name}.",
                        schema_name=schema_name,
                        validation_error=fb_val_err,
                    ) from fb_val_err
                except Exception as fb_exc:
                    logger.error(
                        "fallback llm call failed for %s: %s.", schema_name, fb_exc
                    )
                    lf.update_current_span(
                        level="ERROR",
                        status_message=f"fallback model execution failed: {fb_exc}",
                    )
                    raise ModelExecutionError(
                        f"fallback model execution failed for {schema_name}: {fb_exc}.",
                        schema_name=schema_name,
                        original_exception=fb_exc,
                    ) from fb_exc

            logger.error("llm call failed for %s: %s.", schema_name, val_err)
            lf.update_current_span(
                level="ERROR",
                status_message=f"primary validation failed, no fallback: {val_err}",
            )
            raise SchemaValidationError(
                f"primary llm output validation failed for {schema_name} and no fallback available.",
                schema_name=schema_name,
                validation_error=val_err,
            ) from val_err
        except Exception as exc:
            logger.error(
                "llm call failed across router deployments for %s: %s.",
                schema_name,
                exc,
            )
            lf.update_current_span(
                level="ERROR",
                status_message=f"all router deployments failed: {exc}",
            )
            raise ModelExecutionError(
                f"all router deployments failed for {schema_name}: {exc}.",
                schema_name=schema_name,
                original_exception=exc,
            ) from exc

    @observe(as_type="embedding", capture_input=False, capture_output=False)
    async def gen_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        if not texts:
            return []
        elif not self._config.embed_model or not self._config.embed_api_key:
            logger.error("embed api key or model is missing.")
            return [None] * len(texts)
        elif self._embed_rate_limiter:
            await self._embed_rate_limiter.acquire()

        lf = get_client()
        lf.update_current_span(
            name="gen-embeddings",
            input={"text_count": len(texts)},
            metadata={
                "model": self._config.embed_model,
                "tags": self._config.tracing_tags,
            },
        )

        try:
            res = await litellm.aembedding(
                model=self._config.embed_model,
                input=texts,
                api_key=self._config.embed_api_key,
                encoding_format="float"
                if self._config.embed_model.startswith("nvidia_nim/")
                else None,
            )
            embeddings: list[list[float] | None] = [
                item["embedding"] for item in res.data
            ]
            lf.update_current_span(output={"embedding_count": len(embeddings)})
            return embeddings
        except Exception as exc:
            logger.error("failed to generate embeddings: %s.", exc)
            lf.update_current_span(
                level="ERROR",
                status_message=f"embedding generation failed: {exc}",
            )
            return [None] * len(texts)

    async def aclose(self) -> None:
        if self._config.tracing_enabled:
            lf = get_client()
            lf.flush()
            logger.info("langfuse client flushed.")
        logger.info("closing llm service resources.")
