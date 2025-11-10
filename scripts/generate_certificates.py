"""
Script para generar certificados SSL/TLS autofirmados
Para uso en desarrollo y testing

Para producción, se recomienda usar certificados firmados por una CA reconocida
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("ERROR: cryptography no está instalado")
    print("Instala: pip install cryptography")
    sys.exit(1)


def generate_self_signed_cert(
    output_dir: Path,
    cert_name: str = "server",
    common_name: str = "localhost",
    organization: str = "Printer_connect",
    country: str = "ES",
    days_valid: int = 365
) -> tuple[Path, Path]:
    """
    Genera un certificado autofirmado y su clave privada

    Args:
        output_dir: Directorio donde guardar los archivos
        cert_name: Nombre base para los archivos
        common_name: Common Name (CN) del certificado
        organization: Organización
        country: Código de país (2 letras)
        days_valid: Días de validez del certificado

    Returns:
        Tupla con (ruta_certificado, ruta_clave_privada)
    """
    print(f"Generando certificado autofirmado para '{common_name}'...")

    # Generar clave privada RSA
    print("  [1/4] Generando clave privada RSA (2048 bits)...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Crear el certificado
    print("  [2/4] Creando certificado X.509...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=days_valid)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(common_name),
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    # Crear directorio de salida si no existe
    output_dir.mkdir(parents=True, exist_ok=True)

    # Guardar certificado
    cert_file = output_dir / f"{cert_name}.crt"
    print(f"  [3/4] Guardando certificado: {cert_file}")
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Guardar clave privada
    key_file = output_dir / f"{cert_name}.key"
    print(f"  [4/4] Guardando clave privada: {key_file}")
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    print(f"✓ Certificado generado exitosamente")
    print(f"  - Válido por {days_valid} días")
    print(f"  - Common Name: {common_name}")
    print()

    return cert_file, key_file


def main():
    """Función principal"""
    import argparse
    import ipaddress

    parser = argparse.ArgumentParser(
        description='Genera certificados SSL/TLS autofirmados para Printer_connect'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path(__file__).parent.parent / 'certs',
        help='Directorio de salida (default: ./certs)'
    )
    parser.add_argument(
        '--server',
        action='store_true',
        help='Generar certificado de servidor'
    )
    parser.add_argument(
        '--client',
        action='store_true',
        help='Generar certificado de cliente'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Generar certificados de servidor y cliente'
    )
    parser.add_argument(
        '--hostname',
        type=str,
        default='localhost',
        help='Hostname/IP del servidor (default: localhost)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=365,
        help='Días de validez (default: 365)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print(" Generador de Certificados SSL/TLS - Printer_connect")
    print("=" * 60)
    print()

    if not CRYPTOGRAPHY_AVAILABLE:
        print("ERROR: El módulo cryptography no está disponible")
        sys.exit(1)

    # Determinar qué certificados generar
    generate_server = args.server or args.all or (not args.server and not args.client)
    generate_client = args.client or args.all

    output_dir = args.output_dir
    print(f"Directorio de salida: {output_dir}")
    print(f"Validez: {args.days} días")
    print()

    # Generar certificado de servidor
    if generate_server:
        server_cert, server_key = generate_self_signed_cert(
            output_dir=output_dir,
            cert_name="server",
            common_name=args.hostname,
            organization="Printer_connect Server",
            days_valid=args.days
        )

    # Generar certificado de cliente
    if generate_client:
        client_cert, client_key = generate_self_signed_cert(
            output_dir=output_dir,
            cert_name="client",
            common_name="Printer_connect Client",
            organization="Printer_connect Client",
            days_valid=args.days
        )

    print("=" * 60)
    print(" Certificados generados exitosamente")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANTE: Estos son certificados autofirmados")
    print("   Solo deben usarse para desarrollo y testing.")
    print("   Para producción, usa certificados firmados por una CA reconocida.")
    print()
    print("Próximos pasos:")
    print("1. Configura server/config.ini con las rutas de los certificados")
    print("2. Configura client/config.ini con las rutas de los certificados")
    print("3. Habilita TLS en ambos archivos de configuración")
    print()


if __name__ == '__main__':
    main()
