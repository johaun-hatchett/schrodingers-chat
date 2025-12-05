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


def summarize_problem_solving(transcript: Transcript, model: str = "gpt-4o-mini") -> str:
    """Use an LLM to summarize the student's problem solving/critical thinking.
    
    Returns student-facing feedback with just the archetype codename (not the full overview).
    """
    archetypes = load_archetypes()
    
    # Build archetype reference text (just names and dimensions for student-facing output)
    archetype_text = ""
    if archetypes:
        archetype_text = "\n\n**Problem-Solving Archetypes (for identification only):**\n"
        archetype_text += "Based on the four dimensions, identify which archetype codename best matches the student:\n\n"
        for arch in archetypes:
            dims = arch["dimensions"]
            archetype_text += f"- **{arch['name']}**: {dims['conceptual_foundation']} / {dims['strategic_insight']} / {dims['mathematical_execution']} / {dims['reflective_intuition']}\n"
    
    prompt = f"""
You are an expert physics educator and learning scientist.
You will see a full transcript of an interaction between a **student** (role: user/human)
and an **AI tutor** (role: assistant/ai) working on a physics problem.

Your task is to write **brief, supportive, student-facing feedback** that helps the student understand their problem-solving and critical-thinking approach and how to improve it.

**Personality Rubric Framework:**
Assess the student along these four dimensions (each has two endpoints):

1. **Conceptual Foundation**: 
   - Principled (Concept-focused) vs Formulaic (Equation-focused)
   - Does the student understand the underlying physics concepts, or do they rely primarily on memorized equations?

2. **Strategic Insight**: 
   - Global (Outlines full path) vs Local (Step-by-step)
   - Does the student plan ahead and see the big picture, or do they work incrementally without a clear overall strategy?

3. **Mathematical Execution**: 
   - Algebraic (Symbolic) vs Numeric (Arithmetic)
   - Does the student work with symbols and general relationships, or do they jump to plugging in numbers?

4. **Reflective Intuition**: 
   - Reflective (Checks plausibility) vs Unreflective (Accepts final result)
   - Does the student question their answers and check if they make sense, or do they accept results without validation?
{archetype_text}
Focus on:
- How the student approached understanding the problem and gathering information.
- How they reasoned through the physics concepts and equations.
- How they used feedback from the tutor to refine their thinking.
- Any misconceptions or fragile understandings that showed up.

Write your response **directly to the student**, not about them in the third person.
Be specific, kind, and actionable. Avoid jargon where possible.

Structure your response in this format:

### Your problem-solving personality
Simply state the archetype codename that best matches the student (e.g., "Your problem-solving personality: **The Architect**" or "Your problem-solving personality: **The Craftsman**"). Do NOT include the full overview paragraph—just the codename.

### Overall approach
2-4 sentences summarizing how you tackled the problem and how your thinking evolved.

### Strengths to keep building on
- 2-4 bullet points highlighting concrete strengths in your reasoning, strategies, or persistence.

### Opportunities to grow your problem-solving
- 2-4 bullet points pointing out specific habits or ideas to refine, phrased constructively.

### Suggested next practice steps
- 2-4 very concrete suggestions for what you could practice next (e.g., kinds of problems, specific strategies to rehearse, or reflection prompts), tied to what happened in this transcript.
"""

    llm = GPT(model=model)
    ai_msg = llm.generate_response(prompt, transcript=transcript)
    return ai_msg.content


def get_tutor_insights(transcript: Transcript, model: str = "gpt-4o-mini") -> str:
    """Generate tutor-facing insights with full archetype overviews.
    
    Returns a summary that includes the archetype name and full overview paragraph
    to help tutors understand students at a high level.
    """
    archetypes = load_archetypes()
    
    # Build archetype reference text with full overviews for tutors
    archetype_text = ""
    if archetypes:
        archetype_text = "\n\n**Problem-Solving Archetypes (with full overviews):**\n"
        for arch in archetypes:
            dims = arch["dimensions"]
            archetype_text += f"- **{arch['name']}**: {dims['conceptual_foundation']} / {dims['strategic_insight']} / {dims['mathematical_execution']} / {dims['reflective_intuition']}\n"
            archetype_text += f"  {arch['overview']}\n\n"
    
    prompt = f"""
You are an expert physics educator analyzing a tutoring session transcript.
You will see a full transcript of an interaction between a **student** (role: user/human)
and an **AI tutor** (role: assistant/ai) working on a physics problem.

Your task is to provide **tutor-facing insights** that help the tutor understand this student's problem-solving approach at a high level.

**Personality Rubric Framework:**
Assess the student along these four dimensions (each has two endpoints):

1. **Conceptual Foundation**: 
   - Principled (Concept-focused) vs Formulaic (Equation-focused)

2. **Strategic Insight**: 
   - Global (Outlines full path) vs Local (Step-by-step)

3. **Mathematical Execution**: 
   - Algebraic (Symbolic) vs Numeric (Arithmetic)

4. **Reflective Intuition**: 
   - Reflective (Checks plausibility) vs Unreflective (Accepts final result)
{archetype_text}
Based on the transcript, identify which archetype best matches this student and provide the full archetype overview.
This will help the tutor understand the student's learning style and adapt their teaching approach accordingly.

Structure your response as:

### Student Archetype
[Archetype name, e.g., "The Architect"]

### Archetype Overview
[The full overview paragraph from the archetype definition above]

### Key Observations from This Session
- 2-3 bullet points highlighting specific behaviors or patterns observed in this transcript that align with or deviate from the archetype.
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
