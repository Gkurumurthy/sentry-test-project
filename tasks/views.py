from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Task, Category, Comment, Attachment
from .serializers import TaskSerializer, CategorySerializer, CommentSerializer, AttachmentSerializer
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    
    def get_queryset(self):
        queryset = Task.objects.all()
        
        # Filter by title/description
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        # Filter by category
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        # Filter by completion status
        completed = self.request.query_params.get('completed', None)
        if completed is not None:
            completed = completed.lower() == 'true'
            queryset = queryset.filter(completed=completed)
        
        # Filter by priority
        priority = self.request.query_params.get('priority', None)
        if priority:
            queryset = queryset.filter(priority=priority)
            
        # Filter by due date (upcoming tasks)
        upcoming = self.request.query_params.get('upcoming', None)
        if upcoming is not None:
            queryset = queryset.filter(due_date__gte=timezone.now())
            
        # Filter by overdue
        overdue = self.request.query_params.get('overdue', None)
        if overdue is not None:
            queryset = queryset.filter(due_date__lt=timezone.now(), completed=False)
            
        return queryset
    
    @action(detail=True, methods=['post'])
    def toggle_completed(self, request, pk=None):
        task = self.get_object()
        completed = task.toggle_completed()
        return Response({'completed': completed})
    
    @action(detail=True, methods=['get'])
    def days_until_due(self, request, pk=None):
        task = self.get_object()
        days = task.days_until_due()
        return Response({'days_until_due': days})
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        task = self.get_object()
        comment_count = task.comments.count()
        avg_comment_length = sum(c.get_word_count() for c in task.comments.all()) / max(comment_count, 1)
        
        return Response({
            'comment_count': comment_count,
            'attachment_count': task.attachments.count(),
            'avg_comment_length': avg_comment_length,
            'days_since_creation': (timezone.now() - task.created_at).days,
            'completion_time': (task.updated_at - task.created_at).days if task.completed else None
        })
        
    @action(detail=True, methods=['get'])
    def recent_comments(self, request, pk=None):
        """Get recent comments with a realistic IndexError bug"""
        task = self.get_object()
        
        # Get all comments ordered by creation date
        comments = task.comments.all().order_by('-created_at')
        
        # Realistic bug: Assuming there are at least 3 comments
        latest_comments = [
            comments[0].text,
            comments[1].text,
            comments[2].text
        ]
        
        return Response({
            'latest_comments': latest_comments
        })

    @action(detail=True, methods=['post'])
    def add_metadata(self, request, pk=None):
        """Add metadata to a task with realistic JSONDecodeError bug"""
        task = self.get_object()
        
        # Realistic bug: Not validating JSON structure
        import json
        metadata = json.loads(request.data.get('metadata', '{}'))
        
        # Store metadata in task description (simplified example)
        task.description += "\n\nMetadata: " + str(metadata)
        task.save()
        
        return Response({'status': 'metadata added'})

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        category = self.get_object()
        tasks = Task.objects.filter(category=category)
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        category = self.get_object()
        total_tasks = category.task_set.count()
        completed_tasks = category.task_set.filter(completed=True).count()
        
        # Division by zero potential
        completion_percentage = (completed_tasks / max(total_tasks, 1)) * 100
        
        # KeyError potential
        priority_breakdown = {
            'low': category.task_set.filter(priority=1).count(),
            'medium': category.task_set.filter(priority=2).count(),
            'high': category.task_set.filter(priority=3).count(),
            'critical': category.task_set.filter(priority=4).count()
        }
        
        return Response({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_percentage': completion_percentage,
            'priority_breakdown': priority_breakdown
        })
        
    @action(detail=True, methods=['get'])
    def task_breakdown(self, request, pk=None):
        """Get statistics about tasks by priority with a realistic KeyError bug"""
        category = self.get_object()
        
        # Count tasks by priority
        priority_counts = {}
        for task in category.task_set.all():
            priority_name = task.get_priority_display()
            if priority_name in priority_counts:
                priority_counts[priority_name] += 1
            else:
                priority_counts[priority_name] = 1
        
        # Realistic bug: Accessing dict keys without checking if they exist
        result = {
            'total': category.task_set.count(),
            'high_priority': priority_counts['High'],  # KeyError if no high priority tasks
            'medium_priority': priority_counts['Medium'],  # KeyError if no medium priority tasks
            'low_priority': priority_counts['Low']  # KeyError if no low priority tasks
        }
        
        return Response(result)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    
    def perform_create(self, serializer):
        # Potential for error if user doesn't exist
        serializer.save(author_id=self.request.query_params.get('author_id', 1))

