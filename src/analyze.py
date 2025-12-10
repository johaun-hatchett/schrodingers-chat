"""Summarize a student's problem-solving and critical-thinking from a transcript.

Usage (from project root):

    python demo/src/analyze.py demo/output/transcript.json

You can also pass any other transcript JSON file that follows the same
format as those saved by the game (`GameState.save_transcript`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from llm import GPT, LLMException
from messages import HumanMessage, AIMessage, BaseMessage, Transcript


def _message_from_dict(entry: dict) -> BaseMessage:
    """Convert a serialized message dict back into a message object."""
    speaker = entry.get("speaker", "")
    content = entry.get("content", "")

    if speaker == "human":
        return HumanMessage(content)
    if speaker == "ai":
        return AIMessage(content)
    # Fallback – preserve unknown speakers
    return BaseMessage(speaker=speaker or "unknown", content=content)


def load_archetypes() -> list[dict]:
    """Load the archetype definitions from archetypes.json."""
    archetypes_path = Path(__file__).parent.parent / "data" / "archetypes.json"
    try:
        with archetypes_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def load_transcript(path: Path) -> Transcript:
    """Load a transcript JSON file into a `Transcript` object."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        raise SystemExit(f"Transcript file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in transcript file: {path}\n{exc}") from exc

    if not isinstance(data, list):
        raise SystemExit(f"Transcript JSON must be a list of messages, got {type(data)!r}")

    messages: List[BaseMessage] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        messages.append(_message_from_dict(entry))

    return Transcript(messages)


def generate_likert_scores(transcript: Transcript, model: str = "gpt-4o-mini") -> list[dict]:
    """Generate value-neutral Likert scores (-2..+2) for the four dimensions."""
    prompt = """
You are an expert physics educator. Score the student on four dimensions using a balanced, value-neutral Likert scale from -2 to +2, where -2 is the first endpoint, +2 is the second endpoint, and 0 is balanced/mixed. Return JSON only.

Dimensions (in order):
1) Conceptual Foundation — low: Principled (concept-focused), high: Formulaic (equation-focused)
2) Strategic Insight — low: Global (outlines full path), high: Local (step-by-step)
3) Mathematical Execution — low: Algebraic (symbolic), high: Numeric (arithmetic)
4) Reflective Intuition — low: Reflective (checks plausibility), high: Unreflective (accepts result)

Return exactly:
{
  "dimensions": [
    {"name": "Conceptual Foundation", "scale": <int -2..2>, "low_label": "Principled", "high_label": "Formulaic", "rationale": "<1-2 sentences>"},
    {"name": "Strategic Insight", "scale": <int -2..2>, "low_label": "Global", "high_label": "Local", "rationale": "<1-2 sentences>"},
    {"name": "Mathematical Execution", "scale": <int -2..2>, "low_label": "Algebraic", "high_label": "Numeric", "rationale": "<1-2 sentences>"},
    {"name": "Reflective Intuition", "scale": <int -2..2>, "low_label": "Reflective", "high_label": "Unreflective", "rationale": "<1-2 sentences>"}
  ]
}
No prose outside the JSON. Do not change labels. Keep dimensions in this order.
"""
    llm = GPT(model=model)
    ai_msg = llm.generate_response(prompt, transcript=transcript)

    try:
        payload = json.loads(ai_msg.content)
        dims = payload.get("dimensions", [])
        if not isinstance(dims, list):
            raise ValueError("dimensions not a list")
        return dims
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise LLMException(f"Failed to parse Likert scores JSON: {exc}") from exc


