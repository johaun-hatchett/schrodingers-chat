"""Flask backend API for Schrödinger's Chat."""
import json
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

from game import GameState, get_llm_response, check_answer
from environments import EnvironmentFactory, ProblemType
from messages import HumanMessage, AIMessage
from llm import LLMException
from analyze import (
    summarize_problem_solving,
    get_tutor_insights,
    generate_likert_scores,
)
from database import (
    initialize_database, save_transcript, get_user_sessions, 
    get_all_sessions_for_admin, get_transcript_by_id,
    authenticate_user, create_user
)

# Determine static folder path (works for both local and Docker)
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
if not os.path.exists(static_path):
    static_path = os.path.join(os.path.dirname(__file__), '..', 'static')

app = Flask(__name__, static_folder=static_path, static_url_path='')
CORS(app)

# Initialize database on startup
initialize_database()

# In-memory session storage (in production, use Redis or similar)
sessions = {}


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('../static', 'index.html')


@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login."""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    user = authenticate_user(username, password)
    if user:
        # Create session token
        session_token = str(uuid.uuid4())
        sessions[session_token] = {
            'user_id': user['id'],
            'username': user['username'],
            'is_admin': bool(user['is_admin']),
            'game_state': None,
            'game_started': False,
            'session_id': None,
        }
        return jsonify({
            'success': True,
            'token': session_token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'is_admin': bool(user['is_admin'])
            }
        })
    else:
        return jsonify({'error': 'Invalid username or password'}), 401


@app.route('/api/signup', methods=['POST'])
def signup():
    """Handle user signup."""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400
    
    user_id = create_user(username, password, is_admin=False)
    if user_id:
        return jsonify({'success': True, 'message': 'Account created successfully'})
    else:
        return jsonify({'error': 'Username already exists'}), 400


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get user's past sessions."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token not in sessions:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = sessions[token]['user_id']
    user_sessions = get_user_sessions(user_id)
    return jsonify({'sessions': user_sessions})


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session transcript."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token not in sessions:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = sessions[token]['user_id']
    session_data = get_transcript_by_id(session_id, user_id=user_id)
    
    if session_data:
        return jsonify({
            'session': {
                'id': session_data['id'],
                'session_id': session_data['session_id'],
                'timestamp': session_data['timestamp'],
                'problem_type': session_data['problem_type'],
                'summary': session_data.get('summary'),
                'scores': json.loads(session_data.get('scores', '[]')) if session_data.get('scores') else None,
                'transcript': session_data['transcript_obj'].serialize()
            }
        })
    else:
        return jsonify({'error': 'Session not found'}), 404


@app.route('/api/game/start', methods=['POST'])
def start_game():
    """Start a new game session."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token not in sessions:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    problem_type_str = data.get('problem_type', 'block_on_incline')
    
    try:
        problem_type = ProblemType(problem_type_str)
    except ValueError:
        return jsonify({'error': 'Invalid problem type'}), 400
    
    environment = EnvironmentFactory.create(problem_type)
    game_state = GameState(environment)
    session_id = str(uuid.uuid4())
    
    sessions[token]['game_state'] = game_state
    sessions[token]['game_started'] = True
    sessions[token]['session_id'] = session_id
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'problem': game_state.problem,
        'problem_type': problem_type_str
    })


@app.route('/api/game/message', methods=['POST'])
def send_message():
    """Send a message in the game."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token not in sessions:
        return jsonify({'error': 'Unauthorized'}), 401
    
    session = sessions[token]
    if not session['game_started'] or not session['game_state']:
        return jsonify({'error': 'Game not started'}), 400
    
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    game_state = session['game_state']
    human_msg = HumanMessage(user_message)
    game_state.add_to_transcript(human_msg)
    
    # Check if this is an answer attempt
    answer_check = check_answer(game_state, user_message)
    
    response_messages = []
    game_completed = False
    
    if answer_check is not None:
        is_correct, feedback = answer_check
        if is_correct:
            game_completed = True
            response_messages.append({
                'role': 'assistant',
                'content': f"🎉 {feedback}",
                'type': 'success'
            })
        else:
            response_messages.append({
                'role': 'assistant',
                'content': feedback,
                'type': 'warning'
            })
    
    # Get LLM response (unless game is completed and we got congratulations)
    if not (game_completed and answer_check and answer_check[0]):
        try:
            model = data.get('model', 'gpt-4o-mini')
            use_fast_model = data.get('use_fast_model', False)
            model_to_use = 'gpt-4o' if use_fast_model else model
            
            ai_message = get_llm_response(human_msg, game_state, model=model_to_use)
            game_state.add_to_transcript(ai_message)
            
            content = ai_message.content
            if content and not (game_completed and "Congratulations" in content):
                response_messages.append({
                    'role': 'assistant',
                    'content': content,
                    'type': 'info'
                })
        except LLMException as e:
            response_messages.append({
                'role': 'assistant',
                'content': f"Error communicating with the AI: {e}",
                'type': 'error'
            })
    
    if game_completed:
        session['game_started'] = False
    
    return jsonify({
        'messages': response_messages,
        'game_completed': game_completed
    })


@app.route('/api/game/summary', methods=['POST'])
def generate_summary():
    """Generate problem-solving summary after game completion."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token not in sessions:
        return jsonify({'error': 'Unauthorized'}), 401
    
    session = sessions[token]
    if not session['game_state']:
        return jsonify({'error': 'No game state found'}), 400
    
    game_state = session['game_state']
    transcript = game_state.get_transcript()
    
    try:
        model = request.json.get('model', 'gpt-4o-mini')
        
        # Generate scores once
        scores = generate_likert_scores(transcript, model=model)
        
        # Generate summary with those scores
        summary = summarize_problem_solving(transcript, model=model, scores=scores)
        
        # Save to database
        user_id = session['user_id']
        session_id = session['session_id']
        problem_type = request.json.get('problem_type', 'block_on_incline')
        
        save_transcript(
            user_id,
            session_id,
            problem_type,
            transcript,
            summary=summary,
            scores=scores
        )
        
        return jsonify({
            'summary': summary,
            'scores': scores
        })
    except LLMException as e:
        return jsonify({'error': f'Error generating summary: {e}'}), 500


@app.route('/api/admin/sessions', methods=['GET'])
def admin_sessions():
    """Get all sessions for admin view."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token not in sessions or not sessions[token]['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    all_sessions = get_all_sessions_for_admin()
    return jsonify({'sessions': all_sessions})


@app.route('/api/admin/sessions/<int:session_id>', methods=['GET'])
def admin_get_session(session_id):
    """Get a specific session for admin view."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token not in sessions or not sessions[token]['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    session_data = get_transcript_by_id(session_id)
    if session_data:
        return jsonify({
            'session': {
                'id': session_data['id'],
                'session_id': session_data['session_id'],
                'timestamp': session_data['timestamp'],
                'problem_type': session_data['problem_type'],
                'username': session_data.get('username'),
                'summary': session_data.get('summary'),
                'scores': json.loads(session_data.get('scores', '[]')) if session_data.get('scores') else None,
                'transcript': session_data['transcript_obj'].serialize()
            }
        })
    else:
        return jsonify({'error': 'Session not found'}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(host='0.0.0.0', port=port, debug=False)

