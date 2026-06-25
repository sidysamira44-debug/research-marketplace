"""
Profile views.

GET  /api/v1/profiles/me/student/   → own student profile
PUT  /api/v1/profiles/me/student/   → update own student profile
GET  /api/v1/profiles/me/employer/  → own employer profile
PUT  /api/v1/profiles/me/employer/  → update own employer profile
GET  /api/v1/profiles/students/     → public student list (employer / admin)
GET  /api/v1/profiles/students/<id>/→ public student detail
GET  /api/v1/profiles/employers/<id>/→ public employer detail
GET  /api/v1/profiles/skills/       → all active skills
"""
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsStudent, IsEmployer, IsPlatformAdmin, IsOwnerOrAdmin
from .models import Skill, StudentProfile, EmployerProfile
from .serializers import (
    SkillSerializer,
    StudentProfileSerializer, StudentProfilePublicSerializer,
    EmployerProfileSerializer, EmployerProfilePublicSerializer,
)
from .filters import StudentProfileFilter


class SkillListView(generics.ListAPIView):
    """GET /api/v1/profiles/skills/  — public, no auth needed."""
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]
    queryset = Skill.objects.filter(is_active=True)
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "name_en", "category"]


class MyStudentProfileView(generics.RetrieveUpdateAPIView):
    """GET/PUT/PATCH /api/v1/profiles/me/student/"""
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_object(self):
        return self.request.user.student_profile

    def retrieve(self, request, *args, **kwargs):
        from rest_framework.response import Response
        serializer = self.get_serializer(self.get_object())
        return Response({"success": True, "data": serializer.data})

    def update(self, request, *args, **kwargs):
        from rest_framework.response import Response
        kwargs["partial"] = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": serializer.data})


class MyEmployerProfileView(generics.RetrieveUpdateAPIView):
    """GET/PUT/PATCH /api/v1/profiles/me/employer/"""
    serializer_class = EmployerProfileSerializer
    permission_classes = [IsAuthenticated, IsEmployer]

    def get_object(self):
        return self.request.user.employer_profile

    def retrieve(self, request, *args, **kwargs):
        from rest_framework.response import Response
        serializer = self.get_serializer(self.get_object())
        return Response({"success": True, "data": serializer.data})

    def update(self, request, *args, **kwargs):
        from rest_framework.response import Response
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": serializer.data})


class StudentListView(generics.ListAPIView):
    """
    GET /api/v1/profiles/students/
    Employer / Admin can browse verified students.
    Supports filtering by skill, availability, university.
    """
    serializer_class = StudentProfilePublicSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StudentProfileFilter
    search_fields = ["user__full_name", "university", "field_of_study", "bio"]
    ordering_fields = ["average_rating", "total_projects_completed", "hourly_rate"]
    ordering = ["-average_rating"]

    def get_queryset(self):
        return StudentProfile.objects.filter(
            user__is_verified=True,
            user__is_active=True,
        ).select_related("user").prefetch_related("skills")


class StudentDetailView(generics.RetrieveAPIView):
    """GET /api/v1/profiles/students/<uuid:pk>/"""
    serializer_class = StudentProfilePublicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StudentProfile.objects.filter(
            user__is_active=True
        ).select_related("user").prefetch_related("skills")

    def retrieve(self, request, *args, **kwargs):
        from rest_framework.response import Response
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})


class EmployerDetailView(generics.RetrieveAPIView):
    """GET /api/v1/profiles/employers/<uuid:pk>/"""
    serializer_class = EmployerProfilePublicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployerProfile.objects.filter(user__is_active=True).select_related("user")

    def retrieve(self, request, *args, **kwargs):
        from rest_framework.response import Response
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})
