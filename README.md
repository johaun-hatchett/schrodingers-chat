# Schrodinger's Chat: A Text-Based Educational Game Engine

Schrödinger's Chat is a text-based educational game where users interact with an AI gamemaster to solve physics problems. The project is designed to not only help users find the correct answer but also to analyze their problem-solving approach and provide personalized feedback.

## Features

*   **Interactive Physics Problems:** Solve a variety of physics problems by interacting with an AI tutor.
*   **AI-Powered Guidance:** The AI gamemaster provides Socratic hints to guide you without giving away the answer.
*   **Problem-Solving Analysis:** The system analyzes your approach and identifies your problem-solving archetype.
*   **Personalized Feedback:** Receive a detailed summary of your problem-solving style after completing a problem.
*   **Multiple Environments:** The game supports different physics problems, including:
    *   Block on an Incline
    *   Pendulum
    *   Projectile Motion
    *   Rocket Equation
*   **Web and CLI Interfaces:** Interact with the game through a user-friendly Streamlit web interface or a command-line interface.

## How to Run

There are two ways to run the application:

### 1. Streamlit Web Application

To run the web-based interface, execute the following command:

```bash
streamlit run src/app.py
```

This will open a new tab in your browser with the Schrödinger's Chat interface.

### 2. Command-Line Interface (CLI)

To run the game in your terminal, execute the following command:

```bash
python3 src/main.py
```

## Project Structure

The project is organized into the following directories:

*   `data/`: Contains the JSON files that define the problem-solving archetypes and the rubric for evaluating them.
    *   `archetypes.json`: Defines 16 different problem-solving archetypes based on four dimensions of problem-solving.
    *   `rubric.json`: Defines the criteria and endpoints for each dimension of the problem-solving rubric.
*   `src/`: Contains the Python source code for the application.
    *   `main.py`: The main entry point for the command-line interface.
    *   `app.py`: The entry point for the Streamlit web application.
    *   `environments.py`: Defines the different physics problem environments.
    *   `llm.py`: Handles communication with the language model.
    *   `messages.py`: Defines the data structures for messages in the conversation.
    *   `analyze.py`: Contains the logic for analyzing the user's problem-solving approach.
*   `outputs/`: Contains the output of the application, such as conversation transcripts.

## Problem-Solving Archetypes

The core of Schrödinger's Chat is its ability to analyze a user's problem-solving style and provide personalized feedback. This is done using a system of 16 archetypes, each representing a different approach to problem-solving. These archetypes are defined by four dimensions:

*   **Conceptual Foundation:** Whether the user's approach is based on first principles or on memorized formulas.
*   **Strategic Insight:** Whether the user plans the entire solution path upfront or works step-by-step.
*   **Mathematical Execution:** Whether the user prefers to work with symbolic algebra or with concrete numbers.
*   **Reflective Intuition:** Whether the user checks the plausibility of their results or accepts them without reflection.

By analyzing the user's interactions, the system can identify their dominant archetype and provide feedback to help them become a more effective problem-solver.

## Contributing

Contributions are welcome! If you have any ideas for new features, bug fixes, or improvements, please open an issue or submit a pull request.