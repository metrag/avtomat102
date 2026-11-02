"""Чистая логика расчёта упреждения и времени полёта пули."""


def time_of_flight(distance: float, bullet_speed: float) -> float:
    """Рассчитывает время полёта пули до цели.

    Args:
        distance: Дистанция до цели в метрах.
        bullet_speed: Скорость пули в м/с.

    Returns:
        Время полёта в секундах.

    Raises:
        ValueError: Если distance < 0 или bullet_speed <= 0.

    Example:
        >>> time_of_flight(850.0, 850.0)
        1.0
    """
    if distance < 0:
        raise ValueError("Distance cannot be negative")
    if bullet_speed <= 0:
        raise ValueError("Bullet speed must be greater than zero")

    # Линейная модель: t = s / v
    return distance / bullet_speed


def lead_offset(
    velocity: tuple[float, float],
    distance: float,
    bullet_speed: float,
) -> tuple[float, float]:
    """Рассчитывает смещение прицела (упреждение) по движущейся цели.

    Args:
        velocity: Вектор скорости цели (vx, vy) в м/с.
        distance: Дистанция до цели в метрах.
        bullet_speed: Скорость пули в м/с.

    Returns:
        Кортеж (dx, dy) — смещение прицела в метрах.

    Raises:
        ValueError: Если velocity некорректен или bullet_speed <= 0.

    Example:
        >>> lead_offset((10.0, 0.0), 850.0, 850.0)
        (10.0, 0.0)
    """
    if len(velocity) != 2:
        raise ValueError("Velocity must be a 2D vector")

    flight_time = time_of_flight(distance, bullet_speed)
    vx, vy = velocity
    dx = vx * flight_time
    dy = vy * flight_time
    return (dx, dy)
