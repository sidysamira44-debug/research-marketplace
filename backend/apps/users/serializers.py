"""
Serializers for users app.

RegisterSerializer   : validates + creates new user (student or employer)
LoginSerializer      : email + password → JWT tokens
UserSerializer       : read-only public user info
UserProfileSerializer: full user info for self-view (includes role-specific profile)
ChangePasswordSerializer: authenticated password change
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserRole


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles new user registration.
    Password is write-only and confirmed with password2.
    On success, returns JWT access + refresh tokens immediately.
    """
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"}, label="تأیید رمز عبور")
    tokens = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "phone_number", "password", "password2", "tokens"]
        extra_kwargs = {
            "role": {"required": True},
        }

    def validate_role(self, value):
        if value == UserRole.ADMIN:
            raise serializers.ValidationError("ثبت‌نام با نقش مدیر مجاز نیست.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "رمزهای عبور با هم مطابقت ندارند."})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def get_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class LoginSerializer(serializers.Serializer):
    """
    Email + password login.
    Returns user data + JWT tokens on success.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("ایمیل و رمز عبور الزامی هستند.")

        user = authenticate(request=self.context.get("request"), email=email, password=password)

        if not user:
            raise serializers.ValidationError("ایمیل یا رمز عبور اشتباه است.")
        if not user.is_active:
            raise serializers.ValidationError("حساب کاربری شما تعلیق شده است.")

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Compact user representation for public views and nested usage."""
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "role_display", "avatar", "is_verified", "date_joined"]
        read_only_fields = ["id", "email", "role", "is_verified", "date_joined"]


class UserMeSerializer(serializers.ModelSerializer):
    """
    Full user info for /auth/me/ endpoint (authenticated user only).
    Includes editable fields like full_name, phone_number, avatar.
    """
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "role", "role_display",
            "phone_number", "avatar", "is_verified", "is_active",
            "date_joined", "last_seen",
        ]
        read_only_fields = ["id", "email", "role", "is_verified", "is_active", "date_joined", "last_seen"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    new_password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("رمز عبور فعلی اشتباه است.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "رمزهای عبور جدید با هم مطابقت ندارند."})
        validate_password(attrs["new_password"])
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
