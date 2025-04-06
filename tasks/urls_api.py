from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tasks', views.TaskViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'comments', views.CommentViewSet)
router.register(r'attachments', views.AttachmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Legacy endpoints (non-DRF) with potential bugs
    path('task/<int:task_id>/', views.task_detail, name='api_task_detail'),
    path('category/<int:category_id>/tasks/', views.category_tasks, name='api_category_tasks'),
] 