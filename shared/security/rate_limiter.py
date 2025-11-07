"""
Rate limiter para prevenir abuso y ataques DoS
Implementa algoritmo de token bucket
"""

import time
import logging
import threading
from typing import Optional, Dict
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class RateLimitExceeded(Exception):
    """Excepción cuando se excede el rate limit"""
    pass


@dataclass
class TokenBucket:
    """
    Implementación de Token Bucket para rate limiting
    """
    capacity: int  # Capacidad máxima del bucket
    refill_rate: float  # Tokens por segundo
    tokens: float = field(init=False)  # Tokens actuales
    last_refill: float = field(init=False)  # Última recarga

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def _refill(self):
        """Recarga tokens basado en el tiempo transcurrido"""
        now = time.time()
        elapsed = now - self.last_refill

        # Agregar tokens basado en el tiempo transcurrido
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Intenta consumir tokens

        Args:
            tokens: Número de tokens a consumir

        Returns:
            True si se pudieron consumir, False si no hay suficientes
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_available_tokens(self) -> int:
        """Retorna el número de tokens disponibles"""
        self._refill()
        return int(self.tokens)

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Calcula cuánto tiempo hay que esperar para tener suficientes tokens

        Args:
            tokens: Tokens necesarios

        Returns:
            Segundos a esperar
        """
        self._refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiter:
    """
    Rate limiter con múltiples buckets por cliente
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: Optional[int] = None,
        cleanup_interval: int = 300,  # 5 minutos
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el rate limiter

        Args:
            requests_per_minute: Requests permitidos por minuto
            burst_size: Tamaño del burst (capacidad del bucket)
            cleanup_interval: Intervalo de limpieza de buckets inactivos (segundos)
            logger: Logger para mensajes
        """
        self.logger = logger or logging.getLogger(__name__)

        # Calcular parámetros del bucket
        self.requests_per_minute = requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # Tokens por segundo

        # Burst size por defecto es el doble de requests por minuto
        self.burst_size = burst_size or (requests_per_minute * 2)

        # Buckets por cliente
        self.buckets: Dict[str, TokenBucket] = {}
        self.bucket_lock = threading.RLock()

        # Cleanup
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()

        self.logger.info(
            f"RateLimiter inicializado (requests_per_minute={requests_per_minute}, "
            f"burst_size={self.burst_size})"
        )

    def _get_bucket(self, client_id: str) -> TokenBucket:
        """
        Obtiene o crea un bucket para un cliente

        Args:
            client_id: ID del cliente

        Returns:
            TokenBucket del cliente
        """
        with self.bucket_lock:
            if client_id not in self.buckets:
                self.buckets[client_id] = TokenBucket(
                    capacity=self.burst_size,
                    refill_rate=self.refill_rate
                )

            return self.buckets[client_id]

    def check_rate_limit(
        self,
        client_id: str,
        cost: int = 1,
        raise_on_limit: bool = True
    ) -> bool:
        """
        Verifica si un cliente puede hacer una request

        Args:
            client_id: ID del cliente
            cost: Costo en tokens de la request
            raise_on_limit: Lanzar excepción si se excede el límite

        Returns:
            True si puede hacer la request, False si no

        Raises:
            RateLimitExceeded: Si se excede el límite y raise_on_limit=True
        """
        bucket = self._get_bucket(client_id)

        if bucket.consume(cost):
            return True

        # Rate limit excedido
        if raise_on_limit:
            wait_time = bucket.get_wait_time(cost)
            self.logger.warning(
                f"Rate limit excedido para client_id='{client_id}' "
                f"(espera {wait_time:.1f}s)"
            )
            raise RateLimitExceeded(
                f"Rate limit excedido. Espera {wait_time:.1f} segundos."
            )

        return False

    def get_remaining_requests(self, client_id: str) -> int:
        """
        Obtiene el número de requests restantes para un cliente

        Args:
            client_id: ID del cliente

        Returns:
            Número de requests disponibles
        """
        bucket = self._get_bucket(client_id)
        return bucket.get_available_tokens()

    def get_wait_time(self, client_id: str, cost: int = 1) -> float:
        """
        Obtiene el tiempo de espera necesario para un cliente

        Args:
            client_id: ID del cliente
            cost: Costo en tokens

        Returns:
            Segundos a esperar
        """
        bucket = self._get_bucket(client_id)
        return bucket.get_wait_time(cost)

    def reset_client(self, client_id: str):
        """
        Resetea el rate limit de un cliente

        Args:
            client_id: ID del cliente
        """
        with self.bucket_lock:
            if client_id in self.buckets:
                del self.buckets[client_id]
                self.logger.info(f"Rate limit reseteado para client_id='{client_id}'")

    def cleanup_inactive_buckets(self, max_age_seconds: int = 600):
        """
        Limpia buckets inactivos

        Args:
            max_age_seconds: Edad máxima de un bucket inactivo
        """
        now = time.time()

        # Solo limpiar si ha pasado suficiente tiempo
        if now - self.last_cleanup < self.cleanup_interval:
            return

        with self.bucket_lock:
            inactive_clients = []

            for client_id, bucket in self.buckets.items():
                age = now - bucket.last_refill

                if age > max_age_seconds:
                    inactive_clients.append(client_id)

            # Eliminar buckets inactivos
            for client_id in inactive_clients:
                del self.buckets[client_id]

            if inactive_clients:
                self.logger.info(
                    f"Limpiados {len(inactive_clients)} buckets inactivos"
                )

            self.last_cleanup = now

    def get_stats(self) -> Dict[str, any]:
        """
        Obtiene estadísticas del rate limiter

        Returns:
            Dictionary con estadísticas
        """
        with self.bucket_lock:
            active_buckets = len(self.buckets)

            total_tokens = sum(
                bucket.get_available_tokens()
                for bucket in self.buckets.values()
            )

            avg_tokens = total_tokens / active_buckets if active_buckets > 0 else 0

            return {
                'active_clients': active_buckets,
                'requests_per_minute': self.requests_per_minute,
                'burst_size': self.burst_size,
                'total_available_tokens': total_tokens,
                'avg_tokens_per_client': avg_tokens
            }


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter adaptativo que ajusta los límites basado en la carga del sistema
    """

    def __init__(
        self,
        base_requests_per_minute: int = 60,
        min_requests_per_minute: int = 10,
        max_requests_per_minute: int = 120,
        **kwargs
    ):
        """
        Inicializa el rate limiter adaptativo

        Args:
            base_requests_per_minute: Requests base por minuto
            min_requests_per_minute: Mínimo requests por minuto
            max_requests_per_minute: Máximo requests por minuto
            **kwargs: Argumentos adicionales para RateLimiter
        """
        super().__init__(requests_per_minute=base_requests_per_minute, **kwargs)

        self.base_rpm = base_requests_per_minute
        self.min_rpm = min_requests_per_minute
        self.max_rpm = max_requests_per_minute

        self.logger.info(
            f"AdaptiveRateLimiter inicializado "
            f"(base={base_requests_per_minute}, "
            f"min={min_requests_per_minute}, "
            f"max={max_requests_per_minute})"
        )

    def adjust_rate(self, system_load: float):
        """
        Ajusta el rate basado en la carga del sistema

        Args:
            system_load: Carga del sistema (0.0 - 1.0)
        """
        # Calcular nuevo rate
        # Si carga es baja (0.0), permitir más requests
        # Si carga es alta (1.0), reducir requests
        rate_multiplier = 1.0 - system_load

        new_rpm = int(
            self.min_rpm +
            (self.max_rpm - self.min_rpm) * rate_multiplier
        )

        # Actualizar rate
        old_rpm = self.requests_per_minute
        self.requests_per_minute = new_rpm
        self.refill_rate = new_rpm / 60.0

        if old_rpm != new_rpm:
            self.logger.info(
                f"Rate ajustado: {old_rpm} → {new_rpm} RPM "
                f"(system_load={system_load:.2f})"
            )
