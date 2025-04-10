from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=20, default="blue")
    
    def __str__(self):
        return self.name
    
    def get_task_count(self):
        return self.task_set.count()
    
    def get_completed_percentage(self):
        total = self.task_set.count()
        if total == 0:
            return 0
        completed = self.task_set.filter(completed=True).count()
        return (completed / total) * 100
    
    def get_average_priority(self):
        """Calculate average priority with a ZeroDivisionError bug"""
        tasks = self.task_set.all()
        priority_sum = sum(task.priority for task in tasks)
        # Will cause ZeroDivisionError if category has no tasks
        return priority_sum / tasks.count()  

    def get_completion_stats(self):
        """Get completion statistics with KeyError bug"""
        stats = {
            'total': self.task_set.count(),
            'completed': self.task_set.filter(completed=True).count(),
        }
        # KeyError: 'completion_percentage' - this key doesn't exist
        return stats['completion_percentage']

class Task(models.Model):
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical')
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    def days_until_due(self):
        if self.due_date:
            return (self.due_date - timezone.now()).days
        return None
    
    def is_overdue(self):
        if not self.due_date or self.completed:
            return False
        return self.due_date < timezone.now()
    
    def toggle_completed(self):
        self.completed = not self.completed
        self.save()
        return self.completed
    
    def is_high_priority(self):
        """Check if task is high priority - has AttributeError bug"""
        # Misspelled attribute name corrected
        return self.priority >= 3

    def get_formatted_due_date(self):
        """Format the due date with a TypeError bug"""
        if self.due_date:
            days = self.days_until_due()
            # TypeError: can only concatenate str (not "int") to str
            return "Due in " + days + " days"
        return "No due date"

    def get_status_message(self):
        """Get a status message with an UnboundLocalError bug"""
        if self.completed:
            message = "This task has been completed"
        elif self.due_date and self.due_date < timezone.now():
            message = "This task is overdue"
        elif self.due_date and self.due_date > timezone.now():
            message = "This task is upcoming"
        # Missing else clause when task has no due date and is not completed
        return message  # UnboundLocalError if none of the conditions are met
    
    def get_priority_class(self):
        """Get CSS class for priority with realistic UnboundLocalError bug"""
        if self.priority == 4:
            priority_class = 'danger'
        elif self.priority == 3:
            priority_class = 'warning'
        elif self.priority == 2:
            priority_class = 'info'
        # Realistic bug: Missing the else branch for priority == 1
        return priority_class  # UnboundLocalError if priority is 1

    def parse_json_description(self):
        """Tries to parse description as JSON - may cause JSONDecodeError"""
        import json
        return json.loads(self.description)

class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.task.title}"
    
    def get_word_count(self):
        # This will cause an AttributeError if text is None
        return len(self.text.split())

class Attachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"Attachment for {self.task.title}"
    
    def file_size(self):
        # This will raise an exception if the file doesn't exist
        return self.file.size
    
    def file_extension(self):
        # This will cause an IndexError if there's no '.' in the filename
        return self.file.name.split('.')[-1]