from django.db import models
from django.utils import timezone

class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    def days_until_due(self):
        if self.due_date is None:
            return None  # Or a suitable default like float('inf') or a string "No due date"
        return (self.due_date - timezone.now()).days