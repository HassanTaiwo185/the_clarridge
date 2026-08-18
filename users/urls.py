from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView,
    VerifyEmailView,
    ForgotPasswordView,
    ResetPasswordView,
    GetUserView,
    UpdateUserView,
    PendingUsersView,
    ApproveUserView,
    PromoteAdminView,
    ChangePasswordView,
    LogoutView

)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('me/', GetUserView.as_view(), name='get-user'),
    path('me/update/', UpdateUserView.as_view(), name='update-user'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='login-refresh'),
    path('admin/pending-users/', PendingUsersView.as_view(), name='pending-users'),
    path('admin/approve-user/', ApproveUserView.as_view(), name='approve-user'),
    path('admin/promote-admin/', PromoteAdminView.as_view(), name='promote-admin'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('logout/', LogoutView.as_view(), name='logout'),

]