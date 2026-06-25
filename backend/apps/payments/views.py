"""
Payment views — Stripe escrow workflow.

POST /api/v1/payments/create-intent/   → employer creates PaymentIntent
POST /api/v1/payments/webhook/         → Stripe webhook (no auth)
POST /api/v1/payments/release/<pk>/    → admin releases escrow to student
GET  /api/v1/payments/transactions/    → list own transactions
POST /api/v1/payments/dispute/         → raise a dispute
GET  /api/v1/payments/disputes/        → admin: list all disputes
POST /api/v1/payments/disputes/<pk>/resolve/ → admin resolves dispute
"""
import stripe
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404

from core.permissions import IsEmployer, IsPlatformAdmin
from apps.notifications.models import Notification
from .models import Transaction, Dispute
from .serializers import (
    TransactionSerializer, DisputeSerializer,
    CreatePaymentIntentSerializer,
)

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


class CreatePaymentIntentView(APIView):
    """
    POST /api/v1/payments/create-intent/
    Employer initiates escrow payment for an in-progress project.
    Returns a Stripe client_secret for frontend to complete payment.
    """
    permission_classes = [IsAuthenticated, IsEmployer]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data["project_id"]

        commission_pct = Decimal(str(settings.PLATFORM_COMMISSION_PERCENT))
        gross = project.agreed_price
        commission = (gross * commission_pct / 100).quantize(Decimal("0.01"))
        net = gross - commission

        try:
            # Stripe works in smallest currency unit (Rial × 10 for test; use USD for real)
            # For Iran (IRR), use amount in Tomans × 10 = Rials
            intent = stripe.PaymentIntent.create(
                amount=int(gross * 10),         # Tomans → Rials
                currency="irr",
                metadata={
                    "project_id": str(project.id),
                    "employer_id": str(request.user.id),
                    "student_id": str(project.hired_student.id) if project.hired_student else "",
                    "commission_amount": str(commission),
                    "net_amount": str(net),
                },
                description=f"Escrow for project: {project.title}",
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            return Response(
                {"success": False, "error": {"message": f"خطای پرداخت: {str(e)}"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create pending transaction record
        txn = Transaction.objects.create(
            project=project,
            payer=request.user,
            payee=project.hired_student,
            gross_amount=gross,
            commission_amount=commission,
            net_amount=net,
            commission_percent=commission_pct,
            transaction_type=Transaction.TransactionType.ESCROW_HOLD,
            status=Transaction.Status.PENDING,
            stripe_payment_intent_id=intent.id,
            description=f"امانت برای پروژه: {project.title}",
        )

        return Response({
            "success": True,
            "data": {
                "client_secret": intent.client_secret,
                "transaction_id": str(txn.id),
                "amount": str(gross),
                "commission": str(commission),
                "net_to_student": str(net),
            }
        })


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """
    POST /api/v1/payments/webhook/
    Receives Stripe events. No JWT auth — verified by Stripe signature.
    Key events handled:
      - payment_intent.succeeded → mark transaction COMPLETED
      - payment_intent.payment_failed → mark FAILED
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.warning(f"Invalid Stripe webhook: {e}")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event["type"] == "payment_intent.succeeded":
            self._handle_payment_succeeded(event["data"]["object"])
        elif event["type"] == "payment_intent.payment_failed":
            self._handle_payment_failed(event["data"]["object"])

        return Response({"received": True})

    def _handle_payment_succeeded(self, intent):
        try:
            txn = Transaction.objects.get(stripe_payment_intent_id=intent["id"])
            txn.status = Transaction.Status.COMPLETED
            txn.completed_at = timezone.now()
            txn.save(update_fields=["status", "completed_at"])
            logger.info(f"Payment succeeded for transaction {txn.id}")

            Notification.send(
                recipient=txn.payer,
                notification_type="payment_released",
                title="پرداخت موفق",
                body=f"مبلغ {txn.gross_amount:,.0f} تومان برای پروژه «{txn.project.title}» با موفقیت پرداخت شد.",
                related_object_id=txn.project.id,
                related_object_type="project",
            )
        except Transaction.DoesNotExist:
            logger.error(f"Transaction not found for intent {intent['id']}")

    def _handle_payment_failed(self, intent):
        try:
            txn = Transaction.objects.get(stripe_payment_intent_id=intent["id"])
            txn.status = Transaction.Status.FAILED
            txn.stripe_error_message = intent.get("last_payment_error", {}).get("message", "")
            txn.save(update_fields=["status", "stripe_error_message"])
        except Transaction.DoesNotExist:
            pass


class ReleaseEscrowView(APIView):
    """
    POST /api/v1/payments/release/<uuid:txn_id>/
    Admin-only: release escrowed funds to student after project verification.
    """
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, txn_id):
        txn = get_object_or_404(Transaction, pk=txn_id, transaction_type=Transaction.TransactionType.ESCROW_HOLD)

        if txn.status != Transaction.Status.COMPLETED:
            return Response(
                {"success": False, "error": {"message": "فقط تراکنش‌های موفق قابل آزادسازی هستند."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # In production, use Stripe Connect transfer to student's account
        # For now, create a RELEASE transaction record
        release_txn = Transaction.objects.create(
            project=txn.project,
            payer=txn.payer,
            payee=txn.payee,
            gross_amount=txn.gross_amount,
            commission_amount=txn.commission_amount,
            net_amount=txn.net_amount,
            commission_percent=txn.commission_percent,
            transaction_type=Transaction.TransactionType.RELEASE,
            status=Transaction.Status.COMPLETED,
            completed_at=timezone.now(),
            description=f"آزادسازی وجه برای پروژه: {txn.project.title}",
        )

        if txn.payee:
            Notification.send(
                recipient=txn.payee,
                notification_type="payment_released",
                title="وجه دریافت شد",
                body=f"مبلغ {txn.net_amount:,.0f} تومان برای پروژه «{txn.project.title}» به حساب شما واریز شد.",
                related_object_id=txn.project.id,
                related_object_type="project",
            )

        return Response({
            "success": True,
            "message": "وجه با موفقیت آزاد شد.",
            "data": TransactionSerializer(release_txn).data,
        })


class TransactionListView(generics.ListAPIView):
    """GET /api/v1/payments/transactions/ — user sees own transactions"""
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["transaction_type", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Transaction.objects.all().select_related("project", "payer", "payee")
        return Transaction.objects.filter(
            payer=user
        ).select_related("project", "payer", "payee")


class RaiseDisputeView(generics.CreateAPIView):
    """POST /api/v1/payments/dispute/ — employer or student raises a dispute"""
    serializer_class = DisputeSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(raised_by=self.request.user)
        # Change project status to DISPUTED
        project = serializer.instance.project
        project.status = "disputed"
        project.save(update_fields=["status"])


class DisputeListView(generics.ListAPIView):
    """GET /api/v1/payments/disputes/ — admin sees all disputes"""
    serializer_class = DisputeSerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    filterset_fields = ["resolution"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Dispute.objects.all().select_related("project", "raised_by", "resolved_by")


class ResolveDisputeView(APIView):
    """POST /api/v1/payments/disputes/<uuid:pk>/resolve/ — admin resolves"""
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, pk):
        dispute = get_object_or_404(Dispute, pk=pk)
        resolution = request.data.get("resolution")
        admin_note = request.data.get("admin_note", "")

        valid_resolutions = [c[0] for c in Dispute.Resolution.choices if c[0] != "pending"]
        if resolution not in valid_resolutions:
            return Response(
                {"success": False, "error": {"message": f"نتیجه باید یکی از {valid_resolutions} باشد."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dispute.resolution = resolution
        dispute.admin_note = admin_note
        dispute.resolved_by = request.user
        dispute.resolved_at = timezone.now()
        dispute.save(update_fields=["resolution", "admin_note", "resolved_by", "resolved_at"])

        # Notify both parties
        for recipient in [dispute.project.employer, dispute.project.hired_student]:
            if recipient:
                Notification.send(
                    recipient=recipient,
                    notification_type="dispute_resolved",
                    title="اختلاف حل شد",
                    body=f"اختلاف پروژه «{dispute.project.title}» توسط ادمین بررسی و حل شد.",
                    related_object_id=dispute.project.id,
                    related_object_type="project",
                )

        return Response({
            "success": True,
            "message": "اختلاف با موفقیت حل شد.",
            "data": DisputeSerializer(dispute).data,
        })
