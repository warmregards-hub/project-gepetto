import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings


class EndpointRegistry:
    def __init__(self, path: str):
        self.path = Path(path)
        self.data: Dict[str, Any] = {
            "version": 1,
            "updated_at": self._now(),
            "models": {},
        }

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            self.save()
            return self.data
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                parsed = json.load(f)
            if isinstance(parsed, dict):
                self.data = parsed
        except Exception:
            self.data = {
                "version": 1,
                "updated_at": self._now(),
                "models": {},
            }
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = self._now()
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        temp.replace(self.path)

    def _ensure_endpoint(self, model: str, kind: str, endpoint: str) -> Dict[str, Any]:
        models = self.data.setdefault("models", {})
        model_entry = models.setdefault(model, {})
        kind_entry = model_entry.setdefault(
            kind,
            {
                "status": "unknown",
                "last_success_url": None,
                "last_failure_url": None,
                "endpoints": {},
            },
        )
        return kind_entry.setdefault(
            "endpoints", {}
        ).setdefault(
            endpoint,
            {
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "last_success": None,
                "last_failure": None,
                "last_status_code": None,
                "last_error_type": None,
                "last_error_message": None,
                "last_params": {},
            },
        )

    def get_candidates(self, model: str, kind: str, defaults: List[str]) -> List[str]:
        model_entry = self.data.setdefault("models", {}).setdefault(model, {})
        kind_entry = model_entry.setdefault(kind, {"endpoints": {}})
        endpoints = kind_entry.setdefault("endpoints", {})
        known = sorted(
            endpoints.keys(),
            key=lambda url: (
                -int(endpoints[url].get("success_count", 0)),
                int(endpoints[url].get("consecutive_failures", 0)),
                int(endpoints[url].get("failure_count", 0)),
            ),
        )
        merged: List[str] = []
        for endpoint in known + defaults:
            if endpoint not in merged:
                merged.append(endpoint)
        return merged

    def record_success(self, model: str, kind: str, endpoint: str, params: Dict[str, Any]) -> None:
        endpoint_entry = self._ensure_endpoint(model, kind, endpoint)
        endpoint_entry["success_count"] = int(endpoint_entry.get("success_count", 0)) + 1
        endpoint_entry["consecutive_failures"] = 0
        endpoint_entry["last_success"] = self._now()
        endpoint_entry["last_status_code"] = 200
        endpoint_entry["last_error_type"] = None
        endpoint_entry["last_error_message"] = None
        endpoint_entry["last_params"] = params

        kind_entry = self.data["models"][model][kind]
        kind_entry["status"] = "healthy"
        kind_entry["last_success_url"] = endpoint
        self.save()

    def record_failure(
        self,
        model: str,
        kind: str,
        endpoint: str,
        error_type: str,
        status_code: Optional[int],
        message: str,
    ) -> None:
        endpoint_entry = self._ensure_endpoint(model, kind, endpoint)
        endpoint_entry["failure_count"] = int(endpoint_entry.get("failure_count", 0)) + 1
        endpoint_entry["consecutive_failures"] = int(endpoint_entry.get("consecutive_failures", 0)) + 1
        endpoint_entry["last_failure"] = self._now()
        endpoint_entry["last_status_code"] = status_code
        endpoint_entry["last_error_type"] = error_type
        endpoint_entry["last_error_message"] = message[:500]

        kind_entry = self.data["models"][model][kind]
        kind_entry["last_failure_url"] = endpoint
        max_failures = max(
            (int(entry.get("consecutive_failures", 0)) for entry in kind_entry.get("endpoints", {}).values()),
            default=0,
        )
        kind_entry["status"] = "down" if max_failures >= 3 else "degraded"
        self.save()

    def sort_models(self, kind: str, models: List[str]) -> List[str]:
        deduped: List[str] = []
        for model in models:
            if model not in deduped:
                deduped.append(model)

        def rank(model: str) -> tuple[int, int, int]:
            kind_entry = self.data.get("models", {}).get(model, {}).get(kind, {})
            status = kind_entry.get("status", "unknown")
            status_score = {"healthy": 3, "degraded": 2, "unknown": 1, "down": 0}.get(status, 1)
            endpoints = kind_entry.get("endpoints", {})
            success = sum(int(entry.get("success_count", 0)) for entry in endpoints.values())
            failure = sum(int(entry.get("failure_count", 0)) for entry in endpoints.values())
            return (status_score, success, -failure)

        return sorted(deduped, key=rank, reverse=True)


