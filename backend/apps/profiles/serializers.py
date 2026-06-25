"""
Serializers for profiles app.

SkillSerializer          : skill tag
StudentProfileSerializer : full student profile (self + public)
EmployerProfileSerializer: full employer profile
"""
from rest_framework import serializers
from .models import Skill, StudentProfile, EmployerProfile
from apps.users.serializers import UserSerializer


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name", "name_en", "category"]


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Skill.objects.filter(is_active=True),
        write_only=True, source="skills", required=False,
    )
    availability_display = serializers.CharField(source="get_availability_display", read_only=True)
    degree_display = serializers.CharField(source="get_degree_display", read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "user", "university", "field_of_study", "degree", "degree_display",
            "gpa", "graduation_year", "skills", "skill_ids", "bio", "research_interests",
            "resume", "portfolio_url", "github_url", "linkedin_url",
            "availability", "availability_display", "hourly_rate",
            "total_projects_completed", "average_rating",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "total_projects_completed", "average_rating", "created_at", "updated_at"]


class StudentProfilePublicSerializer(serializers.ModelSerializer):
    """Reduced fields for public-facing student card (project browse, employer search)."""
    user = UserSerializer(read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    availability_display = serializers.CharField(source="get_availability_display", read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "user", "university", "field_of_study", "degree",
            "skills", "bio", "portfolio_url", "github_url",
            "availability", "availability_display", "hourly_rate",
            "total_projects_completed", "average_rating",
        ]


class EmployerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    organization_type_display = serializers.CharField(source="get_organization_type_display", read_only=True)

    class Meta:
        model = EmployerProfile
        fields = [
            "id", "user", "organization_name", "organization_type", "organization_type_display",
            "description", "website", "logo", "city", "province",
            "registration_number", "verification_document",
            "total_projects_posted", "total_hires", "average_rating",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "total_projects_posted", "total_hires", "average_rating", "created_at", "updated_at"]
        extra_kwargs = {
            "verification_document": {"write_only": True},
            "registration_number": {"write_only": True},
        }


class EmployerProfilePublicSerializer(serializers.ModelSerializer):
    """Public-facing employer info (no sensitive verification docs)."""
    user = UserSerializer(read_only=True)
    organization_type_display = serializers.CharField(source="get_organization_type_display", read_only=True)

    class Meta:
        model = EmployerProfile
        fields = [
            "id", "user", "organization_name", "organization_type", "organization_type_display",
            "description", "website", "logo", "city", "province",
            "total_projects_posted", "total_hires", "average_rating",
        ]
