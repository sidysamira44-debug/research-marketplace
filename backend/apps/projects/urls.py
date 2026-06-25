from django.urls import path
from .views import (
    ProjectCategoryListView,
    ProjectListCreateView, ProjectDetailView,
    PublishProjectView, CompleteProjectView,
    MyProjectsView, ReviewCreateView,
)

app_name = "projects"

urlpatterns = [
    path("",                            ProjectListCreateView.as_view(),  name="list-create"),
    path("categories/",                 ProjectCategoryListView.as_view(), name="category-list"),
    path("my/",                         MyProjectsView.as_view(),          name="my-projects"),
    path("<uuid:pk>/",                  ProjectDetailView.as_view(),       name="detail"),
    path("<uuid:pk>/publish/",          PublishProjectView.as_view(),      name="publish"),
    path("<uuid:pk>/complete/",         CompleteProjectView.as_view(),     name="complete"),
    path("<uuid:project_pk>/review/",   ReviewCreateView.as_view(),        name="review-create"),
]