class KieClient:
    IMAGE_FALLBACKS = ["gpt-image-1", "nano-banana-pro", "flux-kontext", "midjourney"]
    VIDEO_FALLBACKS = ["veo-3.1-fast", "veo-3.1", "kling", "runway-aleph", "sora2"]

    def __init__(self):
        self.api_key = (settings.kie_api_key or "").strip()
        base_url = settings.kie_base_url.rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=60.0,
        )
        self.registry = EndpointRegistry(settings.endpoint_registry_path)
        self.registry.load()
        self.model_cache_path = Path(settings.model_cache_path)

    @staticmethod
    def initialize_registry() -> None:
        EndpointRegistry(settings.endpoint_registry_path).load()

    async def chat_completion(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        model = settings.kie_chat_model
        payload: Dict[str, Any] = {"model": model, "messages": messages}
        if settings.kie_chat_reasoning:
            payload["reasoning"] = settings.kie_chat_reasoning
        payload["temperature"] = settings.kie_chat_temperature
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        endpoints = [f"{self.base_url}/{model}/v1/chat/completions"]
        last_error = None
        for endpoint in endpoints:
            result = await self._post_with_retries(endpoint, payload, model, "chat")
            if result["ok"]:
                return result["data"]
            print(f"[Project Gepetto Kie Client] Chat endpoint failed: {endpoint} -> {result}")
            last_error = result
        print(f"[Project Gepetto Kie Client] Chat failed across endpoints: {last_error}")
        return {"choices": [{"message": {"role": "assistant", "content": "I hit a temporary backend issue. Please retry in a moment."}}]}

    def _load_model_cache(self) -> Dict[str, Any]:
        if not self.model_cache_path.exists():
            return {"models": []}
        try:
            with open(self.model_cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            return {"models": []}
        return {"models": []}

    def _save_model_cache(self, payload: Dict[str, Any]) -> None:
        self.model_cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.model_cache_path.with_suffix(self.model_cache_path.suffix + ".tmp")
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        temp.replace(self.model_cache_path)

    async def list_models(self, query: Optional[str] = None, kind: str = "any") -> Dict[str, Any]:
        endpoints = self.registry.get_candidates(
            "models",
            "list",
            [
                f"{self.base_url}/v1/models",
                f"{self.base_url}/models",
                f"{self.base_url}/api/v1/models",
            ],
        )

        last_error = None
        for endpoint in endpoints:
            result = await self._get_with_retries(endpoint, "models", "list")
            if result["ok"]:
                data = result["data"]
                self._save_model_cache(data)
                return self._filter_models(data, query=query, kind=kind)
            last_error = result

        cached = self._load_model_cache()
        filtered = self._filter_models(cached, query=query, kind=kind)
        filtered["cache_only"] = True
        filtered["error"] = str(last_error.get("error_type") if isinstance(last_error, dict) else "unknown")
        return filtered

    def _filter_models(self, payload: Dict[str, Any], query: Optional[str], kind: str) -> Dict[str, Any]:
        models = payload.get("models") or payload.get("data") or []
        if isinstance(models, dict):
            models = [models]
        if not isinstance(models, list):
            models = []

        filtered: List[Dict[str, Any]] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = str(item.get("id") or item.get("name") or "")
            item_kind = str(item.get("type") or item.get("kind") or "any")
            if query and query.lower() not in name.lower():
                continue
            if kind != "any" and kind != item_kind:
                continue
            filtered.append(item)

        return {"models": filtered}

    async def generate_images(
        self,
        prompts: List[str],
        model: str,
        size: str = "1024x1024",
        callback_url: Optional[str] = None,
        project_id: Optional[str] = None,
        allow_fallbacks: bool = False,
    ) -> Dict[str, Any]:
        if settings.mock_generation:
            return {
                "ok": True,
                "urls": [f"mock_image_{uuid.uuid4().hex}_{i}.jpg" for i in range(len(prompts))],
                "model_used": model,
                "endpoint_used": "mock://images",
                "pending_callback": False,
            }
            
        all_urls: List[str] = []
        pending_tasks: List[str] = []
        errors: List[Dict[str, Any]] = []
        model_used = model
        
        for prompt in prompts:
            result = await self._generate(
                kind="image",
                prompt=prompt,
                requested_model=model,
                count=1,
                callback_url=callback_url,
                project_id=project_id,
                size=size,
                allow_fallbacks=allow_fallbacks,
            )
            if not result.get("ok"):
                errors.append(result)
            else:
                all_urls.extend(result.get("urls", []))
                if result.get("pending_callback") and result.get("task_id"):
                    pending_tasks.append(result["task_id"])
                model_used = result.get("model_used", model_used)
                
        if errors and not all_urls and not pending_tasks:
            return {
                "ok": False,
                "message": errors[0].get("message", "All prompts failed"),
                "errors": errors,
            }
            
        return {
            "ok": True,
            "urls": all_urls,
            "model_used": model_used,
            "pending_callback": len(pending_tasks) > 0,
            "task_ids": pending_tasks,
            "errors": errors if errors else None
        }

    async def generate_video(
        self,
        prompt: str,
        model: str,
        callback_url: Optional[str] = None,
        project_id: Optional[str] = None,
        allow_fallbacks: bool = False,
    ) -> Dict[str, Any]:
        if settings.mock_generation:
            return {
                "ok": True,
                "urls": [f"mock_video_{uuid.uuid4().hex}.mp4"],
                "model_used": model,
                "endpoint_used": "mock://videos",
                "pending_callback": False,
            }
        return await self._generate(
            kind="video",
            prompt=prompt,
            requested_model=model,
            count=1,
            callback_url=callback_url,
            project_id=project_id,
            allow_fallbacks=allow_fallbacks,
        )

    async def _generate(
        self,
        kind: str,
        prompt: str,
        requested_model: str,
        count: int,
        callback_url: Optional[str],
        project_id: Optional[str],
        size: str = "1024x1024",
        allow_fallbacks: bool = False,
    ) -> Dict[str, Any]:
        if kind == "image" and self._use_jobs_api():
            return await self._generate_via_jobs_api(
                prompt=prompt,
                requested_model=requested_model,
                callback_url=callback_url,
                size=size,
            )

        payload_base: Dict[str, Any] = {"prompt": prompt}
        if kind == "image":
            payload_base["n"] = count
            payload_base["size"] = size
        if project_id:
            payload_base["client_id"] = project_id

        use_callback = bool(callback_url and settings.environment != "development")
        if use_callback:
            payload_base["callBackUrl"] = callback_url

        sequence = self._model_sequence(kind, requested_model) if allow_fallbacks else [requested_model]
        errors: List[Dict[str, Any]] = []

        for model in sequence:
            payload = dict(payload_base)
            payload["model"] = model
            endpoints = self.registry.get_candidates(model, kind, self._generation_endpoints(kind, model))
            if not use_callback:
                endpoints = [ep for ep in endpoints if "/api/v1/generate" not in ep and "/api/v1/video/generate" not in ep]

            for endpoint in endpoints:
                post_result = await self._post_with_retries(endpoint, payload, model, kind)
                if not post_result["ok"]:
                    errors.append(post_result)
                    continue

                data = post_result["data"]
                urls = self._extract_urls(data)
                if urls:
                    return {
                        "ok": True,
                        "urls": urls,
                        "model_used": model,
                        "endpoint_used": endpoint,
                        "pending_callback": False,
                    }

                task_id = self._extract_task_id(data)
                if not task_id:
                    errors.append(
                        {
                            "ok": False,
                            "model": model,
                            "endpoint": endpoint,
                            "error_type": "invalid_response",
                            "message": "No task_id returned",
                        }
                    )
                    continue

                if use_callback:
                    return {
                        "ok": True,
                        "urls": [],
                        "task_id": task_id,
                        "model_used": model,
                        "endpoint_used": endpoint,
                        "pending_callback": True,
                    }

                poll_result = await self._poll_task(task_id, model, kind)
                if poll_result["ok"]:
                    return {
                        "ok": True,
                        "urls": poll_result.get("urls", []),
                        "task_id": task_id,
                        "model_used": model,
                        "endpoint_used": endpoint,
                        "pending_callback": False,
                    }

                errors.append(poll_result)

        suggested = self._suggest_alternative(kind, requested_model)
        return {
            "ok": False,
            "requested_model": requested_model,
            "suggested_model": suggested,
            "message": self._friendly_failure(requested_model, suggested),
            "errors": errors,
        }

    def _use_jobs_api(self) -> bool:
        return "kie.ai" in self.base_url

    def _size_to_aspect_ratio(self, size: str) -> str:
        if not size:
            return "1:1"
        if ":" in size:
            return size
        mapping = {
            "1024x1792": "9:16",
            "1792x1024": "16:9",
            "1024x1024": "1:1",
        }
        return mapping.get(size, "1:1")

    async def _generate_via_jobs_api(
        self,
        prompt: str,
        requested_model: str,
        callback_url: Optional[str],
        size: str,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": requested_model,
            "input": {
                "prompt": prompt,
                "aspect_ratio": self._size_to_aspect_ratio(size),
            },
        }
        if callback_url:
            payload["callBackUrl"] = callback_url

        endpoint = f"{self.base_url}/api/v1/jobs/createTask"
        post_result = await self._post_with_retries(endpoint, payload, requested_model, "image")
        if not post_result["ok"]:
            return post_result

        data = post_result["data"]
        if isinstance(data, dict):
            code = data.get("code")
            if code not in (200, "200"):
                return {
                    "ok": False,
                    "error_type": "api_error",
                    "status_code": int(code) if isinstance(code, str) and code.isdigit() else 500,
                    "endpoint": endpoint,
                    "message": str(data.get("msg") or "Unknown API error"),
                    "model": requested_model,
                }
            task_id = None
            payload_data = data.get("data") if isinstance(data.get("data"), dict) else {}
            if isinstance(payload_data, dict):
                task_id = payload_data.get("taskId")
            if not task_id:
                return {
                    "ok": False,
                    "error_type": "invalid_response",
                    "message": "No taskId returned",
                    "endpoint": endpoint,
                    "model": requested_model,
                }

            if callback_url:
                return {
                    "ok": True,
                    "urls": [],
                    "task_id": str(task_id),
                    "model_used": requested_model,
                    "endpoint_used": endpoint,
                    "pending_callback": True,
                }

            poll_result = await self._poll_job_task(str(task_id), requested_model)
            if poll_result.get("ok"):
                return {
                    "ok": True,
                    "urls": poll_result.get("urls", []),
                    "task_id": str(task_id),
                    "model_used": requested_model,
                    "endpoint_used": poll_result.get("endpoint", endpoint),
                    "pending_callback": False,
                }
            return poll_result

        return {
            "ok": False,
            "error_type": "invalid_response",
            "message": "Unexpected response payload",
            "endpoint": endpoint,
            "model": requested_model,
        }

    async def _poll_job_task(self, task_id: str, model: str) -> Dict[str, Any]:
        endpoint = f"{self.base_url}/api/v1/jobs/recordInfo?taskId={task_id}"
        for _ in range(40):
            await asyncio.sleep(3)
            result = await self._get_with_retries(endpoint, model, "poll_image")
            if not result["ok"]:
                continue
            data = result["data"]
            if not isinstance(data, dict):
                continue
            code = data.get("code")
            if code not in (200, "200"):
                continue
            payload = data.get("data") if isinstance(data.get("data"), dict) else {}
            state = str(payload.get("state") or "").lower()
            if state == "success":
                result_json = payload.get("resultJson")
                urls: List[str] = []
                if isinstance(result_json, str):
                    try:
                        parsed = json.loads(result_json)
                        if isinstance(parsed, dict):
                            urls = parsed.get("resultUrls") or []
                    except Exception:
                        urls = []
                if isinstance(result_json, dict):
                    urls = result_json.get("resultUrls") or []
                return {"ok": True, "urls": urls, "endpoint": endpoint}
            if state == "fail":
                return {
                    "ok": False,
                    "error_type": "task_failed",
                    "message": str(payload.get("failMsg") or "Task failed"),
                    "endpoint": endpoint,
                }

        return {
            "ok": False,
            "error_type": "timeout",
            "message": f"Task {task_id} timed out",
            "endpoint": endpoint,
        }

    async def _poll_task(self, task_id: str, model: str, kind: str) -> Dict[str, Any]:
        poll_kind = f"poll_{kind}"
        endpoints = self.registry.get_candidates(model, poll_kind, self._poll_endpoints(model, task_id))
        for _ in range(40):
            await asyncio.sleep(3)
            for endpoint in endpoints:
                result = await self._get_with_retries(endpoint, model, poll_kind)
                if not result["ok"]:
                    continue
                data = result["data"]
                status = str(data.get("status", "")).lower()
                if status in ("succeeded", "completed", "success"):
                    return {"ok": True, "urls": self._extract_urls(data), "endpoint_used": endpoint}
                if status in ("failed", "error", "cancelled"):
                    return {
                        "ok": False,
                        "error_type": "task_failed",
                        "message": f"Task {task_id} failed",
                        "endpoint": endpoint,
                    }
        return {
            "ok": False,
            "error_type": "timeout",
            "message": f"Task {task_id} timed out",
            "endpoint": "task_poll",
        }

    async def _post_with_retries(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        model: str,
        kind: str,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        retryable = {408, 409, 425, 429, 500, 502, 503, 504}
        backoff = [1, 3, 9]
        for attempt in range(max_attempts):
            try:
                response = await self.client.post(endpoint, json=payload)
                if response.status_code in retryable and attempt < max_attempts - 1:
                    self.registry.record_failure(model, kind, endpoint, "retryable_status", response.status_code, response.text)
                    await asyncio.sleep(backoff[min(attempt, len(backoff) - 1)])
                    continue
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, dict):
                    api_code = str(data.get("code", "200"))
                    if api_code != "200" and api_code != "0" and api_code != "None":
                        msg = data.get("msg") or data.get("message") or "Unknown API logic error"
                        if api_code in ["408", "429", "500", "502", "503", "504"] and attempt < max_attempts - 1:
                            self.registry.record_failure(model, kind, endpoint, "api_error_retryable", 500, msg)
                            await asyncio.sleep(backoff[min(attempt, len(backoff) - 1)])
                            continue
                        self.registry.record_failure(model, kind, endpoint, "api_error", 500, msg)
                        return {
                            "ok": False,
                            "error_type": "api_error",
                            "status_code": int(api_code) if api_code.isdigit() else 500,
                            "endpoint": endpoint,
                            "message": msg[:500],
                            "model": model,
                        }

                self.registry.record_success(model, kind, endpoint, payload)
                print(f"[Project Gepetto Kie Client] SUCCESS kind={kind} model={model} endpoint={endpoint} payload={payload}")
                return {"ok": True, "data": data, "endpoint": endpoint}
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                body = e.response.text
                self.registry.record_failure(model, kind, endpoint, "http_status", status, body)
                if status in retryable and attempt < max_attempts - 1:
                    await asyncio.sleep(backoff[min(attempt, len(backoff) - 1)])
                    continue
                return {
                    "ok": False,
                    "error_type": "http_status",
                    "status_code": status,
                    "endpoint": endpoint,
                    "message": body[:500],
                    "model": model,
                }
            except (httpx.TimeoutException, httpx.RequestError) as e:
                self.registry.record_failure(model, kind, endpoint, "request_error", None, str(e))
                if attempt < max_attempts - 1:
                    await asyncio.sleep(backoff[min(attempt, len(backoff) - 1)])
                    continue
                return {
                    "ok": False,
                    "error_type": "request_error",
                    "status_code": None,
                    "endpoint": endpoint,
                    "message": str(e),
                    "model": model,
                }
        return {
            "ok": False,
            "error_type": "unknown",
            "status_code": None,
            "endpoint": endpoint,
            "message": "Unknown post failure",
            "model": model,
        }

    async def _get_with_retries(
        self,
        endpoint: str,
        model: str,
        kind: str,
        max_attempts: int = 2,
    ) -> Dict[str, Any]:
        retryable = {408, 409, 425, 429, 500, 502, 503, 504}
        backoff = [1, 3]
        for attempt in range(max_attempts):
            try:
                response = await self.client.get(endpoint)
                if response.status_code in retryable and attempt < max_attempts - 1:
                    self.registry.record_failure(model, kind, endpoint, "retryable_status", response.status_code, response.text)
                    await asyncio.sleep(backoff[min(attempt, len(backoff) - 1)])
                    continue
                response.raise_for_status()
                data = response.json()
                self.registry.record_success(model, kind, endpoint, {"method": "GET"})
                return {"ok": True, "data": data, "endpoint": endpoint}
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                body = e.response.text
                self.registry.record_failure(model, kind, endpoint, "http_status", status, body)
                if status in retryable and attempt < max_attempts - 1:
                    await asyncio.sleep(backoff[min(attempt, len(backoff) - 1)])
                    continue
                return {
                    "ok": False,
                    "error_type": "http_status",
                    "status_code": status,
                    "endpoint": endpoint,
                    "message": body[:500],
                }
            except (httpx.TimeoutException, httpx.RequestError) as e:
                self.registry.record_failure(model, kind, endpoint, "request_error", None, str(e))
                if attempt < max_attempts - 1:
                    await asyncio.sleep(backoff[min(attempt, len(backoff) - 1)])
                    continue
                return {
                    "ok": False,
                    "error_type": "request_error",
                    "status_code": None,
                    "endpoint": endpoint,
                    "message": str(e),
                }
        return {
            "ok": False,
            "error_type": "unknown",
            "status_code": None,
            "endpoint": endpoint,
            "message": "Unknown get failure",
        }

    def _extract_task_id(self, data: Dict[str, Any]) -> Optional[str]:
        task_id = data.get("task_id") or data.get("id")
        if task_id:
            return str(task_id)
        payload = data.get("data")
        if isinstance(payload, dict):
            nested = payload.get("task_id") or payload.get("id")
            if nested:
                return str(nested)
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                nested = first.get("task_id") or first.get("id")
                if nested:
                    return str(nested)
        return None

    def _extract_urls(self, data: Dict[str, Any]) -> List[str]:
        urls: List[str] = []
        if isinstance(data.get("url"), str):
            urls.append(data["url"])
        for key in ("data", "output", "result"):
            payload = data.get(key)
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and isinstance(item.get("url"), str):
                        urls.append(item["url"])
                    elif isinstance(item, str):
                        urls.append(item)
            elif isinstance(payload, dict) and isinstance(payload.get("url"), str):
                urls.append(payload["url"])
            elif isinstance(payload, str):
                urls.append(payload)
        deduped: List[str] = []
        for url in urls:
            if url not in deduped:
                deduped.append(url)
        return deduped

    def _generation_endpoints(self, kind: str, model: str) -> List[str]:
        if kind == "image":
            return [
                f"{self.base_url}/{model}/v1/images/generations",
                f"{self.base_url}/v1/images/generations",
                f"{self.base_url}/images/generations",
                f"{self.base_url}/{model}/api/v1/generate",
                f"{self.base_url}/api/v1/generate",
            ]
        return [
            f"{self.base_url}/{model}/v1/videos/generations",
            f"{self.base_url}/v1/videos/generations",
            f"{self.base_url}/videos/generations",
            f"{self.base_url}/{model}/api/v1/video/generate",
            f"{self.base_url}/api/v1/video/generate",
        ]

    def _poll_endpoints(self, model: str, task_id: str) -> List[str]:
        return [
            f"{self.base_url}/v1/task/{task_id}",
            f"{self.base_url}/task/{task_id}",
            f"{self.base_url}/api/v1/task/{task_id}",
            f"{self.base_url}/{model}/v1/task/{task_id}",
        ]

    def _model_sequence(self, kind: str, requested_model: str) -> List[str]:
        defaults = self.IMAGE_FALLBACKS if kind == "image" else self.VIDEO_FALLBACKS
        models = [requested_model] + [model for model in defaults if model != requested_model]
        return self.registry.sort_models(kind, models)

    def _suggest_alternative(self, kind: str, requested_model: str) -> Optional[str]:
        for model in self._model_sequence(kind, requested_model):
            if model != requested_model:
                return model
        return None

    def _friendly_failure(self, requested_model: str, suggested_model: Optional[str]) -> str:
        if suggested_model:
            return f"Couldn't reach {requested_model}. Want me to try {suggested_model}?"
        return f"Couldn't reach {requested_model}. Want me to try a different model?"
