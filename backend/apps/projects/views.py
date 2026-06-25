"""
Project views.

GET    /api/v1/projects/                → public list (open projects)
POST   /api/v1/projects/               → employer creates project
GET    /api/v1/projects/<id>/          → project detail (increments view count)
PUT    /api/v1/projects/<id>/          → employer updates own project (DRAFT only)
DELETE /api/v1/projects/<id>/          → employer cancels own project
POST   /api/v1/projects/<id>/publish/  → employer publishes DRAFT → OPEN
POST   /api/v1/projects/<id>/complete/ → employer marks project as completed
GET    /api/v1/projects/my/            → employer's own projects
GET    /api/v1/projects/categories/    → list all project categories
POST   /api/v1/projects/<id>/review/   → leave review after completion
"""
from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from core.permissions import IsEmployer, IsVerifiedEmployer, IsPlatformAdmin, IsOwnerOrAdmin
from .models import Project, ProjectCategory, Review
from .serializers import ProjectListSerializer, ProjectDetailSerializer, ProjectCategorySerializer, ReviewSerializer
from .filters import ProjectFilter


class ProjectCategoryListView(generics.ListAPIView):
    """GET /api/v1/projects/categories/"""
    serializer_class = ProjectCategorySerializer
    permission_classes = [AllowAny]
    queryset = ProjectCategory.objects.filter(is_active=True)


class ProjectListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/projects/  → public browsing of open projects
    POST /api/v1/projects/  → employer creates a new project (starts as DRAFT)
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProjectFilter
    search_fields = ["title", "description", "required_skills__name"]
    ordering_fields = ["created_at", "budget_min", "budget_max", "proposals_count", "views_count"]
    ordering = ["-is_featured", "-created_at"]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsVerifiedEmployer()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProjectDetailSerializer
        return ProjectListSerializer

    def get_queryset(self):
        qs = Project.objects.select_related("employer", "category").prefetch_related("required_skills")
        if self.request.method == "GET":
            return qs.filter(status=Project.Status.OPEN)
        return qs

    def perform_create(self, serializer):
        serializer.save(employer=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Update employer stats
        try:
            request.user.employer_profile.total_projects_posted += 1  # type: ignore
            request.user.employer_profile.save(update_fields=["total_projects_posted"])
        except Exception:
            pass
        return Response(
            {"success": True, "message": "پروژه با موفقیت ایجاد شد.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/projects/<id>/  → any user
    PUT    /api/v1/projects/<id>/  → employer (DRAFT only)
    DELETE /api/v1/projects/<id>/  → employer cancels
    """
    serializer_class = ProjectDetailSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerOrAdmin()]

    def get_queryset(self):
        return Project.objects.select_related(
            "employer", "hired_student", "category"
        ).prefetch_related("required_skills", "attachments")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count (non-atomic is fine for analytics)
        Project.objects.filter(pk=instance.pk).update(views_count=instance.views_count + 1)
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != Project.Status.DRAFT:
            return Response(
                {"success": False, "error": {"message": "فقط پروژه‌های پیش‌نویس قابل ویرایش هستند."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        kwargs["partial"] = True
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == Project.Status.IN_PROGRESS:
            return Response(
                {"success": False, "error": {"message": "پروژه‌های در حال انجام را نمی‌توان حذف کرد. از لغو استفاده کنید."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.cancel()
        return Response({"success": True, "message": "پروژه لغو شد."}, status=status.HTTP_200_OK)


class PublishProjectView(APIView):
    """POST /api/v1/projects/<uuid:pk>/publish/ — employer publishes DRAFT → OPEN"""
    permission_classes = [IsAuthenticated, IsVerifiedEmployer]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, employer=request.user)
        if project.status != Project.Status.DRAFT:
            return Response(
                {"success": False, "error": {"message": "فقط پروژه‌های پیش‌نویس را می‌توان منتشر کرد."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project.publish()
        return Response({"success": True, "message": "پروژه با موفقیت منتشر شد.", "data": ProjectDetailSerializer(project).data})


class CompleteProjectView(APIView):
    """POST /api/v1/projects/<uuid:pk>/complete/ — employer confirms project done"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, employer=request.user)
        if project.status != Project.Status.IN_PROGRESS:
            return Response(
                {"success": False, "error": {"message": "فقط پروژه‌های در حال انجام را می‌توان تکمیل کرد."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project.complete()

        # Update student stats
        if project.hired_student:
            try:
                sp = project.hired_student.student_profile
                sp.total_projects_completed += 1
                sp.save(update_fields=["total_projects_completed"])
            except Exception:
                pass

        # Notify student
        from apps.notifications.models import Notification
        if project.hired_student:
            Notification.send(
                recipient=project.hired_student,
                notification_type="project_completed",
                title="پروژه تکمیل شد",
                body=f"پروژه «{project.title}» توسط کارفرما تکمیل اعلام شد.",
                related_object_id=project.id,
                related_object_type="project",
            )

        return Response({"success": True, "message": "پروژه با موفقیت تکمیل شد."})


class MyProjectsView(generics.ListAPIView):
    """GET /api/v1/projects/my/ — employer sees own projects"""
    serializer_class = ProjectListSerializer
    permission_classes = [IsAuthenticated, IsEmployer]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Project.objects.filter(
            employer=self.request.user
        ).select_related("category").prefetch_related("required_skills")


class ReviewCreateView(generics.CreateAPIView):
    """POST /api/v1/projects/<uuid:project_pk>/review/"""
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        if project.status != Project.Status.COMPLETED:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("فقط برای پروژه‌های تکمیل‌شده می‌توان نظر ثبت کرد.")
        serializer.save(project=project)
