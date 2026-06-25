from django.urls import path
from .views import (
    CreatePaymentIntentView, StripeWebhookView,
    ReleaseEscrowView, TransactionListView,
    RaiseDisputeView, DisputeListView, ResolveDisputeView,
)

app_name = "payments"

urlpatterns = [
    path("create-intent/",              CreatePaymentIntentView.as_view(), name="create-intent"),
    path("webhook/",                    StripeWebhookView.as_view(),       name="webhook"),
    path("release/<uuid:txn_id>/",      ReleaseEscrowView.as_view(),       name="release"),
    path("transactions/",               TransactionListView.as_view(),     name="transactions"),
    path("dispute/",                    RaiseDisputeView.as_view(),        name="raise-dispute"),
    path("disputes/",                   DisputeListView.as_view(),         name="dispute-list"),
    path("disputes/<uuid:pk>/resolve/", ResolveDisputeView.as_view(),      name="resolve-dispute"),
]
