"""
Test end-to-end de la Fase 4: Seguridad con TLS y autenticación
"""

import sys
import time
import logging
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Verificar dependencias
try:
    from shared.security.auth import AuthenticationManager
    from shared.security.tls_wrapper import create_server_context, create_client_context
    from shared.security.validation import InputValidator
    from shared.security.rate_limiter import RateLimiter
    SECURITY_AVAILABLE = True
except ImportError as e:
    print(f"ERROR: Módulos de seguridad no disponibles: {e}")
    print("Instala las dependencias: pip install cryptography pyjwt")
    SECURITY_AVAILABLE = False


def test_certificate_generation():
    """Test 1: Generación de certificados"""
    print("\n" + "=" * 60)
    print("TEST 1: Generación de Certificados")
    print("=" * 60)

    cert_dir = Path(__file__).parent.parent / 'certs'

    # Verificar si ya existen certificados
    server_cert = cert_dir / 'server.crt'
    server_key = cert_dir / 'server.key'

    if server_cert.exists() and server_key.exists():
        print(f"✓ Certificados encontrados:")
        print(f"  - {server_cert}")
        print(f"  - {server_key}")
        return True
    else:
        print("❌ Certificados no encontrados")
        print()
        print("Genera certificados con:")
        print("  python scripts/generate_certificates.py --server")
        return False


