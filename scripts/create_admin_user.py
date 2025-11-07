"""
Script para crear usuario administrador inicial
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.database.database import DatabaseManager
from shared.security.auth import AuthenticationManager


def main():
    """Función principal"""
    print("=" * 60)
    print(" Crear Usuario Administrador")
    print("=" * 60)
    print()

    # Conectar a base de datos
    db_manager = DatabaseManager('sqlite:///./data/printer_connect.db')

    # Verificar si ya existe admin
    existing = db_manager.get_user_by_username('admin')
    if existing:
        print("⚠️  El usuario 'admin' ya existe")
        print()
        response = input("¿Deseas cambiar su contraseña? (s/n): ")
        if response.lower() != 's':
            print("Operación cancelada")
            return

        # Cambiar contraseña
        password = input("Nueva contraseña: ")
        confirm = input("Confirmar contraseña: ")

        if password != confirm:
            print("❌ Las contraseñas no coinciden")
            return

        if len(password) < 6:
            print("❌ La contraseña debe tener al menos 6 caracteres")
            return

        # Hash de contraseña
        password_hash, password_salt = AuthenticationManager.hash_password(password)

        # Actualizar
        success = db_manager.update_user_password(
            user_id=existing.id,
            password_hash=password_hash,
            password_salt=password_salt.hex()
        )

        if success:
            print()
            print("✓ Contraseña actualizada exitosamente")
            print()
            print("Credenciales:")
            print(f"  Usuario: admin")
            print(f"  Contraseña: {password}")
        else:
            print("❌ Error actualizando contraseña")

        return

    # Crear nuevo usuario admin
    print("Crear nuevo usuario administrador")
    print()

    username = input("Usuario (default: admin): ").strip() or "admin"
    password = input("Contraseña: ")
    confirm = input("Confirmar contraseña: ")

    if password != confirm:
        print("❌ Las contraseñas no coinciden")
        return

    if len(password) < 6:
        print("❌ La contraseña debe tener al menos 6 caracteres")
        return

    email = input("Email (opcional): ").strip() or None
    full_name = input("Nombre completo (opcional): ").strip() or None

    # Hash de contraseña
    password_hash, password_salt = AuthenticationManager.hash_password(password)

    # Crear usuario
    user = db_manager.create_user(
        username=username,
        password_hash=password_hash,
        password_salt=password_salt.hex(),
        email=email,
        full_name=full_name,
        role='admin'
    )

    print()
    print("✓ Usuario administrador creado exitosamente")
    print()
    print("Credenciales:")
    print(f"  Usuario: {username}")
    print(f"  Contraseña: {password}")
    print(f"  Rol: admin")
    print()
    print("Puedes iniciar sesión en el dashboard web con estas credenciales")


if __name__ == '__main__':
    main()
