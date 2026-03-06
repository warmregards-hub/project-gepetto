# Global Agent Preferences
# These apply to ALL projects unless overridden by per-project preferences.

## Aspect Ratios
- UGC content (selfies, testimonials, lifestyle, talking head, product demos): ALWAYS 9:16 portrait
- Product shots, still life, pack shots: ALWAYS 1:1 square
- Cinematic / brand film stills: ALWAYS 16:9 landscape
- Default if not specified: 1:1

## Generation Defaults
- Variants per request: 4 (2 concepts × 2 variants)
- Default style: photorealistic unless brief specifies otherwise
- Default image model: gpt-image-1
- Default video model: veo-3.1-fast

## UGC Rules
- UGC images must look organic and unposed — not professional photography
- Natural lighting preferred (window light, ambient)
- Slight motion blur or camera shake is acceptable and preferred
- No studio lighting, no seamless backgrounds
- Subject should look directly at camera unless brief specifies otherwise

## Quality Gates (human review — NO automated scoring)
- All variants go to the human review gallery
- Only auto-reject: API error, corrupt file, or completely blank image
- Human always makes final keep/reject decision

## Prompt Construction
- Always include aspect ratio as parameter (e.g. --ar 9:16 for Midjourney, or in prompt text for others)
- Always include the model explicitly in the tool call
- Keep prompts concise — describe the shot, not a novel

## Auto Updates
- selfie.aspect_ratio: 9:16
