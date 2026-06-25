"""Serializers for proposals app."""
from rest_framework import serializers
from .models import Proposal, Message
from apps.users.serializers import UserSerializer
from apps.projects.serializers import ProjectListSerializer


class ProposalListSerializer(serializers.ModelSerializer):
    """Compact proposal for listing views."""
    student = UserSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Proposal
        fields = [
            "id", "project", "student", "proposed_price",
            "proposed_duration_days", "status", "status_display", "created_at",
        ]


class ProposalDetailSerializer(serializers.ModelSerializer):
    """Full proposal detail."""
    student = UserSerializer(read_only=True)
    project = ProjectListSerializer(read_only=True)
    project_id = serializers.UUIDField(write_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Proposal
        fields = [
            "id", "project", "project_id", "student",
            "cover_letter", "proposed_price", "proposed_duration_days",
            "relevant_experience", "portfolio_link",
            "status", "status_display", "employer_note",
            "created_at", "updated_at", "reviewed_at",
        ]
        read_only_fields = ["id", "student", "status", "employer_note", "reviewed_at", "created_at", "updated_at"]

    def validate_project_id(self, value):
        from apps.projects.models import Project
        try:
            project = Project.objects.get(id=value)
        except Project.DoesNotExist:
            raise serializers.ValidationError("پروژه یافت نشد.")
        if project.status != Project.Status.OPEN:
            raise serializers.ValidationError("این پروژه برای دریافت پیشنهاد باز نیست.")
        return project

    def validate(self, attrs):
        request = self.context["request"]
        project = attrs.get("project_id")
        if project and Proposal.objects.filter(project=project, student=request.user).exists():
            raise serializers.ValidationError({"project_id": "شما قبلاً برای این پروژه پیشنهاد ارسال کرده‌اید."})
        return attrs

    def create(self, validated_data):
        project = validated_data.pop("project_id")
        proposal = Proposal.objects.create(
            student=self.context["request"].user,
            project=project,
            **validated_data,
        )
        # Update project proposal count
        from apps.projects.models import Project
        Project.objects.filter(pk=project.pk).update(proposals_count=project.proposals_count + 1)
        return proposal


class ProposalActionSerializer(serializers.Serializer):
    """Used by employer to accept/reject a proposal."""
    action = serializers.ChoiceField(choices=["accept", "reject"])
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "project", "sender", "body", "attachment", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "is_read", "created_at"]
