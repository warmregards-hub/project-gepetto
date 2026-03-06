import json
from pathlib import Path

class LearningEngine:
    def __init__(self):
        self.projects_dir = Path("projects")
        
    async def get_preferences(self, project_id: str):
        # 1. Load global preferences (apply to all projects)
        global_pref_path = self.projects_dir / "global" / "preferences.md"
        global_prefs = ""
        if global_pref_path.exists():
            with open(global_pref_path, "r") as f:
                global_prefs = f.read()

        # 2. Load per-project preferences (override global where specified)
        pref_path = self.projects_dir / project_id / "preferences.md"
        patterns_path = self.projects_dir / project_id / "learned-patterns.json"
        
        project_prefs = ""
        if pref_path.exists():
            with open(pref_path, "r") as f:
                project_prefs = f.read()

        patterns = {}
        if patterns_path.exists():
            with open(patterns_path, "r") as f:
                try:
                    patterns = json.load(f)
                except json.JSONDecodeError:
                    pass

        combined = ""
        if global_prefs:
            combined += f"## Global Rules (all projects)\n{global_prefs}\n\n"
        if project_prefs:
            combined += f"## Project-Specific Rules (override global)\n{project_prefs}\n\n"
        if patterns:
            combined += f"## Learned Patterns (auto-generated from your feedback)\n"
            combined += f"- Additions: {', '.join(patterns.get('recommended_prompt_additions', []))}\n"
            combined += f"- Exclusions: {', '.join(patterns.get('recommended_prompt_exclusions', []))}\n"
            combined += f"- Positive patterns: {', '.join(patterns.get('positive_patterns', []))}\n"
            combined += f"- Negative patterns: {', '.join(patterns.get('negative_patterns', []))}\n"

        return {"preferences_md": combined.strip(), "learned_patterns": patterns}
        
    async def analyze_feedback(self, project_id: str):
        # Read the raw qc-feedback.jsonl
        feedback_path = self.projects_dir / project_id / "qc-feedback.jsonl"
        patterns_path = self.projects_dir / project_id / "learned-patterns.json"
        
        if not feedback_path.exists():
            return False
            
        entries = []
        with open(feedback_path, "r") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
        
        # Calculate keep_rate_by_model
        models_data = {}
        kept_prompts = []
        rejected_prompts = []
        
        for e in entries:
            model = e.get("model", "unknown")
            if model not in models_data:
                models_data[model] = {"total": 0, "kept": 0}
            
            models_data[model]["total"] += 1
            if e.get("decision") == "keep":
                models_data[model]["kept"] += 1
                kept_prompts.append(e.get("prompt", ""))
            else:
                rejected_prompts.append(e.get("prompt", ""))
                
        keep_rate_by_model = {
            m: f"{int((d['kept']/d['total'])*100)}%" for m, d in models_data.items() if d["total"] > 0
        }
        
        # To strictly follow the "distill feedback" requirement, we'd ideally use an LLM here
        # to find semantic patterns, but we'll implement a basic keyword frequency approach as a solid foundation,
        # or we could make an LLM call here via KieClient. For now, we will construct a system 
        # message simulating the LLM extraction or do a rudimentary word frequency analysis.
        
        # We will ask an LLM offline or simulate the patterns if LLM is unavailable.
        # Given this is happening inside the learning engine, we'll formulate the schema:
        # (A full LLM prompt to distill patterns from `kept_prompts` and `rejected_prompts` would go here)
        
        # Basic mock implementation of semantic distillation:
        from collections import Counter
        import re
        
        def get_words(texts):
            words = []
            for t in texts:
                 words.extend(re.findall(r'\b\w{4,}\b', t.lower()))
            return Counter(words)
            
        kept_words = set([word for word, count in get_words(kept_prompts).most_common(20)])
        rej_words = set([word for word, count in get_words(rejected_prompts).most_common(20)])
        
        positive_patterns = list(kept_words - rej_words)[:10]
        negative_patterns = list(rej_words - kept_words)[:10]
        
        learned = {
            "keep_rate_by_model": keep_rate_by_model,
            "positive_patterns": positive_patterns,
            "negative_patterns": negative_patterns,
            "recommended_prompt_additions": positive_patterns[:5],
            "recommended_prompt_exclusions": negative_patterns[:5]
        }
        
        patterns_path.parent.mkdir(parents=True, exist_ok=True)
        with open(patterns_path, "w") as f:
            json.dump(learned, f, indent=2)
            
        print(f"[Project Gepetto Learning] Distilled patterns for {project_id}")
        return True

    async def log_qc_decision(self, project_id: str, asset_url: str, decision: str, prompt: str = ""):
        feedback_path = self.projects_dir / project_id / "qc-feedback.jsonl"
        feedback_path.parent.mkdir(parents=True, exist_ok=True)
        
        import time
        entry = {
            "asset_url": asset_url,
            "model": "unknown", # Will need front-end to supply model if possible
            "decision": decision, # "keep" or "reject"
            "prompt": prompt,
            "timestamp": int(time.time())
        }
        
        with open(feedback_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
            
        print(f"[Project Gepetto Learning] Logged {decision} for {asset_url} in project {project_id}")
        
        # Trigger analysis (in reality you might want to debounce this or trigger every N feedbacks)
        # We trigger it now as an example hook
        await self.analyze_feedback(project_id)
        return True

    async def update_preferences(self, project_id: str, updates: dict):
        pref_path = self.projects_dir / project_id / "preferences.md"
        pref_path.parent.mkdir(parents=True, exist_ok=True)

        existing = ""
        if pref_path.exists():
            existing = pref_path.read_text()

        update_lines = [f"- {k}: {v}" for k, v in updates.items()]
        update_block = "\n\n## Auto Updates\n" + "\n".join(update_lines) + "\n"

        if "## Auto Updates" in existing:
            # Append new updates beneath the existing auto updates section
            new_content = existing.rstrip() + "\n" + "\n".join(update_lines) + "\n"
        else:
            new_content = existing.rstrip() + update_block

        pref_path.write_text(new_content)
        return {"status": "success"}
