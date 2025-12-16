from openai import OpenAI
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
import json

from messages import AIMessage, Transcript, HumanMessage
from environments import BaseEnvironment

class LLMException(Exception):
    """Exception raised for errors in the LLM."""
    pass


class BaseLLM(ABC):
    """Abstract base class for LLMs."""
    @abstractmethod
    def generate_response(
        self,
        prompt: str,
        transcript: Optional[Transcript] = None,
        instructions: Optional[str] = None
    ) -> AIMessage:
        """Generates a response from the LLM."""
        pass


class GPT(BaseLLM):
    """GPT LLM."""
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        """Initializes the LLM."""
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def generate_response(
        self, 
        prompt: str, 
        transcript: Optional[Transcript] = None,
        instructions: Optional[str] = None
    ) -> AIMessage:
        """
        Generates a response from the LLM.
        
        Args:
            prompt: The user prompt/message
            transcript: Optional transcript containing conversation history
            instructions: Optional system-level instructions (added first as system message)
        
        Returns:
            AIMessage with the LLM's response
        """
        messages: List[Dict[str, str]] = []
        
        # Add instructions first as a system message if provided
        if instructions:
            messages.append({"role": "system", "content": instructions})
        
        # Add conversation history from transcript
        if transcript:
            for msg in transcript.serialize():
                if msg["speaker"] == "human":
                    messages.append({"role": "user", "content": msg["content"]})
                elif msg["speaker"] == "ai":
                    messages.append({"role": "assistant", "content": msg["content"]})
                else:
                    # fallback for unknown speaker
                    messages.append({"role": "system", "content": msg["content"]})
        
        # Add the current prompt as a user message
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return AIMessage(response.choices[0].message.content)
        except Exception as e:
            raise LLMException(f"Error generating response from {self.model}: {e}")


class Tutor:
    """Tutor (gamemaster) that provides guidance to students. Blind to correct answers."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        """Initialize the Tutor with a GPT backend."""
        self.llm = GPT(model=model, api_key=api_key)
        self.model = model
    
    def _build_instruction_prompt(self, problem: str, environment_params: Dict) -> str:
        """Build the instruction prompt for the tutor."""
        return f"""You are a physics tutor gamemaster.
The user is solving the following problem: {problem}
The current state of the environment (only what the student could in principle observe) is: {json.dumps(environment_params, indent=2)}

Based on the user's latest action, provide a helpful response (you may use markdown and LaTeX formatting ($$...$$ for display; $...$ for inline math) if helpful). If the user is measuring something, provide the value from the environment.
If the user is stuck, provide a Socratic hint: a hint that prompts the user to think about which step comes next. NEVER explicitly suggest a step or reveal the correct answer.

IMPORTANT:
- You do NOT have direct access to the correct numeric answer, and you MUST NOT try to infer or state whether an answer is exactly correct.
- A separate hidden validator will check the student's final numeric answers and provide explicit feedback messages (which will appear in the conversation history).
- When you see such feedback, you can react to it pedagogically (e.g., help the student reflect on mistakes or next steps) but do not override or re-check the validator.

Keep the conversation user-led, and don't provide any information that is not explicitly asked for.
"""
    
    def generate_response(
        self, 
        human_message: HumanMessage, 
        game_state, 
        transcript: Optional[Transcript] = None
    ) -> AIMessage:
        """
        Generate a tutor response to a human message.
        
        Args:
            human_message: The student's message
            game_state: The current game state (for problem and environment info)
            transcript: Optional transcript (if None, uses game_state.get_transcript())
        
        Returns:
            AIMessage with the tutor's response
        """
        if transcript is None:
            transcript = game_state.get_transcript()
        
        environment_params = game_state.environment.get_parameters()
        instructions = self._build_instruction_prompt(
            game_state.problem, 
            environment_params
        )
        
        return self.llm.generate_response(
            prompt=human_message.content,
            transcript=transcript,
            instructions=instructions
        )


class Validator:
    """Validator that checks if a student message is a final answer attempt."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        """Initialize the Validator with a GPT backend."""
        self.llm = GPT(model=model, api_key=api_key)
        self.model = model
    
    def _build_instruction_prompt(self, problem: str) -> str:
        """Build the instruction prompt for answer detection."""
        return f"""You are judging if a student's latest message is offering a final numeric answer to the problem.
Problem: {problem}

