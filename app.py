from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

def generate_course_content(topic):
    """Generate course structure, lessons, and quizzes using Gemini"""
    model = genai.GenerativeModel("gemini-pro-latest")
   
    prompt = f"""Create a comprehensive mini-course about "{topic}".
    
    Return ONLY valid JSON (no markdown, no code blocks) with this exact structure:
    {{
        "course_title": "Course Title",
        "course_description": "Brief description",
        "duration": "Estimated duration",
        "lessons": [
            {{
                "lesson_number": 1,
                "title": "Lesson Title",
                "content": "Detailed lesson content (2-3 paragraphs)",
                "key_points": ["point1", "point2", "point3"],
                "youtube_search_query": "Search query for finding relevant YouTube videos"
            }}
        ],
        "quiz": {{
            "title": "Course Quiz",
            "questions": [
                {{
                    "question": "Question text?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": 0,
                    "explanation": "Why this is correct"
                }}
            ]
        }},
        "learning_objectives": ["objective1", "objective2", "objective3"],
        "resources": ["Resource 1", "Resource 2"]
    }}
    
    Create 3-4 lessons. Make content educational and engaging."""
    
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Clean up response if wrapped in markdown code blocks
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        course_data = json.loads(content.strip())
        return course_data
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response was: {content}")
        return None

def get_youtube_video_id(search_query):
    """Generate a YouTube embed URL based on search query"""
    # In production, use YouTube API for actual search
    # For demo, create a search-based embed
    search_query_encoded = search_query.replace(" ", "+")
    return f"https://www.youtube.com/embed/results?search_query={search_query_encoded}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-course', methods=['POST'])
def generate_course():
    data = request.json
    topic = data.get('topic', '').strip()
    
    if not topic:
        return jsonify({'error': 'Topic is required'}), 400
    
    if not GEMINI_API_KEY:
        return jsonify({'error': 'GEMINI_API_KEY not configured'}), 500
    
    try:
        course_data = generate_course_content(topic)
        
        if not course_data:
            return jsonify({'error': 'Failed to generate course content'}), 500
        
        # Add video URLs to lessons
        for lesson in course_data.get('lessons', []):
            query = lesson.get('youtube_search_query', lesson.get('title', ''))
            lesson['video_url'] = get_youtube_video_id(query)
        
        return jsonify({
            'success': True,
            'course': course_data,
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-quiz', methods=['POST'])
def submit_quiz():
    data = request.json
    answers = data.get('answers', [])
    quiz_data = data.get('quiz', {})
    
    questions = quiz_data.get('questions', [])
    score = 0
    results = []
    
    for i, answer in enumerate(answers):
        if i < len(questions):
            question = questions[i]
            is_correct = answer == question.get('correct_answer')
            if is_correct:
                score += 1
            results.append({
                'question': question.get('question'),
                'user_answer': answer,
                'correct_answer': question.get('correct_answer'),
                'is_correct': is_correct,
                'explanation': question.get('explanation')
            })
    
    percentage = (score / len(questions) * 100) if questions else 0
    
    return jsonify({
        'success': True,
        'score': score,
        'total': len(questions),
        'percentage': percentage,
        'results': results,
        'passed': percentage >= 70
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)