def test_authentication_manager():
    """Test 2: Authentication Manager"""
    print("\n" + "=" * 60)
    print("TEST 2: Authentication Manager")
    print("=" * 60)

    if not SECURITY_AVAILABLE:
        print("❌ PyJWT no está disponible")
        return False

    try:
        # Crear authentication manager
        auth_manager = AuthenticationManager(
            secret_key='test_secret_key_for_phase4',
            token_expiration_hours=1
        )

        print("✓ AuthenticationManager inicializado")

        # Generar token
        token = auth_manager.generate_token(
            client_id='test_client',
            username='test_user',
            roles=['user']
        )

        print(f"✓ Token generado: {token[:50]}...")

        # Validar token
        payload = auth_manager.validate_token(token)

        print(f"✓ Token validado:")
        print(f"  - client_id: {payload['client_id']}")
        print(f"  - username: {payload['username']}")
        print(f"  - roles: {payload['roles']}")

        # Test hash de contraseña
        password = 'my_test_password'
        hash_hex, salt = AuthenticationManager.hash_password(password)

        print(f"✓ Password hasheado: {hash_hex[:50]}...")

        # Verificar contraseña
        is_valid = AuthenticationManager.verify_password(password, hash_hex, salt)

        if is_valid:
            print("✓ Verificación de contraseña correcta")
        else:
            print("❌ Verificación de contraseña falló")
            return False

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_input_validator():
    """Test 3: Input Validator"""
    print("\n" + "=" * 60)
    print("TEST 3: Input Validator")
    print("=" * 60)

    try:
        validator = InputValidator()

        print("✓ InputValidator inicializado")

        # Test validaciones exitosas
        test_cases = [
            ('client_id', 'test_client_123'),
            ('username', 'john_doe'),
            ('job_id', 'job_abc123'),
        ]

        for field, value in test_cases:
            if field == 'client_id':
                result = validator.validate_client_id(value)
            elif field == 'username':
                result = validator.validate_username(value)
            elif field == 'job_id':
                result = validator.validate_job_id(value)

            print(f"✓ {field} validado: {result}")

        # Test validaciones fallidas
        print("\nProbando validaciones que deben fallar:")

        from shared.security.validation import ValidationError

        try:
            validator.validate_client_id('client@invalid')
            print("❌ Debería haber fallado la validación")
            return False
        except ValidationError:
            print("✓ Validación fallida correctamente (caracteres inválidos)")

        try:
            validator.validate_username('ab')
            print("❌ Debería haber fallado la validación")
            return False
        except ValidationError:
            print("✓ Validación fallida correctamente (muy corto)")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiter():
    """Test 4: Rate Limiter"""
    print("\n" + "=" * 60)
    print("TEST 4: Rate Limiter")
    print("=" * 60)

    try:
        # Crear rate limiter con límites bajos para testing
        limiter = RateLimiter(
            requests_per_minute=60,
            burst_size=5
        )

        print("✓ RateLimiter inicializado (burst_size=5)")

        # Hacer requests hasta agotar el burst
        client_id = 'test_client'

        for i in range(5):
            can_proceed = limiter.check_rate_limit(client_id, raise_on_limit=False)
            if can_proceed:
                print(f"✓ Request {i+1}/5 permitida")
            else:
                print(f"❌ Request {i+1}/5 bloqueada (no debería)")
                return False

        # La siguiente debería fallar
        print("\nProbando request #6 (debería fallar):")
        can_proceed = limiter.check_rate_limit(client_id, raise_on_limit=False)

        if not can_proceed:
            print("✓ Request bloqueada correctamente (burst agotado)")
        else:
            print("❌ Request permitida (no debería)")
            return False

        # Verificar que otros clientes no se ven afectados
        other_client = 'other_client'
        can_proceed = limiter.check_rate_limit(other_client, raise_on_limit=False)

        if can_proceed:
            print("✓ Otro cliente puede hacer requests (rate limit por cliente)")
        else:
            print("❌ Otro cliente bloqueado (no debería)")
            return False

        # Reset
        limiter.reset_client(client_id)
        can_proceed = limiter.check_rate_limit(client_id, raise_on_limit=False)

        if can_proceed:
            print("✓ Cliente reseteado correctamente")
        else:
            print("❌ Cliente aún bloqueado después del reset")
            return False

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tls_context():
    """Test 5: TLS Context Creation"""
    print("\n" + "=" * 60)
    print("TEST 5: TLS Context Creation")
    print("=" * 60)

    cert_dir = Path(__file__).parent.parent / 'certs'
    server_cert = cert_dir / 'server.crt'
    server_key = cert_dir / 'server.key'

    if not server_cert.exists() or not server_key.exists():
        print("⚠️  Certificados no encontrados, saltando test")
        return True

    try:
        # Crear contexto de servidor
        server_context = create_server_context(
            certfile=server_cert,
            keyfile=server_key,
            require_client_cert=False
        )

        print("✓ Contexto TLS de servidor creado")
        print(f"  - Protocolo mínimo: TLS 1.2")
        print(f"  - Certificado: {server_cert}")

        # Crear contexto de cliente
        client_context = create_client_context(
            cafile=server_cert,  # Usar el cert del servidor como CA (autofirmado)
            verify_server=False  # Para testing con cert autofirmado
        )

        print("✓ Contexto TLS de cliente creado")
        print(f"  - Verificación: Deshabilitada (testing)")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal"""
    print("=" * 60)
    print(" PRINTER_CONNECT - TEST FASE 4 (SEGURIDAD)")
    print(" Versión 0.4.0")
    print("=" * 60)

    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,  # Solo warnings y errores
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Ejecutar tests
    tests = [
        ("Certificados", test_certificate_generation),
        ("Authentication Manager", test_authentication_manager),
        ("Input Validator", test_input_validator),
        ("Rate Limiter", test_rate_limiter),
        ("TLS Context", test_tls_context),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error ejecutando test '{name}': {e}")
            results.append((name, False))

    # Resumen
    print("\n" + "=" * 60)
    print(" RESUMEN DE TESTS")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Total: {passed}/{total} tests pasados")

    if passed == total:
        print()
        print("🎉 ¡Todos los tests de Fase 4 pasaron!")
        print()
        print("Próximos pasos:")
        print("1. Genera certificados si no lo has hecho:")
        print("   python scripts/generate_certificates.py --server")
        print()
        print("2. Inicia el servidor seguro:")
        print("   python server/main_v4.py")
        print()
        print("3. Los clientes necesitarán tokens JWT para autenticarse")
        print("   El servidor genera un token de ejemplo al iniciar")
        return 0
    else:
        print()
        print("❌ Algunos tests fallaron. Revisa los errores arriba.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
