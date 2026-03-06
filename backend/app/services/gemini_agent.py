import json
import uuid
import re
from pathlib import Path
from typing import Any, Dict, List

import httpx

from app.services.cost_tracker import CostTracker
from app.services.kie_client import KieClient
from app.services.learning_engine import LearningEngine
from app.services.n8n_client import N8nClient
from app.services.storage_service import StorageService


class GeminiAgentService:
    MAX_TOOL_CALLS = 20
    MAX_LOOP_STEPS = 12

    def __init__(self, db_session):
        self.kie_client = KieClient()
        self.storage = StorageService()
        self.learning = LearningEngine()
        self.n8n = N8nClient("https://dummy_webhook")
        self.cost_tracker = CostTracker(db_session)

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
                            "prompts": {"type": "array", "items": {"type": "string"}, "description": "Array of detailed prompts. Each prompt generates one distinct image."},
                            "model": {"type": "string", "description": "The exact API name of the image model to use."},
                            "size": {"type": "string", "description": "Aspect ratio/resolution (e.g. 1024x1024, 1024x1792)"},
                            "project_id": {"type": "string"},
                            "style_overrides": {"type": "object"},
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

    def _extract_explicit_model(self, message: str) -> str | None:
        text = message.strip()
        if not text:
            return None
        lowered = text.lower()
        patterns = [r"\busing\s+([^\n\r\.,;]+)", r"\buse\s+([^\n\r\.,;]+)", r"\bwith\s+([^\n\r\.,;]+)"]
        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if not match:
                continue
            candidate = match.group(1).strip()
            candidate = re.split(r"[,.;]", candidate, maxsplit=1)[0].strip()
            candidate = re.split(r"\b(just|only|please|do|and|for|to|that|like)\b", candidate, maxsplit=1)[0].strip()
            candidate = re.sub(r"\bmodel\b", "", candidate, flags=re.IGNORECASE).strip()
            candidate = candidate.strip("\"'()[]{} ")
            if candidate:
                return candidate
        return None

    def _coerce_model_name(self, name: str) -> str:
        cleaned = name.strip().strip("\"'()[]{} ")
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"-+", "-", cleaned)
        return cleaned

    def _extract_rules(self, preferences_md: str) -> Dict[str, str]:
        rules: Dict[str, str] = {}
        for line in preferences_md.splitlines():
            line = line.strip()
            if not line.startswith("-"):
                continue
            payload = line.lstrip("- ").strip()
            if ":" not in payload:
                continue
            key, value = payload.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key:
                rules[key] = value
        return rules

    def _ratio_to_size(self, ratio: str) -> str:
        normalized = ratio.strip()
        if normalized in ("9:16", "9x16"):
            return "1024x1792"
        if normalized in ("16:9", "16x9"):
            return "1792x1024"
        if normalized in ("1:1", "1x1"):
            return "1024x1024"
        if normalized in ("4:3", "4x3"):
            return "1024x768"
        if normalized in ("3:4", "3x4"):
            return "768x1024"
        return "1024x1024"

    def _apply_preference_rules(self, prompts: List[str], size: str, rules: Dict[str, str]) -> tuple[List[str], str]:
        updated_size = size
        style_hints: List[str] = []

        base_aspect = rules.get("aspect_ratio") or rules.get("aspect ratio")
        if base_aspect:
            updated_size = self._ratio_to_size(base_aspect)

        selfie_aspect = rules.get("selfie.aspect_ratio") or rules.get("selfies.aspect_ratio")
        if selfie_aspect:
            if any("selfie" in p.lower() for p in prompts):
                updated_size = self._ratio_to_size(selfie_aspect)

        style_value = rules.get("style")
        if style_value:
            style_hints.append(style_value)
        for key, value in rules.items():
            if key.startswith("style."):
                style_hints.append(value or key.replace("style.", ""))

        if style_hints:
            hint = ", ".join([h for h in style_hints if h])
            if hint:
                prompts = [f"{p.rstrip()} {hint}" for p in prompts]

        return prompts, updated_size

    def _detect_scope(self, message: str, active_project: str) -> tuple[str, str | None]:
        lowered = message.lower()
        project_map = {
            "drew": "drew-5trips",
            "5trips": "drew-5trips",
            "drew-5trips": "drew-5trips",
            "betway": "betway-f1",
            "betway-f1": "betway-f1",
        }
        for key, pid in project_map.items():
            if key in lowered:
                return "project", pid
        if "this project" in lowered or "this campaign" in lowered or "this client" in lowered or "here" in lowered:
            return "project", active_project
        global_markers = ["always", "never", "globally", "in general", "for all projects", "standard", "default"]
        if any(marker in lowered for marker in global_markers):
            return "global", None
        return "session", None

    def _extract_preference_updates(self, message: str, active_project: str) -> tuple[str | None, Dict[str, str]]:
        lowered = message.lower()
        intent_markers = ["should", "must", "only", "never", "always", "avoid", "prefer", "more", "less"]
        if not any(marker in lowered for marker in intent_markers):
            return None, {}

        scope, scope_project = self._detect_scope(message, active_project)
        updates: Dict[str, str] = {}

        ratio_match = re.search(r"\b(\d{1,2}:\d{1,2})\b", lowered)
        if ratio_match:
            ratio = ratio_match.group(1)
            if "selfie" in lowered or "selfies" in lowered:
                updates["selfie.aspect_ratio"] = ratio
            else:
                updates["aspect_ratio"] = ratio

        if "lofi" in lowered or "lo-fi" in lowered:
            updates["style"] = "lofi"
        if "too polished" in lowered:
            updates["style"] = "lofi"
        if "grain" in lowered or "grainy" in lowered:
            updates["style.grain"] = "true"

        if not updates:
            return None, {}

        if scope == "global":
            return "global", updates
        if scope == "project":
            return scope_project or active_project, updates
        return None, {}

    def _is_image_request(self, message: str) -> bool:
        lowered = message.lower()
        if "video" in lowered or "clip" in lowered:
            return False
        keywords = ["image", "photo", "pic", "ugc", "render", "shot", "frame", "generate", "create", "make", "selfie", "portrait"]
        return any(word in lowered for word in keywords)

    def _infer_count(self, message: str) -> int:
        digit_match = re.search(r"\b(\d+)\b", message)
        if digit_match:
            try:
                return max(1, int(digit_match.group(1)))
            except Exception:
                return 1
        return 1

    def _infer_size(self, message: str) -> str:
        lowered = message.lower()
        if "ugc" in lowered:
            return "1024x1792"
        if "cinematic" in lowered:
            return "1792x1024"
        if "product" in lowered:
            return "1024x1024"
        return "1024x1024"

    def _normalize_model_name(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def _render_links_message(self, links: List[str], pending: List[str]) -> str:
        if links:
            body = "\n".join([f"![variant_{idx}]({link})" for idx, link in enumerate(links)])
            content = f"Generated {len(links)}.\n\n{body}"
            if pending:
                content += "\n\nPending callbacks:\n" + "\n".join(pending)
            return content
        if pending:
            return "Generation submitted and waiting for callback.\n\n" + "\n".join(pending)
        return "Generation returned no outputs."

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
            if settings.environment != "development":
                callback_url = f"{settings.backend_url}/api/kie/callback"

            if name == "search_available_models":
                query = args.get("query")
                kind = args.get("kind") or "any"
                result = await self.kie_client.list_models(query=query, kind=kind)
                return {"ok": True, "llm_payload": result}

            if name == "generate_images":
                prompts = args.get("prompts") or []
                model = args.get("model")
                if isinstance(model, str) and " " in model:
                    model = self._coerce_model_name(model)
                size = args.get("size") or "1024x1024"
                if isinstance(size, str) and ":" in size:
                    ratio = size.strip()
                    if ratio == "9:16":
                        size = "1024x1792"
                    elif ratio == "16:9":
                        size = "1792x1024"
                    elif ratio == "1:1":
                        size = "1024x1024"
                tool_project = args.get("project_id") or project_id or "default"
                if not prompts:
                    prompts = [""]

                if not model:
                    return {
                        "ok": False,
                        "public_message": "I need a model name before I can generate images. Which model should I use?",
                        "llm_payload": {"status": "error", "message": "Missing model"},
                    }

                prefs_data = await self.learning.get_preferences(tool_project)
                rules = self._extract_rules(prefs_data.get("preferences_md", ""))
                prompts, size = self._apply_preference_rules(prompts, size, rules)

                generation = await self.kie_client.generate_images(
                    prompts=prompts,
                    model=model,
                    size=size,
                    callback_url=callback_url,
                    project_id=tool_project,
                )

                if not generation.get("ok"):
                    self._debug_log(
                        "generate_images failed "
                        + json.dumps({"model": model, "result": generation}, default=str)
                    )
                    return {
                        "ok": False,
                        "public_message": generation.get("message") or "I couldn't reach that model. Want me to try another?",
                        "llm_payload": {"status": "error", "message": generation.get("message"), "errors": generation.get("errors")},
                    }

                pending_tasks: List[str] = []
                download_links: List[str] = []
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
                        filename = f"gen_{batch_id}_{idx}.jpg"
                        if url.startswith("mock_image_"):
                            car_path = Path("/storage/car.png")
                            if not car_path.exists():
                                continue
                            img_bytes = car_path.read_bytes()
                        else:
                            img_bytes = await self._download_asset(url)
                        saved_path = await self.storage.save_file(img_bytes, tool_project, "generated", filename)
                        relative_name = Path(saved_path).name
                        download_links.append(f"/api/storage/download/{tool_project}/generated/{relative_name}")

                await self.cost_tracker.log_cost(
                    0.0,
                    "kie-image",
                    generation.get("model_used", model),
                    tool_project,
                    f"Image generation ({len(prompts)} assets)",
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
                prompts = args.get("prompts") or []
                model = args.get("model")
                tool_project = args.get("project_id") or project_id or "default"
                if not prompts:
                    prompts = [""]

                if not model:
                    return {
                        "ok": False,
                        "public_message": "I need a model name before I can generate videos. Which model should I use?",
                        "llm_payload": {"status": "error", "message": "Missing model"},
                    }

                all_urls: List[str] = []
                pending_tasks: List[str] = []
                model_used = model
                for prompt in prompts:
                    generation = await self.kie_client.generate_video(
                        prompt=prompt,
                        model=model,
                        callback_url=callback_url,
                        project_id=tool_project,
                    )
                    if not generation.get("ok"):
                        return {
                            "ok": False,
                            "public_message": generation.get("message") or "I couldn't reach that model. Want me to try another?",
                            "llm_payload": {"status": "error", "message": generation.get("message")},
                        }

                    all_urls.extend(generation.get("urls", []))
                    if generation.get("pending_callback") and generation.get("task_id"):
                        pending_tasks.append(f"Webhook job pending (Task ID: {generation['task_id']})")
                    model_used = generation.get("model_used", model_used)

                await self.cost_tracker.log_cost(
                    0.0,
                    "kie-video",
                    model_used,
                    tool_project,
                    f"Video generation ({len(prompts)} assets)",
                )

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
                logged = await self.cost_tracker.log_cost(amount, service, model, pid, description)
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

    async def process_chat(self, user_message: str, project_id: str, conversation_history: List[Dict[str, str]]):
        await self._broadcast({"type": "progress", "data": {"task": "thinking", "progress": 5}})

        prefs_data = await self.learning.get_preferences(project_id)
        prefs_md = prefs_data.get("preferences_md", "")

        pref_scope, pref_updates = self._extract_preference_updates(user_message, project_id)
        if pref_scope and pref_updates:
            try:
                tool_call = {
                    "id": f"pref_update_{uuid.uuid4().hex}",
                    "type": "function",
                    "function": {
                        "name": "update_project_preferences",
                        "arguments": json.dumps({
                            "project_id": pref_scope,
                            "updates": pref_updates,
                        }),
                    },
                }
                await self.execute_tool(tool_call, pref_scope)
            except Exception:
                pass

        explicit_model = self._extract_explicit_model(user_message)
        if explicit_model and self._is_image_request(user_message):
            model_name: str | None = None
            try:
                coerced = self._coerce_model_name(explicit_model)
                resolved = await self.kie_client.list_models(query=coerced, kind="image")
                models = resolved.get("models") or []
                explicit_norm = self._normalize_model_name(coerced)
                matches: List[str] = []
                for item in models:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("id") or item.get("name") or "").strip()
                    if not name:
                        continue
                    if self._normalize_model_name(name) == explicit_norm:
                        matches.append(name)

                if len(matches) == 1:
                    model_name = matches[0]
                elif len(models) == 1 and isinstance(models[0], dict):
                    model_name = str(models[0].get("id") or models[0].get("name") or "").strip() or None
            except Exception:
                model_name = None

            if not model_name:
                model_name = self._coerce_model_name(explicit_model)

            size = self._infer_size(user_message)
            count = self._infer_count(user_message)
            prompt = re.sub(r"\b(using|use|with)\s+[^\n\r\.,;]+", "", user_message, flags=re.IGNORECASE).strip()
            if model_name:
                prompt = re.sub(re.escape(model_name), "", prompt, flags=re.IGNORECASE).strip()
            prompt = prompt or user_message
            prompts = [prompt for _ in range(count)]
            tool_call = {
                "id": f"direct_generate_{uuid.uuid4().hex}",
                "type": "function",
                "function": {
                    "name": "generate_images",
                    "arguments": json.dumps({
                        "prompts": prompts,
                        "model": model_name,
                        "size": size,
                        "project_id": project_id,
                    }),
                },
            }

            result = await self.execute_tool(tool_call, project_id)
            if result.get("ok"):
                rendered_links = result.get("download_links", [])
                pending_tasks = result.get("pending_tasks", [])
                content = self._render_links_message(rendered_links, pending_tasks)
                await self._broadcast({"type": "progress", "data": {"task": "complete", "progress": 100}})
                return {
                    "content": content,
                    "tool_calls_executed": 1,
                    "cost_usd": 0.01,
                }
            return {
                "content": result.get("public_message") or "I couldn't generate that image just now. Want me to try again?",
                "tool_calls_executed": 1,
                "cost_usd": 0.0,
            }

        system_content = (
            f"You are Agent Gepetto. Active project: {project_id}.\n"
            "You are the agent. Decide what to do next.\n"
            "When the user requests generation, you MUST either call a tool or ask a clarification question.\n"
            "If the user already specified a model earlier in the conversation, use that exact model without asking again.\n"
            "If the user states a lasting preference or rule (e.g. 'for this project', 'always', 'only', 'never'), you MUST call update_project_preferences to save it and then confirm it was saved.\n"
            "\n"
            "**Generating Images / Videos**\n"
            "Do NOT assume or hardcode what models exist or what models are best. The available models are dynamic.\n"
            "If a specific model is not explicitly requested by the user or defined in the preferences, you MUST use the `search_available_models` tool to query Kie.ai for the currently available options.\n"
            "If the choice is ambiguous, ask the user. Pass the exact model name string to the `model` parameter.\n"
            "If the tool returns an error, gracefully inform the user, log the failure, and attempt a retry using a different model from the available list or a modified prompt.\n"
            "Never expose raw API errors.\n"
            f"Learned/project preferences:\n{prefs_md}"
        )

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_content}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        tool_calls_executed = 0
        completed_steps: List[str] = []
        rendered_links: List[str] = []
        pending_tasks: List[str] = []
        empty_responses = 0

        def _extract_text(content: Any) -> str:
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: List[str] = []
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                    elif isinstance(item, str):
                        parts.append(item)
                return "".join(parts)
            return ""

        for loop_step in range(self.MAX_LOOP_STEPS):
            await self._broadcast({"type": "progress", "data": {"task": "thinking", "progress": min(90, 10 + loop_step * 6)}})
            response = await self.kie_client.chat_completion(messages, tools=self.tools)
            try:
                self._debug_log(
                    f"chat_response loop={loop_step} "
                    + json.dumps(response, default=str)[:4000]
                )
            except Exception:
                self._debug_log(f"chat_response loop={loop_step} <unserializable>")
            if loop_step == 0:
                try:
                    print("[Project Gepetto] Raw chat response:", json.dumps(response, indent=2))
                except Exception:
                    print("[Project Gepetto] Raw chat response (unserializable)")
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {}) if isinstance(choice, dict) else {}

            tool_calls = message.get("tool_calls") or choice.get("tool_calls") or []
            function_call = message.get("function_call") or choice.get("function_call")
            if not tool_calls and function_call:
                tool_calls = [
                    {
                        "id": f"function_call_{uuid.uuid4().hex}",
                        "type": "function",
                        "function": {
                            "name": function_call.get("name"),
                            "arguments": function_call.get("arguments", "{}"),
                        },
                    }
                ]
            content = message.get("content")
            assistant_text = _extract_text(content).strip()
            if isinstance(assistant_text, str) and "data:image" in assistant_text:
                self._debug_log("blocked_inline_image_response")
                messages.append(
                    {
                        "role": "system",
                        "content": "Do not return inline images or base64. Use tool calls only for generation.",
                    }
                )
                continue

            if not tool_calls and isinstance(content, list):
                for item in content:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") not in ("tool_use", "tool"):
                        continue
                    name = item.get("name") or item.get("tool")
                    tool_input = item.get("input") or item.get("arguments") or {}
                    tool_id = item.get("id")
                    if not name:
                        continue
                    tool_calls.append(
                        {
                            "id": tool_id or f"tool_use_{uuid.uuid4().hex}",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(tool_input),
                            },
                        }
                    )

            print(
                "[Project Gepetto] Parsed chat response: "
                f"tool_calls={len(tool_calls)} function_call={bool(function_call)} text_len={len(assistant_text)}"
            )
            self._debug_log(
                "parsed_chat_response "
                + json.dumps(
                    {
                        "tool_calls": len(tool_calls),
                        "function_call": bool(function_call),
                        "text_len": len(assistant_text),
                    }
                )
            )

            if tool_calls:
                safe_content = message.get("content") or ""
                if isinstance(safe_content, str) and ("data:image" in safe_content or len(safe_content) > 20000):
                    safe_content = ""
                messages.append({"role": "assistant", "content": safe_content, "tool_calls": tool_calls})

                for call in tool_calls:
                    if tool_calls_executed >= self.MAX_TOOL_CALLS:
                        summary = "\n".join([f"- {step}" for step in completed_steps[-8:]]) or "- No completed actions yet"
                        return {
                            "content": "I stopped to prevent a runaway loop (20 tool calls). Here's what I completed so far:\n" + summary,
                            "tool_calls_executed": tool_calls_executed,
                            "cost_usd": 0.0,
                        }

                    if explicit_model and call.get("function", {}).get("name") == "generate_images":
                        try:
                            call_args_raw = call.get("function", {}).get("arguments") or "{}"
                            call_args = json.loads(call_args_raw) if isinstance(call_args_raw, str) else dict(call_args_raw)
                            call_args["model"] = self._coerce_model_name(explicit_model)
                            call["function"]["arguments"] = json.dumps(call_args)
                        except Exception:
                            pass

                    result = await self.execute_tool(call, project_id)
                    tool_calls_executed += 1

                    if not result.get("ok"):
                        # Feed the error back to the LLM instead of returning
                        tool_message = {
                            "role": "tool",
                            "tool_call_id": call.get("id", f"tool_{tool_calls_executed}"),
                            "name": call.get("function", {}).get("name", "tool"),
                            "content": json.dumps(result.get("llm_payload", {"status": "error", "message": result.get("public_message", "Unknown error")})),
                        }
                        messages.append(tool_message)
                        continue

                    rendered_links.extend(result.get("download_links", []))
                    pending_tasks.extend(result.get("pending_tasks", []))
                    completed_steps.append(call.get("function", {}).get("name", "tool"))

                    tool_message = {
                        "role": "tool",
                        "tool_call_id": call.get("id", f"tool_{tool_calls_executed}"),
                        "name": call.get("function", {}).get("name", "tool"),
                        "content": json.dumps(result.get("llm_payload", {"status": "ok"})),
                    }
                    messages.append(tool_message)
                continue

            if assistant_text:
                if (
                    self._is_image_request(user_message)
                    and not tool_calls
                    and not rendered_links
                    and not pending_tasks
                ):
                    messages.append(
                        {
                            "role": "system",
                            "content": "You must respond with a tool call when the user requests image generation. Do not describe or claim images were generated unless a tool call was executed.",
                        }
                    )
                    continue
                if rendered_links or pending_tasks:
                    assistant_text += "\n\n" + self._render_links_message(rendered_links, pending_tasks)
                await self._broadcast({"type": "progress", "data": {"task": "complete", "progress": 100}})
                return {
                    "content": assistant_text,
                    "tool_calls_executed": tool_calls_executed,
                    "cost_usd": 0.0 if tool_calls_executed == 0 else 0.01,
                }

            # Guard against empty responses from the model
            empty_responses += 1
            if empty_responses >= 3:
                return {
                    "content": "I ran into a problem: the model is repeatedly returning empty outputs. Please try rewording your prompt.",
                    "tool_calls_executed": tool_calls_executed,
                    "cost_usd": 0.0,
                }
            
            print(f"[Project Gepetto] Empty model response: {message}")
            messages.append(
                {
                    "role": "system",
                    "content": "You must respond with a tool call or a clarification question. Do not return empty output.",
                }
            )
            continue

        summary = "\n".join([f"- {step}" for step in completed_steps[-8:]]) or "- No completed actions yet"
        return {
            "content": "I stopped after several reasoning steps to avoid a runaway loop. Here's what I completed so far:\n" + summary,
            "tool_calls_executed": tool_calls_executed,
            "cost_usd": 0.0,
        }
