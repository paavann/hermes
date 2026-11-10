from __future__ import annotations

import json
import logging

from litellm.router import Router
from litellm.types.router import DeploymentTypedDict, LiteLLMParamsTypedDict
from pydantic import BaseModel, ValidationError

from hermes_ai.core.config import AiConfig, ModelRoute
from hermes_ai.exceptions import (
    ConfigurationError,
    ModelExecutionError,
    SchemaValidationError,
)
from hermes_ai.services.langfuse import configure_langfuse, flush_langfuse
from hermes_ai.utils.rate_limiter import TbRateLimiter


logger = logging.getLogger(__name__)


def _deployment(
    name: str,
    model: str,
    api_key: str,
    rpm: int | None = None,
) -> DeploymentTypedDict:
    params: LiteLLMParamsTypedDict = {"model": model, "api_key": api_key}
    if rpm is not None:
        params["rpm"] = rpm
    return {"model_name": name, "litellm_params": params}


def _clean_json_str(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned


def _fallback_alias(role: str, index: int, total: int) -> str:
    return f"{role}-fallback" if total == 1 else f"{role}-fallback-{index}"


def _build_deployments(
    routes: dict[str, ModelRoute],
) -> tuple[list[DeploymentTypedDict], list[dict[str, list[str]]]]:
    model_list: list[DeploymentTypedDict] = []
    fallbacks: list[dict[str, list[str]]] = []

    for name, route in routes.items():
        model_list.append(
            _deployment(
                name,
                route.primary.model,
                route.primary.api_key,
                route.primary.rpm,
            )
        )
        fb_names: list[str] = []
        total_fallbacks = len(route.fallbacks)
        for idx, fb in enumerate(route.fallbacks, start=1):
            fb_alias = _fallback_alias(name, idx, total_fallbacks)
            model_list.append(_deployment(fb_alias, fb.model, fb.api_key, fb.rpm))
            fb_names.append(fb_alias)
        if fb_names:
            fallbacks.append({name: fb_names})

    return model_list, fallbacks


class LlmService:
    def __init__(self, config: AiConfig) -> None:
        self._config = config
        model_list, fallbacks = _build_deployments(config.routes)
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
        embed_route = config.routes.get("embed")
        self._embed_rate_limiter = (
            TbRateLimiter(embed_route.primary.rpm)
            if (embed_route and embed_route.primary.rpm)
            else None
        )

        if config.tracing_enabled:
            configure_langfuse(config)

        logger.info(
            "llm service initialized with routes: %s via litellm router.",
            list(config.routes.keys()),
        )

    @property
    def config(self) -> AiConfig:
        return self._config

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

    async def call_llm[T: BaseModel](
        self,
        sys_prompt: str,
        user_prompt: str,
        res_model: type[T],
        schema_name: str,
    ) -> T:
        if "extractor" not in self._config.routes:
            raise ConfigurationError("extractor route is required for extraction.")
        try:
            return await self._invoke_and_parse(
                "extractor",
                sys_prompt,
                user_prompt,
                res_model,
                schema_name,
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as val_err:
            logger.error(
                "llm output validation failed for %s: %s.", schema_name, val_err
            )
            raise SchemaValidationError(
                f"llm output validation failed for {schema_name}: {val_err}.",
                schema_name=schema_name,
                validation_error=val_err,
            ) from val_err
        except Exception as exc:
            logger.error("llm call failed for %s: %s.", schema_name, exc)
            raise ModelExecutionError(
                f"llm call failed for {schema_name}: {exc}.",
                schema_name=schema_name,
                original_exception=exc,
            ) from exc

    async def gen_embeddings(self, texts: list[str]) -> list[list[float] | None]:
        if not texts:
            return []
        elif not self._config.has_embed:
            logger.error("embed route is missing from configuration.")
            return [None] * len(texts)
        elif self._embed_rate_limiter:
            await self._embed_rate_limiter.acquire()
        try:
            embed_route = self._config.routes.get("embed")
            encoding_format = (
                "float"
                if (embed_route and embed_route.primary.model.startswith("nvidia_nim/"))
                else None
            )
            res = await self._router.aembedding(
                model="embed",
                input=texts,
                encoding_format=encoding_format,
            )
            embeddings: list[list[float] | None] = [
                item["embedding"] for item in res.data
            ]
            return embeddings
        except Exception as exc:
            logger.error("failed to generate embeddings: %s.", exc)
            return [None] * len(texts)

    async def aclose(self) -> None:
        if self._config.tracing_enabled:
            flush_langfuse()
        logger.info("closing llm service resources.")
