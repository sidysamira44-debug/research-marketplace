"""Serializers for projects app."""
from rest_framework import serializers
from .models import Project, ProjectCategory, ProjectAttachment, Review
from apps.users.serializers import UserSerializer
from apps.profiles.serializers import SkillSerializer


class ProjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCategory
        fields = ["id", "name", "name_en", "icon"]


class ProjectAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAttachment
        fields = ["id", "file", "name", "uploaded_at"]
        read_only_fields = ["uploaded_at"]


class ProjectListSerializer(serializers.ModelSerializer):
    """Compact serializer for project listing pages."""
    employer = UserSerializer(read_only=True)
    category = ProjectCategorySerializer(read_only=True)
    required_skills = SkillSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    experience_level_display = serializers.CharField(source="get_experience_level_display", read_only=True)
    budget_display = serializers.CharField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "employer", "category", "required_skills",
            "budget_min", "budget_max", "budget_display",
            "duration_days", "experience_level", "experience_level_display",
            "project_type", "status", "status_display",
            "is_featured", "views_count", "proposals_count",
            "deadline", "created_at",
        ]


class ProjectDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for single project view."""
    employer = UserSerializer(read_only=True)
    hired_student = UserSerializer(read_only=True)
    category = ProjectCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ProjectCategory.objects.filter(is_active=True),
        source="category", write_only=True, required=False,
    )
    required_skills = SkillSerializer(many=True, read_only=True)
    required_skill_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="required_skills",
        queryset=__import__("apps.profiles.models", fromlist=["Skill"]).Skill.objects.filter(is_active=True),
        write_only=True, required=False,
    )
    attachments = ProjectAttachmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    experience_level_display = serializers.CharField(source="get_experience_level_display", read_only=True)
    project_type_display = serializers.CharField(source="get_project_type_display", read_only=True)
    budget_display = serializers.CharField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "description", "deliverables", "requirements",
            "employer", "hired_student",
            "category", "category_id",
            "required_skills", "required_skill_ids",
            "budget_min", "budget_max", "budget_display", "agreed_price",
            "duration_days", "experience_level", "experience_level_display",
            "project_type", "project_type_display",
            "status", "status_display", "is_featured",
            "views_count", "proposals_count",
            "deadline", "started_at", "completed_at", "created_at", "updated_at",
            "attachments",
        ]
        read_only_fields = [
            "id", "employer", "hired_student", "agreed_price",
            "status", "views_count", "proposals_count",
            "started_at", "completed_at", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        if attrs.get("budget_min") and attrs.get("budget_max"):
            if attrs["budget_min"] > attrs["budget_max"]:
                raise serializers.ValidationError({"budget_min": "حداقل بودجه نمی‌تواند بیشتر از حداکثر بودجه باشد."})
        return attrs


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = UserSerializer(read_only=True)
    reviewee = UserSerializer(read_only=True)
    reviewee_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Review
        fields = ["id", "project", "reviewer", "reviewee", "reviewee_id", "rating", "comment", "created_at"]
        read_only_fields = ["id", "reviewer", "created_at"]

    def validate_reviewee_id(self, value):
        from apps.users.models import User
        try:
            return User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("کاربر مورد نظر یافت نشد.")

    def create(self, validated_data):
        reviewee = validated_data.pop("reviewee_id")
        return Review.objects.create(
            reviewer=self.context["request"].user,
            reviewee=reviewee,
            **validated_data,
        )
