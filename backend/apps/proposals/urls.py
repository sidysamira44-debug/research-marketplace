from django.urls import path
from .views import (
    SubmitProposalView, MyProposalsView,
    ProjectProposalsView, ProposalDetailView,
    ProposalActionView, WithdrawProposalView,
    MessageThreadView,
)

app_name = "proposals"

urlpatterns = [
    path("",                                 SubmitProposalView.as_view(),    name="submit"),
    path("my/",                              MyProposalsView.as_view(),       name="my-proposals"),
    path("project/<uuid:project_pk>/",       ProjectProposalsView.as_view(),  name="project-proposals"),
    path("<uuid:pk>/",                       ProposalDetailView.as_view(),    name="detail"),
    path("<uuid:pk>/action/",               ProposalActionView.as_view(),    name="action"),
    path("<uuid:pk>/withdraw/",             WithdrawProposalView.as_view(),  name="withdraw"),
    path("messages/<uuid:project_pk>/",     MessageThreadView.as_view(),     name="messages"),
]
