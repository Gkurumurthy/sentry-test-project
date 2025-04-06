from rest_framework import serializers
from .models import Task, Category, Comment, Attachment
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class CategorySerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()
    completed_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'color', 'task_count', 'completed_percentage']
    
    def get_task_count(self, obj):
        return obj.get_task_count()
    
    def get_completed_percentage(self, obj):
        return obj.get_completed_percentage()

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    word_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'task', 'author', 'text', 'created_at', 'word_count']
    
    def get_word_count(self, obj):
        return obj.get_word_count()

class AttachmentSerializer(serializers.ModelSerializer):
    file_size = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()
    
    class Meta:
        model = Attachment
        fields = ['id', 'task', 'file', 'uploaded_at', 'description', 'file_size', 'file_extension']
    
    def get_file_size(self, obj):
        try:
            return obj.file_size()
        except Exception:
            return None
    
    def get_file_extension(self, obj):
        try:
            return obj.file_extension()
        except Exception:
            return None

class TaskSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    days_until_due = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'completed', 'due_date', 
            'created_at', 'updated_at', 'priority', 'category', 
            'assigned_to', 'days_until_due', 'is_overdue',
            'comments', 'attachments'
        ]
    
    def get_days_until_due(self, obj):
        try:
            return obj.days_until_due()
        except Exception:
            return None
    
    def get_is_overdue(self, obj):
        try:
            return obj.is_overdue()
        except Exception:
            return None