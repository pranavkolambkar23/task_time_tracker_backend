from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'employee', 'title', 'description', 'hours_spent', 'tags', 'date', 'status', 'manager_comment']
        read_only_fields = ['employee', 'status']  # Prevents modification of these fields from API

class TaskStatsSerializer(serializers.Serializer):
    total_hours = serializers.FloatField()
    most_used_tags = serializers.ListField(child=serializers.DictField())
    pending_approvals = serializers.IntegerField()