class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer

# Legacy JSON views that might have bugs
def task_detail(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    
    # This will trigger our original bug for tasks with no due date
    days_left = task.days_until_due()
    
    return JsonResponse({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'completed': task.completed,
        'days_until_due': days_left
    })

def category_tasks(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    tasks = []
    
    for task in category.task_set.all():
        # This will also fail without timezone import
        is_overdue = task.is_overdue()
        
        tasks.append({
            'id': task.id,
            'title': task.title,
            'completed': task.completed,
            'is_overdue': is_overdue
        })
    
    return JsonResponse({
        'category': category.name,
        'tasks': tasks
    })

# Simple views for templates
def home(request):
    upcoming_tasks = Task.objects.filter(completed=False).order_by('due_date')[:5]
    categories = Category.objects.all()
    return render(request, 'home.html', {
        'upcoming_tasks': upcoming_tasks,
        'categories': categories,
    })

class TaskListView(ListView):
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Task.objects.all()
        
        # Apply filters based on GET parameters
        search = self.request.GET.get('search')
        category = self.request.GET.get('category')
        completed = self.request.GET.get('completed')
        
        if search:
            queryset = queryset.filter(title__icontains=search)
        if category:
            queryset = queryset.filter(category_id=category)
        if completed:
            completed_bool = completed.lower() == 'true'
            queryset = queryset.filter(completed=completed_bool)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

class TaskDetailView(DetailView):
    model = Task
    template_name = 'tasks/task_detail.html'
    context_object_name = 'task'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        
        # Original functionality
        days_until_due = task.days_until_due()
        context['days_until_due'] = days_until_due
        if days_until_due is not None and days_until_due < 0:
            context['days_overdue'] = abs(days_until_due)
        
        # Realistic bug: Not checking if category exists before accessing its property
        # This will cause AttributeError if task.category is None
        context['category_name'] = task.category.name
        
        # Pass through bug methods without try/except to allow errors to propagate to Sentry
        context['is_high_priority'] = task.is_high_priority()
        context['formatted_due_date'] = task.get_formatted_due_date()
        context['status_message'] = task.get_status_message()
        
        # Additional realistic bug: Add direct access to comments without checking if they exist
        context['latest_comment'] = task.comments.all()[0].text if task.comments.exists() else ''
        
        # Another realistic bug: Using format() incorrectly
        if days_until_due is not None:
            context['due_date_message'] = "Task is due in {} with {} priority".format(
                days_until_due, task.priority
            )
        
        return context

class TaskCreateView(CreateView):
    model = Task
    template_name = 'tasks/task_form.html'
    fields = ['title', 'description', 'category', 'priority', 'due_date']
    success_url = reverse_lazy('task_list')

class TaskUpdateView(UpdateView):
    model = Task
    template_name = 'tasks/task_form.html'
    fields = ['title', 'description', 'category', 'priority', 'due_date']
    success_url = reverse_lazy('task_list')

class TaskDeleteView(DeleteView):
    model = Task
    template_name = 'tasks/task_confirm_delete.html'
    success_url = reverse_lazy('task_list')

class CategoryListView(ListView):
    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'

def task_toggle_completed(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.completed = not task.completed
    task.save()
    return redirect('task_detail', pk=pk)

def category_detail(request, pk):
    """Display details of a specific category"""
    category = get_object_or_404(Category, pk=pk)
    tasks = Task.objects.filter(category=category)
    
    # Remove try/except to allow errors to propagate to Sentry
    average_priority = category.get_average_priority()  # May cause ZeroDivisionError
    completion_stats = category.get_completion_stats()  # Will cause KeyError
    
    return render(request, 'categories/category_detail.html', {
        'category': category,
        'tasks': tasks,
        'average_priority': average_priority,
        'completion_stats': completion_stats
    })