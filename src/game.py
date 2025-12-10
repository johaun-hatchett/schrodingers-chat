"""Core game logic for the physics problem-solving game."""
import json
import re
from typing import Any, List, Optional, Tuple

from environments import BaseEnvironment
from llm import GPT, LLMException
from messages import HumanMessage, AIMessage, MessageType, Transcript


class GameState:
    """Manages the state of the game, including the problem, environment, and transcript."""
    def __init__(self, environment: BaseEnvironment):
        """
        Initialize game state with an environment.
        
        Args:
            environment: An instance of a BaseEnvironment subclass
        """
        self.environment = environment
        self.problem = environment.get_problem_description()
        self.transcript = Transcript()
        self.probes = environment.get_available_probes()

    def add_to_transcript(self, message: MessageType) -> None:
        """Adds an entry to the transcript."""
        self.transcript.add(message)

    def get_transcript(self, serialize: bool=False) -> Transcript:
        """Returns the full transcript."""
        if serialize:
            return self.transcript.serialize()
        return self.transcript

    def save_transcript(self, filename="demo/transcript.json") -> None:
        """Saves the transcript to a file."""
        with open(filename, "w") as f:
            json.dump(self.transcript.serialize(), f, indent=4)


def extract_numeric_answers(text: str) -> List[float]:
    """
    Extract numeric values from text that could be answers.
    Looks for numbers (including decimals) in the text.
    
    Args:
        text: The input text to search for numbers
        
    Returns:
        List of numeric values found in the text
    """
    # Pattern to match numbers (integers and decimals, including negative)
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    
    numeric_values = []
    for match in matches:
        try:
            value = float(match)
            numeric_values.append(value)
        except ValueError:
            continue
    
    return numeric_values


def _is_final_answer_llm(game_state: GameState, user_input: str, model: str = "gpt-4o-mini") -> bool:
    """
    Lightweight LLM check: decide if the user is proposing a final numeric answer.
    Returns True if the LLM replies "Yes", otherwise False.
    """
    prompt = f"""
You are judging if a student's latest message is offering a final numeric answer to the problem.
Problem: {game_state.problem}
Student message: "{user_input}"

Reply with exactly one word: "Yes" if the student is proposing a final numeric answer, otherwise "No".
Do not include punctuation or extra words.
"""
    try:
        llm = GPT(model)
        ai_msg = llm.generate_response(prompt, game_state.get_transcript())
        return ai_msg.content.strip().lower().startswith("yes")
    except LLMException:
        return False


def check_answer(game_state: GameState, user_input: str) -> Optional[Tuple[bool, str]]:
    """
    Check if the user's input contains a correct answer.
    
    Args:
        game_state: The current game state
        user_input: The user's input text
        
    Returns:
        Tuple of (is_correct, feedback_message) if an answer is found and validated,
        None if no valid numeric answer was found
    """
    numeric_answers = extract_numeric_answers(user_input)
    
    if not numeric_answers:
        return None

    # Use LLM to determine if this is a final answer attempt
    if not _is_final_answer_llm(game_state, user_input):
        return None
    
    # Check each numeric value against the environment's validate_answer method
    for answer_value in numeric_answers:
        is_correct, feedback = game_state.environment.validate_answer(answer_value)
        if is_correct:
            return (True, feedback)
    
    # If we found numbers but none were correct, return the last validation result
    if numeric_answers:
        _, feedback = game_state.environment.validate_answer(numeric_answers[-1])
        return (False, feedback)
    
    return None


def get_llm_response(human_message: HumanMessage, game_state: GameState, model: str = "gpt-4o-mini") -> AIMessage:
    """Acts as the gamemaster (LLM), responding to user actions and providing guidance."""
    # Use a more sophisticated prompt for the LLM
    environment_params = game_state.environment.get_parameters()
    full_prompt = f"""You are a physics tutor gamemaster.
    The user is solving the following problem: {game_state.problem}
    The current state of the environment is: {json.dumps(environment_params, indent=2)}

    Based on the user's latest action, provide a helpful response (you may use markdown and LaTeX formatting ($$...$$ for display; $...$ for inline math) if helpful). If the user is measuring something, provide the value from the environment.
    If the user is stuck, provide a Socratic hint: a hint that prompts the user to think about which step comes next. NEVER explicitly suggest a step or reveal the correct answer.
    If the user provides an answer, check it. If it is correct, say "Congratulations! You got it right!".
    Keep the conversation user-led, don't provide any information that is not explicitly asked for.
    """
    # TODO: add step tracking; make LLM aware of procedural steps to guide hinting
    # TODO: make steps align with "personality summary" components (e.g., calculation, intuition, etc.)
    # TODO: keep track of steps to provide progress to user at each turn

    llm = GPT(model)

    return llm.generate_response(full_prompt, game_state.get_transcript())

