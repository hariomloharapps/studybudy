# gemini_utils.py
import os
import json
import google.generativeai as genai
from typing import List, Dict, Union
import logging

logger = logging.getLogger(__name__)

class GeminiQuestionGenerator:
    def __init__(self):
        # Configure Gemini with API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        
        # Initialize model configuration
        self.generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=self.generation_config,
            system_instruction="""You are a question generator bot. Generate multiple-choice questions based on 
            provided images. Each question should have:
            - A clear question text
            - Four options
            - The correct answer index (0-3)
            - An explanation for the correct answer
            
            Format each question as:
            {
                'question': 'Question text',
                'options': ['Option 1', 'Option 2', 'Option 3', 'Option 4'],
                'answer_number': correct_index,
                'correct_description': 'Explanation for the correct answer'
            }"""
        )

    def upload_images(self, image_paths: List[str], mime_types: List[str]) -> List:
        """Upload images to Gemini"""
        uploaded_files = []
        for path, mime_type in zip(image_paths, mime_types):
            try:
                file = genai.upload_file(path, mime_type=mime_type)
                uploaded_files.append(file)
                logger.info(f"Successfully uploaded image: {path}")
            except Exception as e:
                logger.error(f"Error uploading image {path}: {str(e)}")
                raise
        return uploaded_files

    def generate_questions(
        self, 
        image_paths: List[str], 
        mime_types: List[str],
        num_questions: int = 5,
        focus_on: str = ""
    ) -> List[Dict]:
        """
        Generate questions based on provided images
        
        Args:
            image_paths: List of paths to image files
            mime_types: List of mime types for the images
            num_questions: Number of questions to generate
            focus_on: Topic to focus questions on
            
        Returns:
            List of question dictionaries
        """
        try:
            # Upload images
            uploaded_files = self.upload_images(image_paths, mime_types)
            
            # Create chat session
            chat_session = self.model.start_chat(
                history=[
                    {
                        "role": "user",
                        "parts": [
                            *uploaded_files,
                            f"Generate {num_questions} questions" + 
                            (f" focusing on {focus_on}" if focus_on else "")
                        ],
                    },
                ]
            )
            
            # Generate questions
            response = chat_session.send_message("Generate the questions now")
            
            # Parse and validate response
            try:
                # The response might be a string representation of a list of dictionaries
                questions = json.loads(response.text)
                if not isinstance(questions, list):
                    questions = [questions]  # Handle single question case
                    
                # Validate each question has required fields
                for q in questions:
                    assert 'question' in q
                    assert 'options' in q and len(q['options']) == 4
                    assert 'answer_number' in q and 0 <= q['answer_number'] <= 3
                    assert 'correct_description' in q
                    
                return questions
                
            except (json.JSONDecodeError, AssertionError) as e:
                logger.error(f"Error parsing Gemini response: {str(e)}")
                logger.error(f"Raw response: {response.text}")
                raise ValueError("Invalid response format from Gemini")
                
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            raise

# Example usage:
"""
generator = GeminiQuestionGenerator()

# Example image paths and mime types
image_paths = [
    "path/to/image1.jpg",
    "path/to/image2.png"
]
mime_types = [
    "image/jpeg",
    "image/png"
]

try:
    questions = generator.generate_questions(
        image_paths=image_paths,
        mime_types=mime_types,
        num_questions=6,
        focus_on="Python Programming"
    )
    
    for i, q in enumerate(questions, 1):
        print(f"\nQuestion {i}:")
        print(f"Q: {q['question']}")
        print("Options:")
        for j, opt in enumerate(q['options']):
            print(f"{j+1}. {opt}")
        print(f"Correct Answer: {q['answer_number'] + 1}")
        print(f"Explanation: {q['correct_description']}")
        
except Exception as e:
    print(f"Error: {str(e)}")
"""