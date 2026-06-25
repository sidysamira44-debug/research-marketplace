"""
Proposal views.

POST /api/v1/proposals/                    → student submits proposal
GET  /api/v1/proposals/my/                 → student sees own proposals
GET  /api/v1/proposals/project/<id>/       → employer sees proposals for their project
GET  /api/v1/proposals/<id>/               → proposal detail
POST /api/v1/proposals/<id>/action/        → employer: accept / reject
POST /api/v1/proposals/<id>/withdraw/      → student withdraws proposal
GET  /api/v1/proposals/messages/<proj_id>/ → conversation thread
POST /api/v1/proposals/messages/<proj_id>/ → send message
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from core.permissions import IsStudent, IsEmployer, IsPlatformAdmin
from apps.projects.models import Project
from apps.notifications.models import Notification
from .models import Proposal, Message
from .serializers import (
    ProposalListSerializer, ProposalDetailSerializer,
    ProposalActionSerializer, MessageSerializer,
)


class SubmitProposalView(generics.CreateAPIView):
    """POST /api/v1/proposals/ — student submits a proposal"""
    serializer_class = ProposalDetailSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proposal = serializer.save()

        # Notify employer
        Notification.send(
            recipient=proposal.project.employer,
            notification_type="proposal_received",
            title="پیشنهاد جدید دریافت شد",
            body=f"«{request.user.full_name}» برای پروژه «{proposal.project.title}» پیشنهاد ارسال کرد.",
            related_object_id=proposal.id,
            related_object_type="proposal",
        )

        return Response(
            {"success": True, "message": "پیشنهاد با موفقیت ارسال شد.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


class MyProposalsView(generics.ListAPIView):
    """GET /api/v1/proposals/my/ — student's own proposals"""
    serializer_class = ProposalListSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    filterset_fields = ["status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Proposal.objects.filter(
            student=self.request.user
        ).select_related("project", "student")


class ProjectProposalsView(generics.ListAPIView):
    """
    GET /api/v1/proposals/project/<uuid:project_pk>/
    Employer sees all proposals for their own project.
    Admin can see any project's proposals.
    """
    serializer_class = ProposalDetailSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        user = self.request.user
        # Only employer who owns the project or admin
        if user.role == "admin" or project.employer == user:
            return Proposal.objects.filter(project=project).select_related("student", "project")
        return Proposal.objects.none()


class ProposalDetailView(generics.RetrieveAPIView):
    """GET /api/v1/proposals/<uuid:pk>/"""
    serializer_class = ProposalDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Proposal.objects.all()
        if user.role == "student":
            return Proposal.objects.filter(student=user)
        # Employer sees proposals on their own projects
        return Proposal.objects.filter(project__employer=user)

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response({"success": True, "data": serializer.data})


class ProposalActionView(APIView):
    """
    POST /api/v1/proposals/<uuid:pk>/action/
    Body: { "action": "accept" | "reject", "note": "..." }
    Employer accepts or rejects a pending proposal.
    """
    permission_classes = [IsAuthenticated, IsEmployer]

    def post(self, request, pk):
        proposal = get_object_or_404(Proposal, pk=pk, project__employer=request.user)

        if proposal.status != Proposal.Status.PENDING:
            return Response(
                {"success": False, "error": {"message": "فقط پیشنهادهای در انتظار را می‌توان بررسی کرد."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProposalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]
        note = serializer.validated_data.get("note", "")

        if action == "accept":
            proposal.accept()
            notif_type = "proposal_accepted"
            msg = f"پیشنهاد شما برای پروژه «{proposal.project.title}» پذیرفته شد."
            response_msg = "پیشنهاد با موفقیت پذیرفته شد و پروژه شروع شد."
        else:
            proposal.reject(note=note)
            notif_type = "proposal_rejected"
            msg = f"پیشنهاد شما برای پروژه «{proposal.project.title}» رد شد."
            response_msg = "پیشنهاد رد شد."

        Notification.send(
            recipient=proposal.student,
            notification_type=notif_type,
            title="نتیجه بررسی پیشنهاد",
            body=msg,
            related_object_id=proposal.id,
            related_object_type="proposal",
        )

        return Response({"success": True, "message": response_msg})


class WithdrawProposalView(APIView):
    """POST /api/v1/proposals/<uuid:pk>/withdraw/ — student withdraws pending proposal"""
    permission_classes = [IsAuthenticated, IsStudent]

    def post(self, request, pk):
        proposal = get_object_or_404(Proposal, pk=pk, student=request.user)
        if proposal.status != Proposal.Status.PENDING:
            return Response(
                {"success": False, "error": {"message": "فقط پیشنهادهای در انتظار را می‌توان پس گرفت."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        proposal.withdraw()
        return Response({"success": True, "message": "پیشنهاد با موفقیت پس گرفته شد."})


class MessageThreadView(APIView):
    """
    GET  /api/v1/proposals/messages/<uuid:project_pk>/ → get conversation
    POST /api/v1/proposals/messages/<uuid:project_pk>/ → send message
    """
    permission_classes = [IsAuthenticated]

    def _get_project_and_check_access(self, request, project_pk):
        project = get_object_or_404(Project, pk=project_pk)
        user = request.user
        is_employer = project.employer == user
        is_student = project.hired_student == user
        is_admin = user.role == "admin"
        if not (is_employer or is_student or is_admin):
            return None, None
        return project, True

    def get(self, request, project_pk):
        project, ok = self._get_project_and_check_access(request, project_pk)
        if not ok:
            return Response(
                {"success": False, "error": {"message": "دسترسی مجاز نیست."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        messages = Message.objects.filter(project=project).select_related("sender")
        # Mark unread messages as read for this user
        Message.objects.filter(project=project, is_read=False).exclude(sender=request.user).update(is_read=True)
        serializer = MessageSerializer(messages, many=True)
        return Response({"success": True, "data": serializer.data})

    def post(self, request, project_pk):
        project, ok = self._get_project_and_check_access(request, project_pk)
        if not ok:
            return Response(
                {"success": False, "error": {"message": "دسترسی مجاز نیست."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(project=project, sender=request.user)

        # Notify the other party
        recipient = project.hired_student if request.user == project.employer else project.employer
        if recipient:
            Notification.send(
                recipient=recipient,
                notification_type="new_message",
                title="پیام جدید",
                body=f"پیام جدید از «{request.user.full_name}» در پروژه «{project.title}»",
                related_object_id=project.id,
                related_object_type="project",
            )

        return Response(
            {"success": True, "data": MessageSerializer(message).data},
            status=status.HTTP_201_CREATED,
        )
