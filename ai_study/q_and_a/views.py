# views.py
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import default_storage
import os
import google.generativeai as genai
import json
import logging
from typing import List, Dict, Union, Optional
from .models import Test, TestImage, TestQuestion
from app.models import User

logger = logging.getLogger(__name__)

class QuestionValidator:
    @staticmethod
    def validate_question_format(question: Dict) -> bool:
        """Validate individual question format"""
        try:
            # Check if all required fields exist
            required_fields = ['question', 'options', 'answer_number', 'correct_description']
            if not all(field in question for field in required_fields):
                return False
            
            # Validate question field
            if not isinstance(question['question'], str) or not question['question'].strip():
                return False
            
            # Validate options
            if not isinstance(question['options'], list) or len(question['options']) != 4:
                return False
            if not all(isinstance(opt, str) and opt.strip() for opt in question['options']):
                return False
            
            # Validate answer_number
            if not isinstance(question['answer_number'], int) or not (0 <= question['answer_number'] <= 3):
                return False
            
            # Validate correct_description
            if not isinstance(question['correct_description'], str) or not question['correct_description'].strip():
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating question format: {str(e)}")
            return False

    @staticmethod
    def parse_and_validate_questions(response_text: str) -> Optional[List[Dict]]:
        """Parse and validate Gemini response"""
        try:
            try:
                questions = json.loads(response_text)
                if not isinstance(questions, list):
                    questions = [questions]
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format: {str(e)}")
                return None
            
            # Validate each question
            for question in questions:
                if not QuestionValidator.validate_question_format(question):
                    logger.error(f"Invalid question format: {question}")
                    return None
            
            return questions
            
        except Exception as e:
            logger.error(f"Error parsing questions: {str(e)}")
            return None
