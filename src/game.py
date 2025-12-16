"""Core game logic for the physics problem-solving game."""
import json
import re
from typing import Any, List, Optional, Tuple

from environments import BaseEnvironment
from llm import Tutor, Validator, Analyst, LLMException
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


def validator_turn(game_state: GameState, user_input: str, model: str = "gpt-4o-mini") -> Optional[Tuple[bool, str]]:
    """
    Validator turn: Check if the user's input contains a correct answer.
    
    Args:
        game_state: The current game state
        user_input: The user's input text
        model: The LLM model to use for answer detection
        
    Returns:
        Tuple of (is_correct, feedback_message) if an answer is found and validated,
        None if no valid numeric answer was found
    """
    def extract_numeric_answers(text: str) -> List[float]:
        """Extract numeric values from text that could be answers."""
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
    
    def is_final_answer_attempt(text: str) -> bool:
        """Check if the user is proposing a final numeric answer."""
        validator = Validator(model=model)
        human_msg = HumanMessage(text)
        return validator.is_final_answer(human_msg, game_state.problem, game_state.get_transcript())
    
    # Extract numeric values from the input
    numeric_answers = extract_numeric_answers(user_input)
    
    if not numeric_answers:
        return None

    # Use LLM to determine if this is a final answer attempt
    if not is_final_answer_attempt(user_input):
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


def tutor_turn(human_message: HumanMessage, game_state: GameState, model: str = "gpt-4o-mini") -> AIMessage:
    """
    Tutor turn: Generate a response to the student's message.
    
    Args:
        human_message: The student's message
        game_state: The current game state
        model: The LLM model to use
    
    Returns:
        AIMessage with the tutor's response
    """
    tutor = Tutor(model=model)
    return tutor.generate_response(human_message, game_state)


def analyst_turn(
    game_state: GameState,
    model: str = "gpt-4o-mini",
    scores: Optional[List[dict]] = None
) -> Tuple[str, List[dict]]:
    """
    Analyst turn: Generate problem-solving summary and Likert scores from the transcript.
    
    Args:
        game_state: The current game state
        model: The LLM model to use
        scores: Optional precomputed Likert scores (if None, will generate them)
    
    Returns:
        Tuple of (summary: str, scores: List[dict]) containing the student-facing
        feedback summary and the Likert dimension scores
    """
    analyst = Analyst(model=model)
    transcript = game_state.get_transcript()
    
    if scores is None:
        scores = analyst.generate_likert_scores(transcript)
    
    summary = analyst.summarize_problem_solving(transcript, scores=scores)
    
    return (summary, scores)

