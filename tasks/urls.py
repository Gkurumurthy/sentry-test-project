from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('tasks/<int:pk>/update/', views.TaskUpdateView.as_view(), name='task_update'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('tasks/<int:pk>/toggle-completed/', views.task_toggle_completed, name='task_toggle_completed'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    ]


