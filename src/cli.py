"""Command-line interface for the physics problem-solving game."""
from environments import EnvironmentFactory, ProblemType
from llm import LLMException
from messages import HumanMessage, AIMessage
from game import GameState, get_llm_response, check_answer


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

        # Check if the user provided a numeric answer
        answer_check = check_answer(game_state, human_message.content)
        
        if answer_check is not None:
            is_correct, feedback = answer_check
            
            if is_correct:
                print(f"\n\x1b[32m🎉 {feedback}\x1b[0m")
                # Still get LLM response for additional feedback
                try:
                    ai_message = get_llm_response(human_message, game_state, model="gpt-4o-mini")
                    content = ai_message.content if hasattr(ai_message, "content") else str(ai_message)
                    if content and "Congratulations" not in content:
                        print(f"\n\x1b[34m{content}\x1b[0m")
                    game_state.add_to_transcript(ai_message)
                except LLMException:
                    # If LLM fails, still record the correct answer
                    ai_feedback = AIMessage(f"🎉 {feedback}")
                    game_state.add_to_transcript(ai_feedback)
                
                game_state.save_transcript()
                print("\033[93mTranscript saved to transcript.json\x1b[0m")
                break
            else:
                # Answer was provided but incorrect
                print(f"\n\x1b[33m{feedback}\x1b[0m")
                # Still get LLM response for guidance
                try:
                    ai_message = get_llm_response(human_message, game_state, model="gpt-4o-mini")
                    content = ai_message.content if hasattr(ai_message, "content") else str(ai_message)
                    if content:
                        print(f"\n\x1b[34m{content}\x1b[0m")
                    game_state.add_to_transcript(ai_message)
                except LLMException as e:
                    print(f"\x1b[31mError communicating with the AI: {e}\x1b[0m")
        else:
            # No numeric answer detected, proceed with normal LLM response
            try:
                ai_message = get_llm_response(human_message, game_state, model="gpt-4o-mini")
                content = ai_message.content if hasattr(ai_message, "content") else str(ai_message)

                # Legacy check for LLM saying congratulations (backup)
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

