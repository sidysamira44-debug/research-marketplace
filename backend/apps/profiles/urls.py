from django.urls import path
from .views import (
    SkillListView,
    MyStudentProfileView, MyEmployerProfileView,
    StudentListView, StudentDetailView, EmployerDetailView,
)

app_name = "profiles"

urlpatterns = [
    path("skills/",               SkillListView.as_view(),        name="skill-list"),
    path("me/student/",           MyStudentProfileView.as_view(), name="my-student-profile"),
    path("me/employer/",          MyEmployerProfileView.as_view(), name="my-employer-profile"),
    path("students/",             StudentListView.as_view(),      name="student-list"),
    path("students/<uuid:pk>/",   StudentDetailView.as_view(),    name="student-detail"),
    path("employers/<uuid:pk>/",  EmployerDetailView.as_view(),   name="employer-detail"),
]
