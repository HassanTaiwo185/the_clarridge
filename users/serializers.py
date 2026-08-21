from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .models import Profile
from .otp import (
    generate_otp,
    send_otp_email,
    stash_pending_registration,
    get_pending_registration,
    clear_pending_registration,
    stash_password_reset_otp,
    get_password_reset_otp,
    clear_password_reset_otp,
    send_approval_email,
)


# ---------------------------------------------------------
# Registration
# ---------------------------------------------------------
class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField()
    date_of_birth = serializers.DateField()

    def validate_email(self, value):
        existing_user = User.objects.filter(email=value).first()
        if existing_user:
            if existing_user.is_active:
                raise serializers.ValidationError(
                    "An account with this email already exists. Please log in instead."
                )
            else:
                raise serializers.ValidationError(
                    "You've already registered and verified this email. "
                    "Your account is pending admin approval — please wait to be approved before logging in."
                )
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        validated_data.pop('confirm_password')

        # DateField gives us a real `date` object — convert to string so it's JSON-safe for Redis
        validated_data['date_of_birth'] = validated_data['date_of_birth'].isoformat()

        otp = generate_otp(email)
        stash_pending_registration(email, otp, validated_data)
        send_otp_email(email, otp)

        return {'email': email}


# ---------------------------------------------------------
# Email verification (completes registration)
# ---------------------------------------------------------

class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        pending = get_pending_registration(attrs['email'])
        if pending is None:
            raise serializers.ValidationError(
                {'otp': 'Registration expired or not found. Please register again.'}
            )
        if pending['otp'] != attrs['otp']:
            raise serializers.ValidationError({'otp': 'Invalid code.'})
        attrs['pending_data'] = pending['data']
        return attrs

    def create(self, validated_data):
        data = validated_data['pending_data']
        email = validated_data['email']

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=data['first_name'],
            last_name=data['last_name'],
            password=data['password'],
            is_active=False,  # still locked until admin approves
        )

        Profile.objects.create(
            user=user,
            phone_number=data['phone_number'],
            date_of_birth=data['date_of_birth'],
        )

        clear_pending_registration(email)
        return user


# ---------------------------------------------------------
# Forgot password (request OTP)
# ---------------------------------------------------------

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email.")
        return value

    def save(self):
        email = self.validated_data['email']
        otp = generate_otp(email)
        stash_password_reset_otp(email, otp)
        send_otp_email(email, otp)
        return email


# ---------------------------------------------------------
# Reset password (submit OTP + new password)
# ---------------------------------------------------------

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})

        cached_otp = get_password_reset_otp(attrs['email'])
        if cached_otp is None:
            raise serializers.ValidationError({'otp': 'Code expired or not found. Please request a new one.'})
        if cached_otp != attrs['otp']:
            raise serializers.ValidationError({'otp': 'Invalid code.'})

        try:
            attrs['user'] = User.objects.get(email=attrs['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': 'No account found.'})

        return attrs

    def save(self):
        user = self.validated_data['user']
        user.password = make_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        clear_password_reset_otp(self.validated_data['email'])
        return user


# ---------------------------------------------------------
# Get logged-in user's profile
# ---------------------------------------------------------

class GetUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)

    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'email', 'is_active', 'phone_number', 'date_of_birth', 'passport_photo']


# ---------------------------------------------------------
# Update logged-in user's profile
# ---------------------------------------------------------

class UpdateUserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)

    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'phone_number', 'date_of_birth', 'passport_photo']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance
    

# ---------------------------------------------------------
# Superuser: list & approve pending users
# ---------------------------------------------------------

class PendingUserSerializer(serializers.ModelSerializer):
    """Read-only view of users awaiting approval, for the superuser dashboard."""
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'date_joined']


class ApproveUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        if user.is_active:
            raise serializers.ValidationError("User is already approved.")
        self.context['user'] = user
        return value

    def save(self):
        user = self.context['user']
        user.is_active = True
        user.save(update_fields=['is_active'])
        send_approval_email(user.email)
        return user
    
# ---------------------------------------------------------
# Superuser: promote a user to admin
# ---------------------------------------------------------

class PromoteAdminSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        if user.is_staff:
            raise serializers.ValidationError("User is already an admin.")
        self.context['user'] = user
        return value

    def save(self):
        user = self.context['user']
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        return user
    
class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user  # <- comes from the authenticated request, never the body

        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})

        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})

        attrs['user'] = user
        return attrs

    def save(self):
        user = self.validated_data['user']
        user.password = make_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user
    
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        try:
            self.context['token'] = RefreshToken(value)
        except TokenError:
            raise serializers.ValidationError("Invalid or expired token.")
        return value

    def save(self):
        token = self.context['token']
        token.blacklist()





class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'username'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        token['email'] = user.email
        return token

    def validate(self, attrs):
        email = attrs.get("username")
        password = attrs.get("password")
        # ... rest unchanged

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("Incorrect email or password.")

        if not user_obj.check_password(password):
            raise AuthenticationFailed("Incorrect email or password.")

        if not user_obj.is_active:
            raise AuthenticationFailed(
                "Your account has not been activated yet. Please wait for admin approval."
            )

        # credentials correct and account active — proceed with normal token generation
        return super().validate(attrs)
    
class AllUsersSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    is_staff = serializers.BooleanField(source='user.is_staff', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'is_active', 'is_staff', 'date_joined',
            'phone_number', 'date_of_birth',
        ]