def summarize_problem_solving(
    transcript: Transcript,
    model: str = "gpt-4o-mini",
    scores: list[dict] | None = None,
) -> str:
    """Generate student-facing feedback with Likert (-2..+2) scores per dimension."""

    scores = scores or generate_likert_scores(transcript, model=model)
    score_lines = "\n".join(
        [
            f"- {s.get('name')}: scale {s.get('scale')} (low='{s.get('low_label')}', high='{s.get('high_label')}'). Rationale: {s.get('rationale', '')}"
            for s in scores
        ]
    )

    prompt = f"""
You are an expert physics educator and learning scientist.
You will see a full transcript of an interaction between a **student** (role: user/human)
and an **AI tutor** (role: assistant/ai) working on a physics problem.

Your task is to write **brief, supportive, student-facing feedback** that helps the student understand their problem-solving and critical-thinking approach and how to improve it. Do NOT assign archetypes.

**Problem-Solving Lens (value-neutral):**
Assess the student along these four dimensions using a balanced Likert scale from -2 to +2, where -2 is the first endpoint, +2 is the second endpoint, and 0 is balanced/mixed:

1. **Conceptual Foundation**: 
   - Principled (Concept-focused) ↔ Formulaic (Equation-focused)
   - Does the student understand the underlying physics concepts, or do they rely primarily on memorized equations?

2. **Strategic Insight**: 
   - Global (Outlines full path) ↔ Local (Step-by-step)
   - Does the student plan ahead and see the big picture, or do they work incrementally without a clear overall strategy?

3. **Mathematical Execution**: 
   - Algebraic (Symbolic) ↔ Numeric (Arithmetic)
   - Does the student work with symbols and general relationships, or do they jump to plugging in numbers?

4. **Reflective Intuition**: 
   - Reflective (Checks plausibility) ↔ Unreflective (Accepts final result)
   - Does the student question their answers and check if they make sense, or do they accept results without validation?

Focus on:
- How the student approached understanding the problem and gathering information.
- How they reasoned through the physics concepts and equations.
- How they used feedback from the tutor to refine their thinking.
- Any misconceptions or fragile understandings that showed up.

Write your response **directly to the student**, not about them in the third person.
Be specific, kind, and actionable. Avoid jargon where possible.

Structure your response in this format:

### Summary of your approach
4-5 sentences summarizing how you tackled the problem and how your thinking evolved. Include both strengths and areas for growth in this summary.

### Deep dive: how you showed up on the four dimensions
For each dimension, write 2-3 sentences in second person (addressing the student as "you") describing where they landed qualitatively (e.g., "You leaned toward a principled approach" or "You worked more locally, step-by-step"). Do NOT mention the numeric scale value (-2..+2) in the text. Focus on the qualitative description of their approach with specific evidence from the transcript. Write each dimension description as a complete sentence starting with the dimension name, not as a bullet point. Always use "you" and "your" throughout.
Conceptual Foundation: 2-3 sentences in second person describing the qualitative tendency (principled vs formulaic) with specific examples from the transcript.
Strategic Insight: 2-3 sentences in second person describing the qualitative tendency (global vs local) with specific examples from the transcript.
Mathematical Execution: 2-3 sentences in second person describing the qualitative tendency (algebraic vs numeric) with specific examples from the transcript.
Reflective Intuition: 2-3 sentences in second person describing the qualitative tendency (reflective vs unreflective) with specific examples from the transcript.

### Suggested next practice steps
Begin with a lead-in sentence that ties the next steps to what was observed in this session. Then provide 2-4 very concrete suggestions for what you could practice next (e.g., kinds of problems, specific strategies to rehearse, or reflection prompts), tied to what happened in this transcript.

Use the precomputed Likert scores below for consistency across views; do not change them. Align your text descriptions to these values:
{score_lines}

Do not include any JSON in the output. Neither endpoint is “better”—just describe the tendency observed.
"""

    llm = GPT(model=model)
    ai_msg = llm.generate_response(prompt, transcript=transcript)
    return ai_msg.content


def get_tutor_insights(
    transcript: Transcript,
    model: str = "gpt-4o-mini",
    scores: list[dict] | None = None,
) -> str:
    """Generate tutor-facing insights with Likert (-2..+2) scores per dimension."""

    scores = scores or generate_likert_scores(transcript, model=model)
    score_lines = "\n".join(
        [
            f"- {s.get('name')}: scale {s.get('scale')} (low='{s.get('low_label')}', high='{s.get('high_label')}'). Rationale: {s.get('rationale', '')}"
            for s in scores
        ]
    )

    prompt = f"""
You are an expert physics educator analyzing a tutoring session transcript.
You will see a full transcript of an interaction between a **student** (role: user/human)
and an **AI tutor** (role: assistant/ai) working on a physics problem.

Provide **tutor-facing insights** across the four dimensions below, using a balanced Likert scale from -2 to +2 (value-neutral: -2 = first endpoint, +2 = second endpoint, 0 = balanced/mixed). Do not assign archetype labels.

**Four-dimension rubric (value-neutral):**
1) Conceptual Foundation — Principled (concept-focused) ↔ Formulaic (equation-focused)
2) Strategic Insight — Global (outlines full path) ↔ Local (step-by-step)
3) Mathematical Execution — Algebraic (symbolic) ↔ Numeric (arithmetic)
4) Reflective Intuition — Reflective (checks plausibility) ↔ Unreflective (accepts result)

Structure your response as:

### Four-dimension snapshot
- Conceptual Foundation: placement with evidence and the -2..+2 value.
- Strategic Insight: placement with evidence and the -2..+2 value.
- Mathematical Execution: placement with evidence and the -2..+2 value.
- Reflective Intuition: placement with evidence and the -2..+2 value.

### Key observations from this session
- 2-4 bullets on notable behaviors, misconceptions, or turning points.

### Suggested tutor moves
- 2-4 bullets on targeted interventions or scaffolds to try next time, tied to the observed dimensions.

Use the precomputed Likert scores below for consistency across views; do not change them. Align your text descriptions to these values:
{score_lines}

Do not include any JSON in the output. Neither endpoint is “better”—just describe the tendency observed.
"""

    llm = GPT(model=model)
    ai_msg = llm.generate_response(prompt, transcript=transcript)
    return ai_msg.content


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize a student's problem-solving and critical-thinking "
            "from a physics tutoring transcript JSON."
        )
    )
    parser.add_argument(
        "transcript_path",
        type=str,
        help="Path to the transcript JSON file (as saved by the game).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5",
        help="OpenAI chat model name to use (default: gpt-5).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Optional path to save the summary as a text file. If omitted, prints to stdout.",
    )

    args = parser.parse_args(argv)

    transcript_path = Path(args.transcript_path)
    transcript = load_transcript(transcript_path)

    try:
        summary = summarize_problem_solving(transcript, model=args.model)
    except LLMException as e:
        print(f"Error generating summary from LLM: {e}", file=sys.stderr)
        return 1

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.write_text(summary, encoding="utf-8")
        except OSError as e:
            print(f"Failed to write summary to {output_path}: {e}", file=sys.stderr)
            return 1
        print(f"Summary written to {output_path}")
    else:
        print(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