class GeminiService:
    def __init__(self):
        self.api_key = "AIzaSyBPxLbQQ2Ecma393RsaOs4HJ1FSf358iN8"
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=self.api_key)
        self.model = self._setup_model()
    
    def _setup_model(self):
        """Initialize Gemini model"""
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }
        
        return genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config,
            system_instruction="""Generate multiple-choice questions based on provided images. 
            Return a JSON array of questions in this exact format:
            [
                {
                    "question": "Question text",
                    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                    "answer_number": 0-3,
                    "correct_description": "Explanation for correct answer"
                }
            ]"""
        )

    def _get_mime_type(self, image_file):
        """Determine the correct MIME type for an image file"""
        import imghdr
        
        # First try to detect the image type from the file content
        with open(image_file, 'rb') as f:
            img_type = imghdr.what(f)
        
        if img_type == 'jpeg':
            return 'image/jpeg'
        elif img_type == 'png':
            return 'image/png'
        else:
            # Fallback to extension-based detection
            ext = os.path.splitext(image_file)[1].lower()
            if ext in ['.jpg', '.jpeg']:
                return 'image/jpeg'
            elif ext == '.png':
                return 'image/png'
            else:
                raise ValueError(f"Unsupported image type for file: {image_file}")

    def generate_questions(self, images: List[InMemoryUploadedFile], focus_to: str, num_questions: int) -> str:
        """Generate questions using Gemini AI"""
        try:
            temp_paths = []
            uploaded_files = []
            
            for image in images:
                try:
                    # Save temporarily
                    temp_path = default_storage.save(f"temp_{image.name}", image)
                    full_path = default_storage.path(temp_path)
                    temp_paths.append((temp_path, full_path))
                    
                    # Get correct MIME type
                    mime_type = self._get_mime_type(full_path)
                    logger.info(f"Detected MIME type {mime_type} for file {image.name}")
                    
                    # Read file content
                    with open(full_path, 'rb') as f:
                        image_bytes = f.read()
                    
                    # Upload to Gemini with explicit MIME type and image bytes
                    file = genai.upload_file(full_path, mime_type=mime_type)
                    uploaded_files.append(file)
                    
                except Exception as e:
                    logger.error(f"Error processing image {image.name}: {str(e)}")
                    raise
            
            try:
                # Start chat session with processed images
                chat = self.model.start_chat(
                    history=[{
                        "role": "user",
                        "parts": [
                            *uploaded_files,
                            f"Generate {num_questions} questions about {focus_to}"
                        ]
                    }]
                )
                
                # Generate questions
                response = chat.send_message("Generate the questions now")
                return response.text
                
            finally:
                # Clean up temporary files
                for temp_path, full_path in temp_paths:
                    try:
                        default_storage.delete(temp_path)
                    except Exception as e:
                        logger.warning(f"Error deleting temporary file {temp_path}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            raise

def validate_image(image_file):
    """Validate uploaded image file"""
    if not isinstance(image_file, InMemoryUploadedFile):
        return False
    
    # Check file size (max 10MB)
    if image_file.size > 10 * 1024 * 1024:  # 10MB in bytes
        return False
    
    # Check file type
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
    if image_file.content_type not in allowed_types:
        return False
    
    return True

@api_view(['POST'])
def generate_test(request):
    """Generate a new test with AI-generated questions from images"""
    try:
        # Validate request parameters
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({
                'error': 'user_id is required in query parameters'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate request data
        title = request.data.get('title')
        description = request.data.get('description')
        focus_to = request.data.get('focus_to')
        num_questions = int(request.data.get('num_questions', 5))

        if not all([title, focus_to]):
            return Response({
                'error': 'title and focus_to are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate images
        images = request.FILES.getlist('images')
        if not images:
            return Response({
                'error': 'At least one image is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # for image in images:
        #     if not validate_image(image):
        #         return Response({
        #             'error': f'Invalid image file: {image.name}. Must be JPG/PNG under 10MB'
        #         }, status=status.HTTP_400_BAD_REQUEST)

        # Get user
        try:
            user = User.objects.get(uuid=user_id)
        except User.DoesNotExist:
            return Response({
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Create test
        test = Test.objects.create(
            user=user,
            title=title,
            description=description or '',
            focus_to=focus_to
        )

        # Save images
        saved_images = []
        try:
            for index, image_file in enumerate(images):
                test_image = TestImage.objects.create(
                    test=test,
                    image=image_file,
                    order=index
                )
                saved_images.append(test_image)
        except Exception as e:
            test.delete()
            return Response({
                'error': f'Error saving images: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Generate questions using Gemini
        try:
            # Initialize Gemini service
            gemini_service = GeminiService()
            
            # Generate questions
            response_text = gemini_service.generate_questions(
                images=images,
                focus_to=focus_to,
                num_questions=num_questions
            )
            
            # Validate generated questions
            validated_questions = QuestionValidator.parse_and_validate_questions(response_text)
            if validated_questions is None:
                test.delete()
                return Response({
                    'error': 'Invalid question format received from AI'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Save validated questions
            saved_questions = []
            for question_data in validated_questions:
                question = TestQuestion.objects.create(
                    test=test,
                    question=question_data['question'],
                    options=question_data['options'],
                    answer_number=question_data['answer_number']
                )
                saved_questions.append({
                    'question': question.question,
                    'options': question.options,
                    'answer_number': question.answer_number,
                    'correct_description': question_data['correct_description']
                })

        except Exception as e:
            test.delete()
            return Response({
                'error': f'Error generating/saving questions: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Prepare successful response
        response_data = {
            'test_id': str(test.id),
            'title': test.title,
            'description': test.description,
            'focus_to': test.focus_to,
            'created_at': test.created_at,
            'images': [
                {
                    'id': str(img.id),
                    'url': request.build_absolute_uri(img.image.url),
                    'order': img.order
                } for img in saved_images
            ],
            'questions': saved_questions
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error in generate_test: {str(e)}")
        return Response({
            'error': f'Server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)