"""
Script de benchmark de rendimiento para Printer_connect
Mide el rendimiento de operaciones críticas
"""

import sys
import time
import statistics
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.database.database import DatabaseManager
from shared.security.auth import AuthenticationManager
from shared.security.rate_limiter import RateLimiter
from shared.security.validation import InputValidator


def benchmark_function(func, iterations=1000, *args, **kwargs):
    """
    Mide el rendimiento de una función

    Args:
        func: Función a medir
        iterations: Número de iteraciones
        *args, **kwargs: Argumentos para la función

    Returns:
        Dictionary con estadísticas
    """
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convertir a ms

    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'min': min(times),
        'max': max(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0
    }


def main():
    """Función principal"""
    print("=" * 60)
    print(" Printer_connect - Performance Benchmark")
    print("=" * 60)
    print()

    # 1. Database Operations
    print("[1/4] Benchmark de operaciones de base de datos...")
    db_manager = DatabaseManager('sqlite:///:memory:')

    # Create user
    password_hash, password_salt = AuthenticationManager.hash_password('test_password')
    stats = benchmark_function(
        db_manager.create_user,
        iterations=100,
        username=f'user_{time.time()}',
        password_hash=password_hash,
        password_salt=password_salt.hex()
    )
    print(f"  create_user: {stats['mean']:.2f}ms (median: {stats['median']:.2f}ms)")

    # 2. Authentication
    print("\n[2/4] Benchmark de autenticación...")
    auth_manager = AuthenticationManager(secret_key='test_key')

    # Token generation
    stats = benchmark_function(
        auth_manager.generate_token,
        iterations=1000,
        client_id='test_client',
        username='test_user'
    )
    print(f"  generate_token: {stats['mean']:.3f}ms (median: {stats['median']:.3f}ms)")

    # Token validation
    token = auth_manager.generate_token('test_client', 'test_user')
    stats = benchmark_function(
        auth_manager.validate_token,
        iterations=1000,
        token=token
    )
    print(f"  validate_token: {stats['mean']:.3f}ms (median: {stats['median']:.3f}ms)")

    # Password hashing
    stats = benchmark_function(
        AuthenticationManager.hash_password,
        iterations=100,
        password='test_password'
    )
    print(f"  hash_password: {stats['mean']:.2f}ms (median: {stats['median']:.2f}ms)")

    # 3. Rate Limiting
    print("\n[3/4] Benchmark de rate limiting...")
    rate_limiter = RateLimiter(requests_per_minute=60000, burst_size=1000)

    stats = benchmark_function(
        rate_limiter.check_rate_limit,
        iterations=1000,
        client_id='test_client',
        raise_on_limit=False
    )
    print(f"  check_rate_limit: {stats['mean']:.3f}ms (median: {stats['median']:.3f}ms)")

    # 4. Input Validation
    print("\n[4/4] Benchmark de validación...")
    validator = InputValidator()

    stats = benchmark_function(
        validator.validate_client_id,
        iterations=1000,
        client_id='test_client_123'
    )
    print(f"  validate_client_id: {stats['mean']:.3f}ms (median: {stats['median']:.3f}ms)")

    stats = benchmark_function(
        validator.validate_username,
        iterations=1000,
        username='test_user'
    )
    print(f"  validate_username: {stats['mean']:.3f}ms (median: {stats['median']:.3f}ms)")

    # Resumen
    print("\n" + "=" * 60)
    print(" Benchmark Completado")
    print("=" * 60)
    print()
    print("Recomendaciones:")
    print("  - Las operaciones de DB deben ser < 10ms en promedio")
    print("  - La validación de tokens debe ser < 1ms")
    print("  - El rate limiting debe ser < 0.1ms")
    print()
    print("Nota: Los tiempos pueden variar según el hardware")


if __name__ == '__main__':
    main()
