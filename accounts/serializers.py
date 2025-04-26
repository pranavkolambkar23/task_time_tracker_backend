from rest_framework import serializers
from .models import CustomUser
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'role']
        read_only_fields = ['id']  # Optionally, make the 'id' read-only

class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'password', 'role']

    def validate_email(self, value):
        """
        Ensure the email is unique and case-insensitive.
        """
        validate_email(value)  # This validates the email format
        if CustomUser.objects.filter(email=value.lower()).exists():
            raise ValidationError("This email is already registered.")
        return value.lower()  # Store email in lowercase for consistency

    def validate_username(self, value):
        """
        Ensure the username is unique.
        """
        if CustomUser.objects.filter(username=value).exists():
            raise ValidationError("This username is already taken.")
        return value

    def create(self, validated_data):
        # Create a user with hashed password
        user = CustomUser(
            email=validated_data['email'],
            username=validated_data.get('username', ''),
            role=validated_data['role']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)