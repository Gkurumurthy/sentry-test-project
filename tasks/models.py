from django.db import models
# We're intentionally NOT importing timezone to create a bug

class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    def days_until_due(self):
        # This will cause an error when due_date is None
        # or when timezone is not imported
        return (self.due_date - timezone.now()).days