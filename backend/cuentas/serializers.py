"""Cuentas: se usa el usuario de Django. El correo es el nombre de usuario y
first_name guarda el nombre que se muestra en las reseñas ("Sofía M.").
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ErrorDeDjango
from rest_framework import serializers

Usuario = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="first_name")

    class Meta:
        model = Usuario
        fields = ["id", "nombre", "email"]


class RegistroSerializer(serializers.Serializer):
    nombre = serializers.CharField(min_length=2, max_length=60, trim_whitespace=True)
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, email):
        email = email.strip().lower()
        if Usuario.objects.filter(username=email).exists():
            raise serializers.ValidationError("Ya hay una cuenta con este correo. Inicia sesión.")
        return email

    def validate(self, datos):
        # Los validadores de Django (AUTH_PASSWORD_VALIDATORS): largo mínimo, no
        # demasiado común, no solo números, no parecida al nombre o al correo.
        usuario = Usuario(username=datos["email"], email=datos["email"], first_name=datos["nombre"])
        try:
            validate_password(datos["password"], usuario)
        except ErrorDeDjango as error:
            raise serializers.ValidationError({"password": list(error.messages)})
        return datos

    def create(self, datos):
        return Usuario.objects.create_user(
            username=datos["email"], email=datos["email"], first_name=datos["nombre"], password=datos["password"]
        )


class EntrarSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)
