import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.services.cost_tracker import CostTracker
from app.services.kie_client import KieClient
from app.services.learning_engine import LearningEngine
from app.services.n8n_client import N8nClient
from app.services.storage_service import StorageService
from app.services.drive_service import DriveService
from app.services.notification_service import NotificationService
from app.models.generation import GeneratedAsset
from app.models.conversation import Conversation


class GeminiAgentService:
    def __init__(self, db_session, session_id: Optional[str] = None):
        self.kie_client = KieClient()
        self.storage = StorageService()
        self.learning = LearningEngine()
        self.n8n = N8nClient("https://dummy_webhook")
        self.cost_tracker = CostTracker(db_session)
        self.drive = DriveService()
        self.notifier = NotificationService()
        self.db = db_session
        self.session_id = session_id

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_available_models",
                    "description": "List available models and metadata (name, type, pricing, status).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "kind": {"type": "string", "enum": ["image", "video", "chat", "any"]},
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_images",
                    "description": "Generate one or more distinct images using the specified model.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompts": {"type": "array", "items": {"type": "string"}},
                            "model": {"type": "string"},
                            "size": {"type": "string"},
                            "project_id": {"type": "string"},
                            "style_overrides": {"type": "object"},
                            "confirm_plan": {"type": "boolean"},
                        },
                        "required": ["prompts", "project_id", "model"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_videos",
                    "description": "Generate videos with Kie.ai",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompts": {"type": "array", "items": {"type": "string"}},
                            "model": {"type": "string"},
                            "project_id": {"type": "string"},
                            "reference_images": {"type": "array", "items": {"type": "string"}},
                            "confirm_plan": {"type": "boolean"},
                        },
                        "required": ["prompts", "project_id", "model"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "save_to_storage",
                    "description": "Save files to local storage",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "files": {"type": "array", "items": {"type": "string"}},
                            "project_id": {"type": "string"},
                            "subfolder": {"type": "string"},
                        },
                        "required": ["files", "project_id", "subfolder"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_n8n_workflow",
                    "description": "Trigger n8n workflow",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "workflow_name": {
                                "type": "string",
                                "enum": ["ugc-batch", "video-render", "script-process", "voice-generate"],
                            },
                            "payload": {"type": "object"},
                        },
                        "required": ["workflow_name", "payload"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_project_preferences",
                    "description": "Read project preferences and learned patterns",
                    "parameters": {
                        "type": "object",
                        "properties": {"project_id": {"type": "string"}},
                        "required": ["project_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_project_preferences",
                    "description": "Update project preferences",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "updates": {"type": "object"},
                        },
                        "required": ["project_id", "updates"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "log_cost",
                    "description": "Log cost entry",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount_usd": {"type": "number"},
                            "service": {
                                "type": "string",
                                "enum": ["kie-chat", "kie-image", "kie-video", "kie-vision", "elevenlabs"],
                            },
                            "model": {"type": "string"},
                            "project_id": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["amount_usd", "service", "model", "project_id", "description"],
                    },
                },
            },
        ]

    def _build_callback_url(self, base_url: str, project_id: Optional[str]) -> str:
        url = f"{base_url}/api/kie/callback"
        params: List[str] = []
        if project_id:
            params.append(f"project_id={project_id}")
        if self.session_id:
            params.append(f"session_id={self.session_id}")
        if params:
            return url + "?" + "&".join(params)
        return url

    async def _upload_to_drive(self, filename: str, content: bytes) -> Optional[Dict[str, Any]]:
        if not self.drive.is_enabled():
            return None
        return await asyncio.to_thread(self.drive.upload_bytes, filename, content)

    def _remove_local_file(self, path: str) -> None:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            return

    async def _touch_session(self) -> None:
        if not self.session_id or not self.db:
            return
        convo = await self.db.get(Conversation, self.session_id)
        if not convo:
            return
        convo.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def _record_asset(
        self,
        asset_type: str,
        file_path: str,
        drive_info: Optional[Dict[str, Any]],
        prompt: str,
    ) -> None:
        if not self.db:
            return
        asset = GeneratedAsset(
            job_id=None,
            conversation_id=self.session_id,
            asset_type=asset_type,
            file_path=file_path,
            drive_id=drive_info.get("id") if drive_info else None,
            drive_url=drive_info.get("webViewLink") if drive_info else None,
            drive_direct_url=drive_info.get("directUrl") if drive_info else None,
            original_prompt=prompt,
        )
        self.db.add(asset)
        await self.db.commit()
        await self._touch_session()

    async def _notify_completion(self, asset_count: int, link: Optional[str]) -> None:
        if not link:
            return
        title = "Geppetto Complete"
        session_name = None
        if self.session_id and self.db:
            convo = await self.db.get(Conversation, self.session_id)
            if convo:
                session_name = convo.name or None
        message = f"Generated {asset_count} asset(s)."
        if session_name:
            message = f"{session_name} complete. {message}"
        await self.notifier.notify(title, message, link)

    async def _broadcast(self, event: Dict[str, Any]) -> None:
        try:
            from app.api.routes.agent import manager
            await manager.broadcast(event)
        except Exception:
            return

    def _debug_log(self, message: str) -> None:
        try:
            log_path = Path(__file__).resolve().parents[2] / "agent_debug.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception:
            return

    async def _download_asset(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    def _planner_system_prompt(self, project_id: str, preferences_md: str, learned_patterns: Dict[str, Any]) -> str:
        learned_blob = json.dumps(learned_patterns, ensure_ascii=False)
        template = """You are the Geppetto orchestration brain. Return a single JSON object and nothing else. Do not wrap in markdown or code fences.

Valid response types:
1) {{"action":"question", "message":"..."}}
2) {{"action":"plan", "kind":"image"|"video", "project_id":"...", "confirm":true|false, "batches":[{{"model":"...", "prompts":[...], "count":1, "size":"...", "ratio":"..."}}]}}
3) {{"action":"chat", "message":"..."}}

If you need missing info (model, count, ratio, etc.), return action=question.
If you can build a plan, return action=plan.
If the user is just chatting, return action=chat.

If a pending plan exists in history, it is inside <plan>{{...}}</plan>. When the user gives ANY affirmative response (e.g., "looks good", "send it", "yes", "do it", "confirm"), you MUST return action=plan with confirm=true and copy the plan EXACTLY (including batches). Do not modify prompts.
If there is no pending plan in history, confirm MUST be false.
If the user requests edits or specifies changes, return action=plan with confirm=false and generate a NEW plan.

Multi-model requests:
- When the user asks for the same prompt across multiple models, return one batch per model.
- There is no limitation on using multiple models in a single plan. Do not invent restrictions.

Plan requirements:
- prompts must be production-quality and highly enriched. Include subject, setting, lighting, camera/lens, mood, composition.
- IMPORTANT: You MUST strictly integrate the "Project preferences" and "Learned patterns" provided below into the final prompt text.
- do not introduce new entities or locations not implied by the request.
- prompts array length must equal count for each batch.
- for image batches, include BOTH size and ratio.
- use size values: 1024x1024 (1:1), 1024x1792 (9:16), 1792x1024 (16:9), 1024x768 (4:3), 768x1024 (3:4).
- never claim a limitation unless it is a real technical constraint or API error.

Current project_id: {project_id}

Project preferences (apply):
{preferences_md}

Learned patterns (apply):
{learned_blob}
"""
        return template.format(
            project_id=project_id,
            preferences_md=preferences_md,
            learned_blob=learned_blob,
        )

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item, dict) and isinstance(item.get("content"), str):
                    parts.append(item["content"])
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)
        return ""

    def _parse_llm_payload(self, content: Any) -> Optional[Dict[str, Any]]:
        text = self._extract_text(content).strip()
        if not text:
            return None
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                payload = json.loads(text[start : end + 1])
                if isinstance(payload, dict):
                    return payload
            except Exception:
                return None
        return None

    def _validate_llm_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        action = payload.get("action")
        if action not in {"question", "plan", "chat"}:
            return None
        return payload

    def _normalize_plan(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if payload.get("action") != "plan":
            return None
        kind = payload.get("kind")
        if kind not in {"image", "video"}:
            return None
        project_id = payload.get("project_id")
        if not isinstance(project_id, str) or not project_id.strip():
            return None
        confirm = bool(payload.get("confirm"))

        batches = payload.get("batches")
        normalized_batches: List[Dict[str, Any]] = []

        if batches is None:
            model = payload.get("model")
            prompts = payload.get("prompts")
            count = payload.get("count")
            if not isinstance(model, str) or not model.strip():
                return None
            if not isinstance(prompts, list) or not prompts:
                return None
            if not isinstance(count, int) or count != len(prompts):
                return None
            for prompt in prompts:
                if not isinstance(prompt, str) or not prompt.strip():
                    return None
            batch: Dict[str, Any] = {
                "model": model,
                "prompts": prompts,
                "count": count,
            }
            if kind == "image":
                size = payload.get("size")
                ratio = payload.get("ratio")
                if not isinstance(size, str) or not size.strip():
                    return None
                if not isinstance(ratio, str) or not ratio.strip():
                    return None
                batch["size"] = size
                batch["ratio"] = ratio
            normalized_batches.append(batch)
        else:
            if not isinstance(batches, list) or not batches:
                return None
            for batch in batches:
                if not isinstance(batch, dict):
                    return None
                model = batch.get("model")
                prompts = batch.get("prompts")
                count = batch.get("count")
                if not isinstance(model, str) or not model.strip():
                    return None
                if not isinstance(prompts, list) or not prompts:
                    return None
                if not isinstance(count, int) or count != len(prompts):
                    return None
                for prompt in prompts:
                    if not isinstance(prompt, str) or not prompt.strip():
                        return None
                normalized_batch: Dict[str, Any] = {
                    "model": model,
                    "prompts": prompts,
                    "count": count,
                }
                if kind == "image":
                    size = batch.get("size") or payload.get("size")
                    ratio = batch.get("ratio") or payload.get("ratio")
                    if not isinstance(size, str) or not size.strip():
                        return None
                    if not isinstance(ratio, str) or not ratio.strip():
                        return None
                    normalized_batch["size"] = size
                    normalized_batch["ratio"] = ratio
                normalized_batches.append(normalized_batch)

        return {
            "action": "plan",
            "kind": kind,
            "project_id": project_id,
            "confirm": confirm,
            "batches": normalized_batches,
        }

    def _render_links_message(self, links: List[str], pending: List[str]) -> str:
        if links:
            body = "\n".join([f"![variant_{idx}]({link})" for idx, link in enumerate(links)])
            content = f"Generated {len(links)}.\\n\\n{body}"
            if pending:
                content += "\\n\\nPending callbacks:\\n" + "\\n".join(pending)
            return content
        if pending:
            return "Generation submitted and waiting for callback.\\n\\n" + "\\n".join(pending)
        return "Generation returned no outputs."

    def _render_plan_message(self, plan: Dict[str, Any]) -> str:
        batches = plan.get("batches") or []
        lines = ["Proposed generation:", "", f"Total: {len(batches)}"]

        for idx, batch in enumerate(batches):
            if idx > 0:
                lines.append("")
                lines.append("---")
                lines.append("")
            lines.append(f"- Model: {batch.get('model')}")
            if plan.get("kind") == "image":
                lines.append(f"- Aspect ratio: {batch.get('ratio')}")
                lines.append(f"- Size: {batch.get('size')}")
            lines.append("- Prompts (verbatim):")
            for prompt in batch.get("prompts") or []:
                lines.append(f"  {prompt}")

        lines.append("")
        lines.append("Reply with any confirmation (e.g. 'looks good', 'send it') to generate, or send edits.")
        plan_blob = json.dumps(plan, ensure_ascii=False)
        lines.append(f"<plan>{plan_blob}</plan>")
        return "\n".join(lines)


    async def _execute_confirmed_plan(self, plan: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        batches = plan.get("batches") or []
        tasks = []
        for batch in batches:
            tool_name = "generate_images" if plan.get("kind") == "image" else "generate_videos"
            args: Dict[str, Any] = {
                "prompts": batch.get("prompts") or [],
                "model": batch.get("model"),
                "project_id": plan.get("project_id") or project_id,
                "confirm_plan": True,
            }
            if plan.get("kind") == "image":
                args["size"] = batch.get("size")
            tool_call = {
                "id": f"confirm_generate_{datetime.now(timezone.utc).timestamp()}_{uuid.uuid4().hex}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(args),
                },
            }
            tasks.append(self.execute_tool(tool_call, project_id))

        results = await asyncio.gather(*tasks)
        download_links: List[str] = []
        pending_tasks: List[str] = []
        failures: List[Dict[str, Any]] = []

        for result in results:
            if result.get("ok"):
                download_links.extend(result.get("download_links", []))
                pending_tasks.extend(result.get("pending_tasks", []))
            else:
                failures.append(result)

        if download_links or pending_tasks:
            content = self._render_links_message(download_links, pending_tasks)
            if failures:
                content += "\n\nSome batches failed. Want me to retry the failed ones?"
            return {
                "content": content,
                "tool_calls_executed": len(results),
                "cost_usd": 0.0,
            }

        if failures:
            content = failures[0].get("public_message") or "Generation failed."
            return {
                "content": content,
                "tool_calls_executed": len(results),
                "cost_usd": 0.0,
            }

        return {
            "content": "Generation returned no outputs.",
            "tool_calls_executed": len(results),
            "cost_usd": 0.0,
        }

    async def process_chat(self, user_message: str, project_id: str, conversation_history: List[Dict[str, str]]):
        await self._broadcast({"type": "progress", "data": {"task": "thinking", "progress": 5}})
        prefs_data = await self.learning.get_preferences(project_id)
        preferences_md = prefs_data.get("preferences_md", "")
        learned_patterns = prefs_data.get("learned_patterns", {})

        pending_plan = False
        for entry in reversed(conversation_history or []):
            if entry.get("role") != "assistant":
                continue
            content = entry.get("content") or ""
            if "<plan>" in content:
                pending_plan = True
            break

        system_prompt = self._planner_system_prompt(project_id, preferences_md, learned_patterns)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for entry in conversation_history or []:
            role = entry.get("role")
            content = entry.get("content")
            if role in {"user", "assistant", "system"} and isinstance(content, str):
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        response = await self.kie_client.chat_completion(messages)
        try:
            credits = response.get("credits_consumed") if isinstance(response, dict) else None
            if isinstance(credits, (int, float)) and credits > 0:
                await self.cost_tracker.log_cost(
                    float(credits),
                    "kie-chat",
                    "gemini-2.5-flash",
                    project_id,
                    "Agent planning completion",
                    session_id=self.session_id,
                )
        except Exception:
            pass

        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        payload = self._parse_llm_payload(content)
        payload = self._validate_llm_payload(payload or {})
        if not payload:
            await self._broadcast({"type": "progress", "data": {"task": "complete", "progress": 100}})
            return {
                "content": "I had trouble understanding that. Please try again.",
                "tool_calls_executed": 0,
                "cost_usd": 0.0,
            }

        action = payload.get("action")
        if action == "question":
            await self._broadcast({"type": "progress", "data": {"task": "complete", "progress": 100}})
            return {
                "content": payload.get("message") or "I need a bit more detail to proceed.",
                "tool_calls_executed": 0,
                "cost_usd": 0.0,
            }

        if action == "chat":
            await self._broadcast({"type": "progress", "data": {"task": "complete", "progress": 100}})
            return {
                "content": payload.get("message") or "",
                "tool_calls_executed": 0,
                "cost_usd": 0.0,
            }

        plan = self._normalize_plan(payload)
        if not plan:
            await self._broadcast({"type": "progress", "data": {"task": "complete", "progress": 100}})
            return {
                "content": "I couldn't build a valid plan. Please try rephrasing.",
                "tool_calls_executed": 0,
                "cost_usd": 0.0,
            }

        if bool(plan.get("confirm")) and pending_plan:
            await self._broadcast({"type": "progress", "data": {"task": "running", "progress": 70}})
            result = await self._execute_confirmed_plan(plan, project_id)
            await self._broadcast({"type": "progress", "data": {"task": "complete", "progress": 100}})
            return result

        plan_message = self._render_plan_message(plan)
        await self._broadcast({"type": "progress", "data": {"task": "complete", "progress": 100}})
        return {
            "content": plan_message,
            "tool_calls_executed": 0,
            "cost_usd": 0.0,
        }

    async def execute_tool(self, tool_call: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        name = tool_call.get("function", {}).get("name")
        raw_args = tool_call.get("function", {}).get("arguments") or "{}"
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
        except Exception:
            args = {}

        print(f"[Project Gepetto] Executing Agent Tool: {name} with args: {args}")
        self._debug_log(f"execute_tool name={name} args={json.dumps(args, default=str)}")

        try:
            from app.config import settings

            callback_url = None

            if name == "search_available_models":
                query = args.get("query")
                kind = args.get("kind") or "any"
                result = await self.kie_client.list_models(query=query, kind=kind)
                return {"ok": True, "llm_payload": result}

            if name == "generate_images":
                confirm_plan = bool(args.get("confirm_plan"))
                if not confirm_plan:
                    return {
                        "ok": False,
                        "public_message": "Please confirm the plan before I generate.",
                        "llm_payload": {"status": "error", "message": "Missing confirmation"},
                    }

                prompts = args.get("prompts")
                model = args.get("model")
                size = args.get("size")
                tool_project = args.get("project_id") or project_id

                if not tool_project:
                    return {
                        "ok": False,
                        "public_message": "Missing project scope.",
                        "llm_payload": {"status": "error", "message": "Missing project_id"},
                    }
                if not isinstance(prompts, list) or not prompts:
                    return {
                        "ok": False,
                        "public_message": "Missing prompts for generation.",
                        "llm_payload": {"status": "error", "message": "Missing prompts"},
                    }
                if not isinstance(model, str) or not model.strip():
                    return {
                        "ok": False,
                        "public_message": "Missing model name.",
                        "llm_payload": {"status": "error", "message": "Missing model"},
                    }
                if not isinstance(size, str) or not size.strip():
                    return {
                        "ok": False,
                        "public_message": "Missing size for image generation.",
                        "llm_payload": {"status": "error", "message": "Missing size"},
                    }

                if settings.environment != "development":
                    callback_url = self._build_callback_url(settings.backend_url, tool_project)

                generation = await self.kie_client.generate_images(
                    prompts=prompts,
                    model=model,
                    size=size,
                    callback_url=callback_url,
                    project_id=tool_project,
                    allow_fallbacks=False,
                )

                if not generation.get("ok"):
                    self._debug_log(
                        "generate_images failed "
                        + json.dumps({"model": model, "result": generation}, default=str)
                    )
                    return {
                        "ok": False,
                        "public_message": generation.get("message") or "I couldn't reach that model. Want me to try another?",
                        "llm_payload": {
                            "status": "error",
                            "message": generation.get("message"),
                            "errors": generation.get("errors"),
                        },
                    }

                pending_tasks: List[str] = []
                download_links: List[str] = []
                drive_links: List[str] = []
                download_errors: List[str] = []
                urls = generation.get("urls", [])
                task_ids = generation.get("task_ids") or []
                if isinstance(task_ids, str):
                    task_ids = [task_ids]
                if generation.get("pending_callback") and task_ids:
                    for task_id in task_ids:
                        pending_tasks.append(f"Webhook job pending (Task ID: {task_id})")
                else:
                    if not urls:
                        return {
                            "ok": False,
                            "public_message": "Generation returned no assets. Want me to retry?",
                            "llm_payload": {"status": "error", "message": "No asset URLs returned"},
                        }
                    batch_id = uuid.uuid4().hex
                    for idx, url in enumerate(urls):
                        if not isinstance(url, str):
                            continue
                        filename = f"gen_{batch_id}_{idx}.jpg"
                        try:
                            if url.startswith("mock_image_"):
                                car_path = Path("/storage/car.png")
                                if not car_path.exists():
                                    raise FileNotFoundError("Mock placeholder missing")
                                img_bytes = car_path.read_bytes()
                            else:
                                img_bytes = await self._download_asset(url)
                            saved_path = await self.storage.save_file(img_bytes, tool_project, "generated", filename)
                            drive_info = await self._upload_to_drive(filename, img_bytes)
                            if drive_info:
                                self._remove_local_file(saved_path)
                            relative_name = Path(saved_path).name
                            local_link = f"/api/storage/download/{tool_project}/generated/{relative_name}"
                            drive_link = drive_info.get("directUrl") if drive_info else None
                            download_links.append(drive_link or local_link)
                            if drive_info and drive_info.get("webViewLink"):
                                drive_links.append(drive_info["webViewLink"])
                        except Exception as exc:
                            download_errors.append(f"{idx}:{exc}")
                            continue
                        slot_id = f"{batch_id}:{idx}"
                        await self.learning.log_generation(
                            tool_project,
                            download_links[-1],
                            prompts[min(idx, len(prompts) - 1)] if prompts else "",
                            generation.get("model_used", model),
                            size,
                            batch_id,
                            idx,
                            slot_id,
                        )
                        await self._record_asset(
                            asset_type="image",
                            file_path=saved_path,
                            drive_info=drive_info,
                            prompt=prompts[min(idx, len(prompts) - 1)] if prompts else "",
                        )

                    if not download_links:
                        return {
                            "ok": False,
                            "public_message": "Generated assets could not be downloaded. Want me to retry?",
                            "llm_payload": {"status": "error", "message": "Download failed", "errors": download_errors},
                        }

                    await self._notify_completion(len(download_links), drive_links[0] if drive_links else download_links[0])

                await self.cost_tracker.log_cost(
                    0.0,
                    "kie-image",
                    generation.get("model_used", model),
                    tool_project,
                    f"Image generation ({len(prompts)} assets)",
                    session_id=self.session_id,
                )

                return {
                    "ok": True,
                    "download_links": download_links,
                    "pending_tasks": pending_tasks,
                    "llm_payload": {
                        "status": "ok",
                        "download_links": download_links,
                        "pending_tasks": pending_tasks,
                        "model_used": generation.get("model_used", model),
                    },
                }

            if name == "generate_videos":
                confirm_plan = bool(args.get("confirm_plan"))
                if not confirm_plan:
                    return {
                        "ok": False,
                        "public_message": "Please confirm the plan before I generate.",
                        "llm_payload": {"status": "error", "message": "Missing confirmation"},
                    }

                prompts = args.get("prompts")
                model = args.get("model")
                tool_project = args.get("project_id") or project_id

                if not tool_project:
                    return {
                        "ok": False,
                        "public_message": "Missing project scope.",
                        "llm_payload": {"status": "error", "message": "Missing project_id"},
                    }
                if not isinstance(prompts, list) or not prompts:
                    return {
                        "ok": False,
                        "public_message": "Missing prompts for generation.",
                        "llm_payload": {"status": "error", "message": "Missing prompts"},
                    }
                if not isinstance(model, str) or not model.strip():
                    return {
                        "ok": False,
                        "public_message": "Missing model name.",
                        "llm_payload": {"status": "error", "message": "Missing model"},
                    }

                if settings.environment != "development":
                    callback_url = self._build_callback_url(settings.backend_url, tool_project)

                all_urls: List[str] = []
                drive_links: List[str] = []
                pending_tasks: List[str] = []
                model_used = model
                batch_id = uuid.uuid4().hex
                for prompt in prompts:
                    generation = await self.kie_client.generate_video(
                        prompt=prompt,
                        model=model,
                        callback_url=callback_url,
                        project_id=tool_project,
                        allow_fallbacks=False,
                    )
                    if not generation.get("ok"):
                        return {
                            "ok": False,
                            "public_message": generation.get("message") or "I couldn't reach that model. Want me to try another?",
                            "llm_payload": {"status": "error", "message": generation.get("message")},
                        }

                    urls = generation.get("urls", [])
                    if generation.get("pending_callback") and generation.get("task_id"):
                        pending_tasks.append(f"Webhook job pending (Task ID: {generation['task_id']})")
                    else:
                        for idx, url in enumerate(urls):
                            if not isinstance(url, str):
                                continue
                            filename = f"video_{batch_id}_{idx}.mp4"
                            if url.startswith("mock_video_"):
                                video_bytes = b""
                            else:
                                video_bytes = await self._download_asset(url)
                            saved_path = await self.storage.save_file(video_bytes, tool_project, "generated", filename)
                            drive_info = await self._upload_to_drive(filename, video_bytes)
                            if drive_info:
                                self._remove_local_file(saved_path)
                            relative_name = Path(saved_path).name
                            local_link = f"/api/storage/download/{tool_project}/generated/{relative_name}"
                            drive_link = drive_info.get("webViewLink") if drive_info else None
                            all_urls.append(drive_link or local_link)
                            if drive_info and drive_info.get("webViewLink"):
                                drive_links.append(drive_info["webViewLink"])
                            await self._record_asset(
                                asset_type="video",
                                file_path=saved_path,
                                drive_info=drive_info,
                                prompt=prompt,
                            )
                    model_used = generation.get("model_used", model_used)

                await self.cost_tracker.log_cost(
                    0.0,
                    "kie-video",
                    model_used,
                    tool_project,
                    f"Video generation ({len(prompts)} assets)",
                    session_id=self.session_id,
                )

                if all_urls:
                    await self._notify_completion(len(all_urls), drive_links[0] if drive_links else all_urls[0])

                return {
                    "ok": True,
                    "download_links": all_urls,
                    "pending_tasks": pending_tasks,
                    "llm_payload": {
                        "status": "ok",
                        "download_links": all_urls,
                        "pending_tasks": pending_tasks,
                        "model_used": model_used,
                    },
                }

            if name == "save_to_storage":
                paths: List[str] = []
                files = args.get("files") or []
                subfolder = args.get("subfolder") or "generated"
                target_project = args.get("project_id") or project_id
                for idx, item in enumerate(files):
                    content = f"placeholder_{idx}".encode("utf-8")
                    filename = f"file_{idx}.jpg"
                    if isinstance(item, str):
                        clean = item.replace("\\", "/").split("/")[-1]
                        if clean:
                            filename = clean
                    path = await self.storage.save_file(content, target_project, subfolder, filename)
                    paths.append(path)
                return {"ok": True, "llm_payload": {"status": "ok", "saved_paths": paths}}

            if name == "trigger_n8n_workflow":
                workflow = str(args.get("workflow_name") or "ugc-batch")
                payload = args.get("payload", {})
                result = await self.n8n.trigger_workflow(workflow, payload)
                return {"ok": True, "llm_payload": result}

            if name == "read_project_preferences":
                pid = args.get("project_id") or project_id
                prefs = await self.learning.get_preferences(pid)
                return {"ok": True, "llm_payload": prefs}

            if name == "update_project_preferences":
                pid = args.get("project_id") or project_id
                updates = args.get("updates") or {}
                result = await self.learning.update_preferences(pid, updates)
                return {"ok": True, "llm_payload": result}

            if name == "log_cost":
                amount = float(args.get("amount_usd") or 0.0)
                service = args.get("service") or "kie-chat"
                model = args.get("model") or "unknown"
                pid = args.get("project_id") or project_id
                description = args.get("description") or "manual log"
                logged = await self.cost_tracker.log_cost(amount, service, model, pid, description, session_id=self.session_id)
                return {"ok": True, "llm_payload": {"status": "ok", "logged_amount": logged}}

            return {
                "ok": False,
                "public_message": "I couldn't run one of the requested operations.",
                "llm_payload": {"status": "error", "message": "Unknown tool"},
            }

        except Exception as e:
            print(f"[Project Gepetto] Tool execution failed: {name}: {e}")
            return {
                "ok": False,
                "public_message": "I hit a temporary generation issue. Want me to try again?",
                "llm_payload": {"status": "error", "message": "Tool execution failed"},
            }

    async def regenerate_rejected_asset(self, project_id: str, asset_url: str) -> Dict[str, Any]:
        record = await self.learning.find_generation_by_asset(project_id, asset_url)
        if not record:
            return {"ok": False, "message": "No generation record found"}

        prompt = record.get("prompt") or ""
        model = record.get("model") or ""
        size = record.get("size") or ""
        slot_id = record.get("slot_id")

        if slot_id:
            attempts = await self.learning.count_slot_attempts(project_id, slot_id)
            if attempts >= 3:
                return {"ok": False, "message": "Max regeneration attempts reached"}

        if not prompt or not model or not size:
            return {"ok": False, "message": "Missing regeneration data"}

        from app.config import settings
        callback_url = None
        if settings.environment != "development":
            callback_url = f"{settings.backend_url}/api/kie/callback"

        generation = await self.kie_client.generate_images(
            prompts=[prompt],
            model=model,
            size=size,
            callback_url=callback_url,
            project_id=project_id,
            allow_fallbacks=False,
        )

        if not generation.get("ok"):
            return {
                "ok": False,
                "message": generation.get("message") or "Regeneration failed",
                "errors": generation.get("errors"),
            }

        download_links: List[str] = []
        pending_tasks: List[str] = []
        urls = generation.get("urls", [])
        task_ids = generation.get("task_ids") or []
        if isinstance(task_ids, str):
            task_ids = [task_ids]
        if generation.get("pending_callback") and task_ids:
            for task_id in task_ids:
                pending_tasks.append(f"Webhook job pending (Task ID: {task_id})")
        else:
            batch_id = uuid.uuid4().hex
            for idx, url in enumerate(urls):
                if not isinstance(url, str):
                    continue
                filename = f"regen_{batch_id}_{idx}.jpg"
                if url.startswith("mock_image_"):
                    car_path = Path("/storage/car.png")
                    if not car_path.exists():
                        continue
                    img_bytes = car_path.read_bytes()
                else:
                    img_bytes = await self._download_asset(url)
                saved_path = await self.storage.save_file(img_bytes, project_id, "generated", filename)
                relative_name = Path(saved_path).name
                download_links.append(f"/api/storage/download/{project_id}/generated/{relative_name}")
                await self.learning.log_generation(
                    project_id,
                    download_links[-1],
                    prompt,
                    generation.get("model_used", model),
                    size,
                    batch_id,
                    idx,
                    slot_id,
                    asset_url,
                )

        await self.cost_tracker.log_cost(
            0.0,
            "kie-image",
            generation.get("model_used", model),
            project_id,
            "Image regeneration (1 asset)",
        )

        return {
            "ok": True,
            "download_links": download_links,
            "pending_tasks": pending_tasks,
            "message": self._render_links_message(download_links, pending_tasks),
        }
