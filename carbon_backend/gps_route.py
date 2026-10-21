from dataclasses import dataclass
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import Iterable, Optional

from models import GpsRoutePoint

MAX_GPS_ACCURACY_METERS = 25.0
MAX_GPS_GAP_SECONDS = 30.0
MINIMUM_MOVEMENT_METERS = 5.0


@dataclass(frozen=True)
class FilteredRoutePoint:
    latitude: float
    longitude: float
    accuracy: float
    timestamp: datetime
    is_mocked: bool


def _distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    earth_radius_meters = 6_371_000.0
    delta_latitude = radians(latitude_b - latitude_a)
    delta_longitude = radians(longitude_b - longitude_a)
    lat_a = radians(latitude_a)
    lat_b = radians(latitude_b)
    haversine = (
        sin(delta_latitude / 2) ** 2
        + cos(lat_a) * cos(lat_b) * sin(delta_longitude / 2) ** 2
    )
    return 2 * earth_radius_meters * atan2(sqrt(haversine), sqrt(1 - haversine))


def filter_gps_route(
    points: Iterable[GpsRoutePoint],
    transport_mode: str,
) -> float:
    if transport_mode == "Walking":
        max_speed_meters_per_second = 3.0
        process_noise_meters_per_second = 3.0
    elif transport_mode == "Bicycle":
        max_speed_meters_per_second = 12.0
        process_noise_meters_per_second = 3.0
    else:
        max_speed_meters_per_second = 40.0
        process_noise_meters_per_second = 10.0

    previous: Optional[FilteredRoutePoint] = None
    last_timestamp: Optional[datetime] = None
    filtered_latitude: Optional[float] = None
    filtered_longitude: Optional[float] = None
    distance_anchor: Optional[FilteredRoutePoint] = None
    variance = -1.0
    total_distance_meters = 0.0

    for point in points:
        timestamp = point.timestamp
        if point.is_mocked or point.accuracy > MAX_GPS_ACCURACY_METERS:
            continue
        if last_timestamp is not None and timestamp <= last_timestamp:
            continue

        elapsed_seconds = (
            (timestamp - previous.timestamp).total_seconds()
            if previous is not None
            else None
        )
        current = FilteredRoutePoint(
            latitude=point.latitude,
            longitude=point.longitude,
            accuracy=point.accuracy,
            timestamp=timestamp,
            is_mocked=point.is_mocked,
        )

        if previous is None or (
            elapsed_seconds is not None
            and elapsed_seconds > MAX_GPS_GAP_SECONDS
        ):
            previous = current
            last_timestamp = timestamp
            filtered_latitude = point.latitude
            filtered_longitude = point.longitude
            distance_anchor = current
            variance = max(point.accuracy, 1.0) ** 2
            continue

        if elapsed_seconds is None or elapsed_seconds <= 0:
            continue

        raw_distance = _distance_meters(
            previous.latitude,
            previous.longitude,
            point.latitude,
            point.longitude,
        )
        if raw_distance / elapsed_seconds > max_speed_meters_per_second:
            continue

        measurement_accuracy = max(point.accuracy, 1.0)
        variance += elapsed_seconds * process_noise_meters_per_second**2
        measurement_variance = measurement_accuracy**2
        kalman_gain = variance / (variance + measurement_variance)
        filtered_latitude += kalman_gain * (
            point.latitude - filtered_latitude
        )
        filtered_longitude += kalman_gain * (
            point.longitude - filtered_longitude
        )
        variance = (1 - kalman_gain) * variance
        previous = current
        last_timestamp = timestamp

        distance = _distance_meters(
            distance_anchor.latitude,
            distance_anchor.longitude,
            filtered_latitude,
            filtered_longitude,
        )
        minimum_movement = max(
            MINIMUM_MOVEMENT_METERS,
            measurement_accuracy * 0.5,
        )
        if distance >= minimum_movement:
            total_distance_meters += distance
            distance_anchor = FilteredRoutePoint(
                latitude=filtered_latitude,
                longitude=filtered_longitude,
                accuracy=measurement_accuracy,
                timestamp=timestamp,
                is_mocked=False,
            )

    return total_distance_meters / 1000
