"""
Standardized API response formatting and mixins for ViewSets.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message='Success', status_code=status.HTTP_200_OK):
    """
    Return a standardized success response.
    
    Args:
        data: The response data
        message: Success message
        status_code: HTTP status code
        
    Returns:
        Response object with standardized format
    """
    return Response(
        {
            'success': True,
            'data': data,
            'message': message,
        },
        status=status_code
    )


def error_response(errors=None, message='Error occurred', status_code=status.HTTP_400_BAD_REQUEST):
    """
    Return a standardized error response.
    
    Args:
        errors: Dictionary of errors
        message: Error message
        status_code: HTTP status code
        
    Returns:
        Response object with standardized format
    """
    return Response(
        {
            'success': False,
            'errors': errors or {},
            'message': message,
        },
        status=status_code
    )


class StandardResponseMixin:
    """
    Mixin for DRF ViewSets to wrap responses in standard format.
    
    Wraps list(), create(), retrieve(), update(), partial_update() responses
    in the standardized format:
    {
        "success": true,
        "data": {...},
        "message": "Success message"
    }
    
    Usage:
        class MyViewSet(StandardResponseMixin, viewsets.ModelViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """
    
    def list(self, request, *args, **kwargs):
        """Override list to wrap response."""
        response = super().list(request, *args, **kwargs)
        
        # Get pagination info if present
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            # Paginated response
            paginated_data = {
                'count': data.get('count', 0),
                'next': data.get('next'),
                'previous': data.get('previous'),
                'results': data.get('results', []),
            }
            return success_response(
                data=paginated_data,
                message='Muvaffaqiyatli olingan',
                status_code=status.HTTP_200_OK
            )
        else:
            # Non-paginated list
            return success_response(
                data=data,
                message='Muvaffaqiyatli olingan',
                status_code=status.HTTP_200_OK
            )
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to wrap response."""
        response = super().retrieve(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message='Muvaffaqiyatli olingan',
            status_code=status.HTTP_200_OK
        )
    
    def create(self, request, *args, **kwargs):
        """Override create to wrap response."""
        response = super().create(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message='Muvaffaqiyatli yaratildi',
            status_code=response.status_code
        )
    
    def update(self, request, *args, **kwargs):
        """Override update to wrap response."""
        response = super().update(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message='Muvaffaqiyatli yangilandi',
            status_code=status.HTTP_200_OK
        )
    
    def partial_update(self, request, *args, **kwargs):
        """Override partial_update to wrap response."""
        response = super().partial_update(request, *args, **kwargs)
        return success_response(
            data=response.data,
            message='Muvaffaqiyatli yangilandi',
            status_code=status.HTTP_200_OK
        )
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to wrap response."""
        response = super().destroy(request, *args, **kwargs)
        return success_response(
            data=None,
            message='Muvaffaqiyatli o\'chirildi',
            status_code=status.HTTP_204_NO_CONTENT
        )


class ActionResponseMixin:
    """
    Mixin to wrap custom action responses in standard format.
    
    Usage in custom action:
        @action(detail=False, methods=['post'])
        def my_action(self, request):
            # Do something
            return self.action_success(data={'result': 'value'})
    """
    
    def action_success(self, data=None, message='Muvaffaqiyatli', status_code=status.HTTP_200_OK):
        """Return success response for custom action."""
        return success_response(data=data, message=message, status_code=status_code)
    
    def action_error(self, errors=None, message='Xato yuz berdi', status_code=status.HTTP_400_BAD_REQUEST):
        """Return error response for custom action."""
        return error_response(errors=errors, message=message, status_code=status_code)


class CombinedResponseMixin(StandardResponseMixin, ActionResponseMixin):
    """
    Combined mixin that includes both standard and action response handling.
    
    This is the recommended mixin to use for ViewSets that have both
    standard CRUD operations and custom actions.
    """
    pass

