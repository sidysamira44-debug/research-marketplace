"""
Authentication views for Research Marketplace.

POST /api/v1/auth/register/        → RegisterView
POST /api/v1/auth/login/           → LoginView
POST /api/v1/auth/logout/          → LogoutView  (blacklist refresh token)
POST /api/v1/auth/token/refresh/   → TokenRefreshView (SimpleJWT)
GET  /api/v1/auth/me/              → MeView (current user info)
PUT  /api/v1/auth/me/              → MeView (update profile)
POST /api/v1/auth/change-password/ → ChangePasswordView
POST /api/v1/auth/verify/<id>/     → AdminVerifyUserView
"""
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView

from core.permissions import IsPlatformAdmin
from .models import User
from .serializers import (
    RegisterSerializer, LoginSerializer,
    UserMeSerializer, ChangePasswordSerializer, UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Body: { email, full_name, role, phone_number, password, password2 }
    Returns: user data + { access, refresh } tokens
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "success": True,
                "message": "ثبت‌نام با موفقیت انجام شد.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Body: { email, password }
    Returns: user info + { access, refresh } tokens
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.update_last_seen()

        refresh = RefreshToken.for_user(user)
        user_data = UserMeSerializer(user, context={"request": request}).data

        return Response(
            {
                "success": True,
                "message": "ورود موفقیت‌آمیز بود.",
                "data": {
                    "user": user_data,
                    "tokens": {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                    },
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Body: { refresh }
    Blacklists the refresh token to invalidate the session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"success": False, "error": {"message": "توکن refresh الزامی است."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {"success": False, "error": {"message": "توکن نامعتبر است."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"success": True, "message": "با موفقیت خارج شدید."}, status=status.HTTP_200_OK)


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/auth/me/ → current user info
    PUT  /api/v1/auth/me/ → update full_name, phone_number, avatar
    PATCH /api/v1/auth/me/ → partial update
    """
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response({"success": True, "data": serializer.data})

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True  # Always partial to protect email/role
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": serializer.data})


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "message": "رمز عبور با موفقیت تغییر یافت."})


class AdminVerifyUserView(APIView):
    """
    POST /api/v1/auth/verify/<uuid:user_id>/
    Admin-only: verify a user account after document review.
    """
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"success": False, "error": {"message": "کاربر یافت نشد."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_verified:
            return Response(
                {"success": False, "error": {"message": "این کاربر قبلاً تأیید شده است."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.verify()

        # Send notification (non-blocking)
        from apps.notifications.models import Notification
        Notification.send(
            recipient=user,
            notification_type="account_verified",
            title="حساب شما تأیید شد",
            body="حساب کاربری شما توسط مدیریت پلتفرم تأیید شد. اکنون می‌توانید از تمام امکانات استفاده کنید.",
        )

        return Response(
            {
                "success": True,
                "message": f"حساب کاربری {user.full_name} با موفقیت تأیید شد.",
                "data": UserSerializer(user).data,
            }
        )


class AdminUserListView(generics.ListAPIView):
    """
    GET /api/v1/auth/users/
    Admin-only: list all users with filters.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    filterset_fields = ["role", "is_verified", "is_active"]
    search_fields = ["email", "full_name"]
    ordering_fields = ["date_joined", "last_seen"]
    ordering = ["-date_joined"]

    def get_queryset(self):
        return User.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})