Reply with exactly one word: "Yes" if the student is proposing a final numeric answer, otherwise "No".
Do not include punctuation or extra words.
"""
    
    def is_final_answer(
        self, 
        human_message: HumanMessage, 
        problem: str,
        transcript: Optional[Transcript] = None
    ) -> bool:
        """
        Check if the human message is proposing a final numeric answer.
        
        Args:
            human_message: The student's message
            problem: The problem description
            transcript: Optional transcript for context
        
        Returns:
            True if the message is a final answer attempt, False otherwise
        """
        instructions = self._build_instruction_prompt(problem)
        
        try:
            ai_msg = self.llm.generate_response(
                prompt=human_message.content,
                transcript=transcript,
                instructions=instructions
            )
            return ai_msg.content.strip().lower().startswith("yes")
        except LLMException:
            return False


class Analyst:
    """Analyst that generates insights and summaries from tutoring transcripts."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        """Initialize the Analyst with a GPT backend."""
        self.llm = GPT(model=model, api_key=api_key)
        self.model = model
    
    def _build_likert_instructions(self) -> str:
        """Build the instruction prompt for Likert scoring."""
        return """You are an expert physics educator. Score the student on four dimensions using a balanced, value-neutral Likert scale from -2 to +2, where -2 is the first endpoint, +2 is the second endpoint, and 0 is balanced/mixed. Return JSON only.

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
    
    def generate_likert_scores(self, transcript: Transcript) -> list[dict]:
        """
        Generate value-neutral Likert scores (-2..+2) for the four dimensions.
        
        Args:
            transcript: The transcript to analyze
        
        Returns:
            List of dimension dictionaries with scores and rationales
        
        Raises:
            LLMException: If the response cannot be parsed as JSON
        """
        instructions = self._build_likert_instructions()
        prompt = "Analyze the transcript and return the Likert scores as JSON."
        
        ai_msg = self.llm.generate_response(
            prompt=prompt,
            transcript=transcript,
            instructions=instructions
        )
        
        try:
            payload = json.loads(ai_msg.content)
            dims = payload.get("dimensions", [])
            if not isinstance(dims, list):
                raise ValueError("dimensions not a list")
            return dims
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise LLMException(f"Failed to parse Likert scores JSON: {exc}") from exc
    
    def _build_student_feedback_instructions(self, score_lines: str) -> str:
        """Build the instruction prompt for student-facing feedback."""
        return f"""You are an expert physics educator and learning scientist.
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

**Formatting:**
- Use LaTeX formatting for equations, symbols, and mathematical expressions where appropriate.
- Use `$$...$$` for display math (block equations) and `$...$` for inline math (symbols within text).
- For example: "You used the equation $F = ma$" or "The relationship $$E = mc^2$$ shows..."

Structure your response in this format:

### Summary of your approach
4-5 sentences summarizing how you tackled the problem and how your thinking evolved. Include both strengths and areas for growth in this summary.

### Deep dive: how you showed up on the four dimensions
For each dimension, write 2-3 sentences in second person (addressing the student as "you") describing where they landed qualitatively (e.g., "You leaned toward a principled approach" or "You worked more locally, step-by-step"). Do NOT mention the numeric scale value (-2..+2) in the text. Focus on the qualitative description of their approach with specific evidence from the transcript. Write each dimension description as a complete sentence starting with the dimension name, not as a bullet point. Always use "you" and "your" throughout.
Conceptual Foundation: 2-3 sentences in second person describing the qualitative tendency (principled vs formulaic) with specific examples from the transcript.
Strategic Insight: 2-3 sentences in second person describing the qualitative tendency (global vs local) with specific examples from the transcript.
Mathematical Execution: 2-3 sentences in second person describing the qualitative tendency (algebraic vs numeric) with specific examples from the transcript.
Reflective Intuition: 2-3 sentences in second person describing the qualitative tendency (reflective vs unreflective) with specific examples from the transcript.

### Strengths to keep building on
Identify 2-3 specific strengths the student demonstrated during this problem-solving session. Be concrete and reference specific moments or patterns from the transcript. Write in second person, addressing the student directly.

### Opportunities to grow your problem-solving
Identify 2-3 specific areas where the student could develop their problem-solving approach. Be constructive and supportive, focusing on growth opportunities rather than weaknesses. Write in second person, addressing the student directly.

### Suggested next practice steps
Begin with a lead-in sentence that ties the next steps to what was observed in this session. Then provide 2-4 very concrete suggestions for what you could practice next (e.g., kinds of problems, specific strategies to rehearse, or reflection prompts), tied to what happened in this transcript.

Use the precomputed Likert scores below for consistency across views; do not change them. Align your text descriptions to these values:
{score_lines}

Do not include any JSON in the output. Neither endpoint is "better"—just describe the tendency observed.
"""
    
    def summarize_problem_solving(
        self,
        transcript: Transcript,
        scores: list[dict] | None = None
    ) -> str:
        """
        Generate student-facing feedback with Likert (-2..+2) scores per dimension.
        
        Args:
            transcript: The transcript to analyze
            scores: Optional precomputed Likert scores (if None, will generate them)
        
        Returns:
            String containing the student-facing feedback
        """
        if scores is None:
            scores = self.generate_likert_scores(transcript)
        
        score_lines = "\n".join(
            [
                f"- {s.get('name')}: scale {s.get('scale')} (low='{s.get('low_label')}', high='{s.get('high_label')}'). Rationale: {s.get('rationale', '')}"
                for s in scores
            ]
        )
        
        instructions = self._build_student_feedback_instructions(score_lines)
        prompt = "Analyze the transcript and provide student-facing feedback based on the precomputed scores."
        
        ai_msg = self.llm.generate_response(
            prompt=prompt,
            transcript=transcript,
            instructions=instructions
        )
        return ai_msg.content
    
    def _build_tutor_insights_instructions(self, score_lines: str) -> str:
        """Build the instruction prompt for tutor-facing insights."""
        return f"""You are an expert physics educator analyzing a tutoring session transcript.
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

Do not include any JSON in the output. Neither endpoint is "better"—just describe the tendency observed.
"""
    
    def get_tutor_insights(
        self,
        transcript: Transcript,
        scores: list[dict] | None = None
    ) -> str:
        """
        Generate tutor-facing insights with Likert (-2..+2) scores per dimension.
        
        Args:
            transcript: The transcript to analyze
            scores: Optional precomputed Likert scores (if None, will generate them)
        
        Returns:
            String containing the tutor-facing insights
        """
        if scores is None:
            scores = self.generate_likert_scores(transcript)
        
        score_lines = "\n".join(
            [
                f"- {s.get('name')}: scale {s.get('scale')} (low='{s.get('low_label')}', high='{s.get('high_label')}'). Rationale: {s.get('rationale', '')}"
                for s in scores
            ]
        )
        
        instructions = self._build_tutor_insights_instructions(score_lines)
        prompt = "Analyze the transcript and provide tutor-facing insights based on the precomputed scores."
        
        ai_msg = self.llm.generate_response(
            prompt=prompt,
            transcript=transcript,
            instructions=instructions
        )
        return ai_msg.content