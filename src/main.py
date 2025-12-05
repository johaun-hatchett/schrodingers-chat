import json
from typing import Any

from environments import BaseEnvironment, EnvironmentFactory, ProblemType
from llm import GPT, LLMException
from messages import HumanMessage, AIMessage, MessageType, Transcript
try:
    from rich.console import Console
    from rich.markdown import Markdown
    _RICH_AVAILABLE = True
    _console: Any = Console()
except Exception:
    _RICH_AVAILABLE = False
    _console = None


# TODO: add openai compatibility
# TODO: add documentation
# TODO: add summarization/analysis logic to determine feedback using LLM


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


def main():
    """The main game loop."""
    # Create environment - you can change ProblemType to switch between different problems
    # Available types: BLOCK_ON_INCLINE, PENDULUM, PROJECTILE_MOTION, ROCKET_EQUATION
    environment = EnvironmentFactory.create(ProblemType.BLOCK_ON_INCLINE)
    game_state = GameState(environment)

    print("\033[93mWelcome to the Physics Problem-Solving Game!")
    print(f"\n--- The Problem ---\n{game_state.problem}")
    print("\nDescribe your actions to the AI (e.g., 'measure mass', 'what are the forces?'). Type 'quit' to exit.\x1b[0m")

    while True:
        human_message = HumanMessage.create_from_prompt()
        game_state.add_to_transcript(human_message)

        if human_message.content.lower() == "quit":
            print("\n\x1b[34mThanks for playing!\x1b[0m")
            game_state.save_transcript()
            print("\033[93mTranscript saved to transcript.json\x1b[0m")
            break

        # Get the AI's response
        # TODO: add problem solving steps
        # TODO: add game termination logic; check for final answer (i.e., correct coefficient of friction) in user prompt and escape when it is given
        try:
            ai_message = get_llm_response(human_message, game_state, model="gpt-4o-mini")
            content = ai_message.content if hasattr(ai_message, "content") else str(ai_message)

            if "Congratulations! You got it right!" in content:
                print("\n\x1b[32mCongratulations! You got it right!\x1b[0m")
                game_state.save_transcript()
                print("\033[93mTranscript saved to transcript.json\x1b[0m")
                break

            # Render Markdown in terminal if available; otherwise fallback to plain text
            print(f"\n\x1b[34m{content}\x1b[0m")
            game_state.add_to_transcript(ai_message)
        except LLMException as e:
            print(f"\x1b[31mError communicating with the AI: {e}\x1b[0m")


if __name__ == "__main__":
    main()
