from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from .models import Task
from .serializers import TaskSerializer
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from datetime import datetime
from django.db.models import Count, Sum


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def task_stats(request):
    # Extract query parameters for filtering
    date = request.query_params.get('date', None)
    employee = request.query_params.get('employee', None)
    tags = request.query_params.get('tags', None)
    status_filter = request.query_params.get('status', None)

    # Build the filter dictionary based on the query parameters
    filters = {}
    if date:
        try:
            filters['date'] = datetime.strptime(date, '%Y-%m-%d').date()  # Convert to date if needed
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
    if employee:
        filters['employee'] = employee
    if tags:
        filters['tags'] = tags
    if status_filter:
        filters['status'] = status_filter

    # Assuming you have a Task model or a similar structure
    try:
        tasks = Task.objects.filter(**filters)
        
        # Calculate total hours, most-used tags, and pending approvals
        total_hours = tasks.aggregate(Sum('hours_spent'))['hours_spent__sum'] or 0
        most_used_tags = tasks.values('tags').annotate(count=Count('tags')).order_by('-count')[:5]
        pending_approvals = tasks.filter(status='pending').count()

        # Return the stats as JSON
        return Response({
            "total_hours": total_hours,
            "most_used_tags": most_used_tags,
            "pending_approvals": pending_approvals
        })

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TaskCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = TaskSerializer(data=request.data)

        try:
            if serializer.is_valid():
                serializer.save(employee=request.user)
                return Response({
                    "detail": "Task created successfully.",
                    "task": serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "detail": "Validation failed. Please check the provided data.",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({
                "detail": str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

class TaskListView(ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Returns tasks based on the user role:
        - Employees see only their own tasks
        - Managers see all tasks
        """
        user = self.request.user

        if user.role == 'employee':
            queryset = Task.objects.filter(employee=user)
        elif user.role == 'manager':
            queryset = Task.objects.all()
        else:
            queryset = Task.objects.none()  # Or you could raise PermissionDenied()

        # Optional filters from query params
        date_filter = self.request.query_params.get('date')
        if date_filter:
            queryset = queryset.filter(date=date_filter)

        employee_filter = self.request.query_params.get('employee')
        if employee_filter:
            queryset = queryset.filter(employee=employee_filter)

        tags_filter = self.request.query_params.get('tags')
        if tags_filter:
            queryset = queryset.filter(tags__icontains=tags_filter)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "detail": "Tasks fetched successfully.",
            "tasks": serializer.data
        })

class TaskUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            task = Task.objects.get(pk=pk, employee=request.user)
        except Task.DoesNotExist:
            return Response({
                "detail": "Task not found or you're not authorized to edit this task."
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if task status is 'Pending' or 'Rejected' before allowing edits
        if task.status == 'approved':
            return Response({
                "detail": "You cannot edit an approved task."
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            # If task was rejected, reset status to pending
            if task.status == 'rejected':
                serializer.save(status='pending')
            else:
                serializer.save()

            return Response({
                "detail": "Task updated successfully.",
                "task": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "detail": "Invalid data. Task could not be updated.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



class TaskDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        pk = kwargs.get('pk')  # Task ID from the URL

        try:
            task = Task.objects.get(pk=pk, employee=request.user)  # Ensure the task belongs to the logged-in user
        except Task.DoesNotExist:
            return Response({
                "detail": "Task not found or you're not authorized to delete this task."
            }, status=status.HTTP_404_NOT_FOUND)

        # Delete the task
        task.delete()
        return Response({
            "detail": "Task deleted successfully."
        }, status=status.HTTP_204_NO_CONTENT)
    

class TaskActionView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({
                "detail": "Task not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # Ensure the user is a manager
        if request.user.role != 'manager':
            return Response({
                "detail": "You are not authorized to approve/reject tasks."
            }, status=status.HTTP_403_FORBIDDEN)

        # Check if task is already approved or rejected
        if task.status in ['approved', 'rejected']:
            return Response({
                "detail": "This task cannot be changed. It has already been approved or rejected."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Determine the action (approve or reject)
        action = request.data.get('action')

        # Validate the action
        if action not in ['approve', 'reject']:
            return Response({
                "detail": "Invalid action. Must be 'approve' or 'reject'."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Optional comment for rejection
        comment = request.data.get('comment', '')  # Optional comment

        if action == 'approve':
            task.status = 'approved'
        elif action == 'reject':
            task.status = 'rejected'
            task.manager_comment = comment  # Add comment if needed

        # Save the task after updating
        task.save()

        return Response({
            "detail": f"Task {action}d successfully.",
            "task": TaskSerializer(task).data
        }, status=status.HTTP_200_OK)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return Response({
                "detail": "Task not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # Serialize the task
        serializer = TaskSerializer(task)
        return Response({
            "task": serializer.data
        }, status=status.HTTP_200_OK)