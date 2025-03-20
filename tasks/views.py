from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Task

def task_detail(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    
    # This will trigger the bug for tasks with no due date
    days_left = task.days_until_due()
    
    return JsonResponse({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'completed': task.completed,
        'days_until_due': days_left
    })