# Schrödinger's Chat

Schrödinger's Chat is a text-based educational game where students interact with an AI tutor to solve physics problems. The system provides Socratic guidance and analyzes problem-solving approaches across four dimensions, delivering personalized feedback with Likert-scale visualizations.

## Features

*   **Interactive Physics Problems:** Solve a variety of physics problems by interacting with an AI tutor.
*   **AI-Powered Guidance:** The AI tutor provides Socratic hints to guide you without giving away the answer.
*   **Problem-Solving Analysis:** The system analyzes your approach across four dimensions using a Likert scale (-2 to +2).
*   **Personalized Feedback:** Receive a detailed summary of your problem-solving style after completing a problem, including:
    *   Summary of your approach
    *   Deep dive into each dimension with visual Likert scales
    *   Next steps for improvement
*   **Multiple Environments:** The game supports different physics problems, including:
    *   Block on an Incline
    *   Pendulum
    *   Projectile Motion
    *   Rocket Equation
*   **Session History:** View and review your past problem-solving sessions.
*   **Modern Web Interface:** Clean, minimalistic monochrome design with responsive layout.

## Live Demo

The application is deployed on Hugging Face Spaces:
**https://huggingface.co/spaces/jhatchett/schrodinger-chat**

## How to Run Locally

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/johaun-hatchett/schrodingers-chat.git
cd schrodingers-chat
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your_key_here
```

### Running the Application

Start the Flask server:
```bash
python src/app.py
```

Then visit `http://localhost:5000` in your browser.

Alternatively, for Hugging Face Spaces deployment:
```bash
python app.py
```

## Project Structure

The project is organized into the following directories:

*   `src/`: Contains the Python source code for the application.
    *   `app.py`: Flask backend API and static file server.
    *   `game.py`: Core game logic including GameState and answer validation.
    *   `environments.py`: Defines the different physics problem environments.
    *   `llm.py`: Handles communication with the language model.
    *   `messages.py`: Defines the data structures for messages in the conversation.
    *   `analyze.py`: Contains the logic for analyzing the user's problem-solving approach and generating Likert scores.
    *   `database.py`: Handles user authentication and session storage.
    *   `cli.py`: Command-line interface (legacy).
*   `static/`: Contains frontend files.
    *   `index.html`: Main HTML file.
    *   `styles.css`: CSS styling.
    *   `app.js`: JavaScript for frontend logic.
    *   `assets/`: Static assets (icons, etc.).
*   `data/`: Contains data files.
    *   `rubric.json`: Defines the criteria and endpoints for each dimension of the problem-solving rubric.
*   `app.py`: Entry point for Hugging Face Spaces deployment.
*   `Dockerfile`: Docker configuration for deployment.
*   `requirements.txt`: Python dependencies.

## Problem-Solving Analysis

The core of Schrödinger's Chat is its ability to analyze a user's problem-solving style and provide personalized feedback. This is done using a four-dimensional framework, with each dimension represented on a Likert scale from -2 to +2:

*   **Conceptual Foundation:** Whether the user's approach is based on first principles or on memorized formulas.
*   **Strategic Insight:** Whether the user plans the entire solution path upfront or works step-by-step.
*   **Mathematical Execution:** Whether the user prefers to work with symbolic algebra or with concrete numbers.
*   **Reflective Intuition:** Whether the user checks the plausibility of their results or accepts them without reflection.

After completing a problem, users receive:
1. A summary of their overall approach (4-5 sentences)
2. A deep dive into each dimension with:
    - A visual Likert scale showing their score
    - A qualitative description (2-3 sentences) explaining how they demonstrated that dimension
3. Next steps for improvement
