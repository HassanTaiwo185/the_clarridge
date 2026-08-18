from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Profile
from .permissions import IsSuperUser
from .serializers import (
    RegisterSerializer,
    VerifyEmailSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    GetUserSerializer,
    UpdateUserSerializer,
    PendingUserSerializer,
    ApproveUserSerializer,
    PromoteAdminSerializer,
    ChangePasswordSerializer,
     LogoutSerializer
   
)


# ---------------------------------------------------------
# Registration & verification
# ---------------------------------------------------------

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Registration successful. Check your email for a verification code.'},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(generics.CreateAPIView):
    serializer_class = VerifyEmailSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Email verified. Your account is pending admin approval.'},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------
# Password reset
# ---------------------------------------------------------

class ForgotPasswordView(generics.CreateAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'If this email is registered, a reset code has been sent.'},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(generics.CreateAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Password reset successful. You can now log in.'},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------
# Logged-in user's own profile
# ---------------------------------------------------------

class GetUserView(generics.RetrieveAPIView):
    serializer_class = GetUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.profile


class UpdateUserView(generics.UpdateAPIView):
    serializer_class = UpdateUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.profile


# ---------------------------------------------------------
# Superuser: approve pending users
# ---------------------------------------------------------

class PendingUsersView(generics.ListAPIView):
    """Superuser-only: list all users awaiting approval."""
    serializer_class = PendingUserSerializer
    permission_classes = [IsSuperUser]
    queryset = Profile.objects.filter(user__is_active=False)


class ApproveUserView(generics.CreateAPIView):
    """Superuser-only: approve a pending user by ID."""
    serializer_class = ApproveUserSerializer
    permission_classes = [IsSuperUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'message': f'{user.email} has been approved.'},
            status=status.HTTP_200_OK,
        )
    
class PromoteAdminView(generics.CreateAPIView):
    """Superuser-only: promote a user to admin (is_staff)."""
    serializer_class = PromoteAdminSerializer
    permission_classes = [IsSuperUser]  # only the true superuser can promote

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'message': f'{user.email} has been promoted to admin.'},
            status=status.HTTP_200_OK,
        )
    

class ChangePasswordView(generics.CreateAPIView):
    """Authenticated: change your own password using request.user, not the request body."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
    
class LogoutView(generics.CreateAPIView):
    """Authenticated: blacklist the refresh token, ending the session."""
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)