---
description: Summarize a batch of Skyrim mod descriptions for the game-overview README. Detail depends on mod class (gameplay/quest = full verbatim, armor_weapon/follower/other = medium, everything else = brief).
model: nvidia/nvidia/nemotron-3-nano-30b-a3b
subtask: true
---

You are summarizing a batch of mods from Gate to Sovngarde (GTS), a curated Skyrim Anniversary Edition modlist. Use the project's Gate to Sovngarde, Skyrim Modding, and Skyrim Research skills to understand which mods are core gameplay pillars vs decorative additions — this determines the verbatim vs summarized output rules below.

Each mod is in this format:

```
---
name: Mod Name
class: gameplay|quest|texture|audio|animation|ui|visual_env|armor_weapon|npc|follower|fix|framework|other
description: ...
---
```

Detail level depends on class:

- **gameplay / quest**: Normalize any BBCode formatting (e.g. `[font=Georgia]SCHOOL NAME[/font]`) into simple Markdown headings. Discard image/video embeds, technical requirements, and other fluff. Preserve important sections — descriptions of spells, effects, artifacts, systems/mechanics. Use multiple logical lines encoded as literal `\n` when headings, lists, or spacing carry meaning. Concise but detailed.
- **armor_weapon / follower / other**: Write a 1-2 sentence factual summary of what this mod adds or changes.
- **texture / audio / animation / ui / npc / fix / framework / visual_env**: Write a one-sentence factual summary.

CRITICAL RULES — You MUST follow these exactly:
1. Output EXACTLY one transport line per mod, nothing else before, between, or after.
2. Each line MUST be: `EXACT_MOD_NAME: summary text here`
3. You MAY preserve headings, bullets, emoji, lists, and other formatting when it carries content signal, but encode internal newlines as literal `\n` so each mod remains on one transport line.
4. Do NOT wrap in code blocks or quotes.
5. Do NOT add blank lines between entries.
6. The ONLY output should be N transport lines (one per mod), each in the format `Name: text`.
7. For gameplay/quest mods, normalize any BBCode formatting to simple Markdown. Do not return a single-sentence overview when the input contains named spells, perks, artifacts, effects, systems, or mechanics. Preserve those named entries and their effects/details. Use literal `\n` between logical headings/list items when needed. Do not keep irrelevant fluff, image/video embeds, or technical install requirements. Do not destroy meaningful formatting.
8. Every single mod MUST have a line. Do not skip or merge.
9. Do NOT use any tools. Only output the summary lines.

$ARGUMENTS
