# views.py
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET'])
def app_info(request):
    app_data = {
        "version": "2.1.0",
        "lastUpdated": "2025-01-12",
        "newFeatures": [
            "Dark mode support across all screens",
            "Enhanced performance in offline mode",
            "New dashboard widgets",
            "Bug fixes and stability improvements",
            "Integration with cloud storage services"
        ],
        "status": "stable",
        'url': 'https://www.google.com',
        "minOSVersion": {
            "ios": "13.0",
            "android": "8.0"
        }
    }
    
    return Response(app_data, status=status.HTTP_200_OK)
