# app/serializers.py
from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('uuid', 'email', 'name', 'mobile', 'password', 'last_login', 'date_joined')
        extra_kwargs = {
            'uuid': {'read_only': True},
            'date_joined': {'read_only': True}
        }

# app/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import User
from .serializers import UserSerializer
import re

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def validate_email(self, email):
        # Basic email format validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return False
        return True

    @action(detail=False, methods=['post'])
    def check_email(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({
                "status": "error",
                "code": "EMAIL_REQUIRED",
                "message": "Email is required",
                "exists": False
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not self.validate_email(email):
            return Response({
                "status": "error",
                "code": "INVALID_EMAIL_FORMAT",
                "message": "Invalid email format",
                "exists": False
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            return Response({
                "status": "success",
                "code": "EMAIL_EXISTS",
                "message": "Email already exists",
                "exists": True,
                "data": {
                    "email": user.email,
                    "id": user.uuid,
                    "password": user.password
                }
            })
        except User.DoesNotExist:
            new_user = User.objects.create(
                email=email,
                password=""
            )
            return Response({
                "status": "success",
                "code": "EMAIL_AVAILABLE",
                "message": "Email is available",
                "exists": False,
                "data": {
                    "email": new_user.email,
                    "id": new_user.uuid
                }
            })

    @action(detail=False, methods=['post'])
    def register(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        name = request.data.get('name')
        mobile = request.data.get('mobile')

        # Validate required fields
        if not email or not password:
            return Response({
                "status": "error",
                "code": "MISSING_REQUIRED_FIELDS",
                "message": "Email and password are required",
                "errors": {
                    "email": "Required" if not email else None,
                    "password": "Required" if not password else None
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate email format
        if not self.validate_email(email):
            return Response({
                "status": "error",
                "code": "INVALID_EMAIL_FORMAT",
                "message": "Invalid email format",
                "errors": {
                    "email": "Invalid format"
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if email exists
        if User.objects.filter(email=email).exists():
            return Response({
                "status": "error",
                "code": "EMAIL_EXISTS",
                "message": "Email already registered",
                "errors": {
                    "email": "Already exists"
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create new user
        user = User.objects.create(
            email=email,
            password=password,  # Note: In production, use proper password hashing
            name=name or "",
            mobile=mobile or ""
        )

        return Response({
            "status": "success",
            "code": "REGISTRATION_SUCCESS",
            "message": "Registration successful",
            "data": UserSerializer(user).data
        })

    @action(detail=False, methods=['post'])
    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        print(email)
        print(password)
        
        # Validate required fields
        if not email or not password:
            return Response({
                "status": "error",
                "code": "MISSING_CREDENTIALS",
                "message": "Email and password are required",
                "errors": {
                    "email": "Required" if not email else None,
                    "password": "Required" if not password else None
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Check if user has a password set
            if not user.password:
                return Response({
                    "status": "error",
                    "code": "ACCOUNT_INCOMPLETE",
                    "message": "Account setup incomplete",
                    "errors": {
                        "password": "Password not set"
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check password
            if user.password != password:  # Note: In production, use proper password hashing
                return Response({
                    "status": "error",
                    "code": "INVALID_PASSWORD",
                    "message": "Incorrect password",
                    "errors": {
                        "password": "Incorrect password"
                    }
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Update last login
            user.last_login = timezone.now()
            user.save()
            
            return Response({
                "status": "success",
                "code": "LOGIN_SUCCESS",
                "message": "Login successful",
                "data": UserSerializer(user).data
            })
            
        except User.DoesNotExist:
            return Response({
                "status": "error",
                "code": "EMAIL_NOT_FOUND",
                "message": "No account found with this email",
                "errors": {
                    "email": "Account not found"
                }
            }, status=status.HTTP_404_NOT_FOUND)
        

    @action(detail=False, methods=['put'])
    def update_details(self, request):
        user_id = request.query_params.get('token')
        if not user_id:
            return Response({
                "status": "error",
                "code": "USER_ID_REQUIRED",
                "message": "User ID is required"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = User.objects.get(uuid=user_id)
            
            # Get all fields from request.data except 'id'
            update_fields = {k: v for k, v in request.data.items() if k != 'uuid'}
            
            if not update_fields:
                return Response({
                    "status": "error",
                    "code": "NO_FIELDS_TO_UPDATE",
                    "message": "No fields provided for update"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate and update each field
            for field, value in update_fields.items():
                if field not in ['password', 'name', 'mobile']:
                    continue
                    
                if field == 'password':
                    if len(value) < 6:
                        return Response({
                            "status": "error",
                            "code": "INVALID_PASSWORD",
                            "message": "Password must be at least 6 characters long"
                        }, status=status.HTTP_400_BAD_REQUEST)
                    setattr(user, field, value)  # In real app, use set_password()
                    
                elif field == 'name':
                    if value and len(str(value).strip()) > 0:
                        setattr(user, field, str(value).strip())
                        
                elif field == 'mobile':
                    setattr(user, field, value)
            
            user.save()
            
            # Prepare response data with only the updated fields
            response_data = {
                "id": user.id,
                "email": user.email  # Always include email for reference
            }
            for field in update_fields.keys():
                if field != 'password':  # Don't return password in response
                    response_data[field] = getattr(user, field)
            
            return Response({
                "status": "success",
                "code": "USER_UPDATED",
                "message": "User details updated successfully",
                "data": response_data
            })
            
        except User.DoesNotExist:
            return Response({
                "status": "error",
                "code": "USER_NOT_FOUND",
                "message": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)
        



        
    # Add this method to your existing UserViewSet class
    @action(detail=False, methods=['get'])
    def get_user_details(self, request):
        email = request.query_params.get('email')
        
        # Check if email is provided
        if not email:
            return Response({
                "status": "error",
                "code": "EMAIL_REQUIRED",
                "message": "Email is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate email format
        if not self.validate_email(email):
            return Response({
                "status": "error",
                "code": "INVALID_EMAIL_FORMAT",
                "message": "Invalid email format"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            print(user)
            return Response({
                "status": "success",
                "code": "USER_FOUND",
                "message": "User details retrieved successfully",
                "data": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "mobile": user.mobile,
                    "last_login": user.last_login,
                    "date_joined": user.date_joined
                }
            })
        except User.DoesNotExist:
            return Response({
                "status": "error",
                "code": "USER_NOT_FOUND",
                "message": "No user found with this email"
            }, status=status.HTTP_404_NOT_FOUND)