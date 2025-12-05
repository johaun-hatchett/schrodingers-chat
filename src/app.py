import streamlit as st
import json
from typing import Optional

from main import GameState, get_llm_response
from environments import EnvironmentFactory, ProblemType
from messages import HumanMessage, AIMessage
from llm import LLMException
from analyze import summarize_problem_solving


def initialize_game_state(problem_type: ProblemType) -> GameState:
    """Initialize or reinitialize the game state."""
    environment = EnvironmentFactory.create(problem_type)
    return GameState(environment)


def main():
    st.set_page_config(
        page_title="Schrodinger's Chat",
        page_icon="🐈‍⬛",
        layout="wide"
    )
    
    st.title("🐈‍⬛ Schrodinger's Chat")
    st.markdown("---")
    
    # Initialize session state
    if "game_state" not in st.session_state:
        st.session_state.game_state = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "problem_type" not in st.session_state:
        st.session_state.problem_type = ProblemType.BLOCK_ON_INCLINE
    # Default tutor model is gpt-5; a temporary "Answer now" action can use a faster model.
    if "model" not in st.session_state:
        st.session_state.model = "gpt-5"
    if "game_started" not in st.session_state:
        st.session_state.game_started = False
    if "game_completed" not in st.session_state:
        st.session_state.game_completed = False
    if "summary" not in st.session_state:
        st.session_state.summary = None
    # When True, always use the faster model (gpt-4o) instead of the default (gpt-5)
    if "use_fast_model" not in st.session_state:
        st.session_state.use_fast_model = False
    
    # Sidebar for problem selection and controls
    with st.sidebar:
        st.header("Game Controls")

        # Model behavior info and "Answer fast" option (always available)
        st.caption(
            "The tutor normally uses **gpt-5** for higher-quality reasoning. "
            "You can switch to a faster but slightly less capable model "
            "(gpt-4o) using the toggle below."
        )
        st.session_state.use_fast_model = st.checkbox(
            "⚡ Answer fast (use gpt-4o)",
            value=st.session_state.use_fast_model,
        )

        st.markdown("---")
        
        # Problem type selection
        problem_type_map = {
            "Block on Incline": ProblemType.BLOCK_ON_INCLINE,
            "Pendulum": ProblemType.PENDULUM,
            "Projectile Motion": ProblemType.PROJECTILE_MOTION,
            "Rocket Equation": ProblemType.ROCKET_EQUATION,
        }
        
        # Get current problem type index safely
        current_problem_values = list(problem_type_map.values())
        try:
            current_index = current_problem_values.index(st.session_state.problem_type)
        except ValueError:
            current_index = 0
            st.session_state.problem_type = ProblemType.BLOCK_ON_INCLINE
        
        selected_problem = st.selectbox(
            "Select Problem Type",
            options=list(problem_type_map.keys()),
            index=current_index,
            disabled=st.session_state.game_started
        )
        
        st.session_state.problem_type = problem_type_map[selected_problem]
        
        # Start/Reset button
        if not st.session_state.game_started:
            if st.button("Start Game", type="primary", use_container_width=True):
                st.session_state.game_state = initialize_game_state(st.session_state.problem_type)
                st.session_state.game_started = True
                st.session_state.messages = []
                st.session_state.game_completed = False
                st.rerun()
        else:
            if st.button("Reset Game", use_container_width=True):
                st.session_state.game_state = None
                st.session_state.game_started = False
                st.session_state.messages = []
                st.session_state.game_completed = False
                st.rerun()
        
        # Save transcript button
        if st.session_state.game_started and st.session_state.messages:
            if st.button("Save Transcript", use_container_width=True):
                if st.session_state.game_state:
                    st.session_state.game_state.save_transcript("demo/transcript.json")
                    st.success("Transcript saved to demo/transcript.json")
    
    # Main content area
    if not st.session_state.game_started:
        st.info("👈 Select a problem type and click 'Start Game' to begin!")
    else:
        # Display problem description
        if st.session_state.game_state:
            st.subheader("📋 Problem Description")
            st.markdown(f"**{st.session_state.game_state.problem}**")
            st.markdown("---")
        
        # Display conversation history
        st.subheader("💬 Conversation")
        
        # Show messages
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(message["content"])
        
        # Show completion message if game is completed
        if st.session_state.game_completed:
            st.success("🎉 Congratulations! You solved the problem!")
            # Generate and display post-game learning summary
            if st.session_state.game_state:
                if st.session_state.summary is None:
                    with st.spinner("Generating your learning summary..."):
                        try:
                            transcript = st.session_state.game_state.get_transcript()
                            st.session_state.summary = summarize_problem_solving(
                                transcript,
                                model=st.session_state.model,
                            )
                        except LLMException as e:
                            st.session_state.summary = ""
                            st.error(f"Error generating learning summary: {e}")

                if st.session_state.summary:
                    st.subheader("🧠 Your problem-solving summary")
                    st.markdown(st.session_state.summary)

            if st.button("Start New Game"):
                st.session_state.game_state = None
                st.session_state.game_started = False
                st.session_state.messages = []
                st.session_state.game_completed = False
                st.session_state.summary = None
                st.session_state.use_fast_model = False
                st.rerun()
        else:
            # Chat input
            if prompt := st.chat_input("Describe your actions (e.g., 'measure mass', 'what are the forces?')"):
                # Add user message to chat
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Create human message and add to game state
                human_message = HumanMessage(prompt)
                if st.session_state.game_state:
                    st.session_state.game_state.add_to_transcript(human_message)
                
                # Display user message
                with st.chat_message("user"):
                    st.write(prompt)
                
                # Get AI response
                if st.session_state.game_state:
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            try:
                                # Choose model: default is gpt-5; "Answer fast" toggle uses gpt-4o.
                                model_to_use = "gpt-4o" if st.session_state.use_fast_model else st.session_state.model

                                ai_message = get_llm_response(
                                    human_message,
                                    st.session_state.game_state,
                                    model=model_to_use,
                                )
                                content = ai_message.content if hasattr(ai_message, "content") else str(ai_message)
                                
                                # Check if the answer is correct
                                if "Congratulations! You got it right!" in content:
                                    st.session_state.game_completed = True
                                    # Remove congratulations message from displayed content
                                    display_content = content.replace("Congratulations! You got it right!", "").strip()
                                else:
                                    display_content = content
                                
                                # Display AI response (markdown/LaTeX will be rendered)
                                if display_content:
                                    st.markdown(display_content)
                                
                                # Add to messages and transcript (save full content to transcript, but filtered to messages)
                                st.session_state.messages.append({"role": "assistant", "content": display_content if display_content else content})
                                st.session_state.game_state.add_to_transcript(ai_message)
                                
                            except LLMException as e:
                                error_msg = f"Error communicating with the AI: {e}"
                                st.error(error_msg)
                                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    
                    st.rerun()


if __name__ == "__main__":
    main()

