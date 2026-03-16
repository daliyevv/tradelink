"""
Custom exception handler for DRF.

This handler returns all errors in a standardized format:
{
    "success": false,
    "message": "Error message",
    "errors": {
        "field_name": ["error message 1", "error message 2"]
    }
}
"""
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns standardized error responses.
    
    Args:
        exc: The exception instance
        context: A dictionary containing the request, view, and other context
        
    Returns:
        Response with standardized error format or None if unhandled
    """
    # Call DRF's default exception handler first to get response
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # response.data is the default DRF dict containing 'detail' or field errors
        error_data = response.data
        
        # Determine the error message
        if isinstance(error_data, dict):
            # For validation errors (field errors)
            if 'detail' in error_data:
                message = str(error_data['detail'])
                errors = {}
            else:
                # Field-level validation errors
                message = 'Validatsiya xatosi'
                errors = error_data
        elif isinstance(error_data, list):
            # Detail is a list
            message = str(error_data[0]) if error_data else 'Xato yuz berdi'
            errors = {}
        else:
            # Detail is a string
            message = str(error_data)
            errors = {}
        
        # Handle authentication/permission errors
        if response.status_code in (401, 403):
            if response.status_code == 401:
                message = 'Autentifikatsiya talab qilinadi'
            else:
                message = 'Bu amalga ruxsat yo\'q'
        
        # Handle not found errors
        if response.status_code == 404:
            message = 'Resurs topilmadi'
        
        # Handle rate limiting
        if response.status_code == 429:
            message = 'Juda ko\'p so\'rovlar. Iltimos, biroz kuting'
        
        # Construct standardized response
        response.data = {
            'success': False,
            'message': message,
            'errors': errors,
        }
        
        return response
    
    # If DRF doesn't handle it, return None to let Django handle it
    return None


def get_error_message(status_code):
    """
    Get a user-friendly error message based on HTTP status code.
    
    Args:
        status_code: The HTTP status code
        
    Returns:
        A user-friendly error message in Uzbek
    """
    error_messages = {
        400: 'Noto\'g\'ri so\'rov',
        401: 'Autentifikatsiya talab qilinadi',
        403: 'Bu amalga ruxsat yo\'q',
        404: 'Resurs topilmadi',
        405: 'Bu usul qo\'llab-quvvatlanmaydi',
        409: 'Konflikt yuz berdi',
        429: 'Juda ko\'p so\'rovlar',
        500: 'Server xatosi yuz berdi',
        502: 'Noto\'g\'ri shlyuz',
        503: 'Servis vaqtincha ishlamaydi',
    }
    
    return error_messages.get(status_code, 'Xato yuz berdi')
