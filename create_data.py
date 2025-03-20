import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bugtracker.settings')
django.setup()

from tasks.models import Task

# Create a task without a due date (this will cause an error)
task = Task.objects.create(
    title="Fix urgent bug",
    description="This task has no due date and will cause an error",
    completed=False,
    due_date=None
)

print(f"Created task: {task.title} (ID: {task.id})")