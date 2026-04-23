# The pymfm framework
# Centralised settings — all environment-variable access lives here.
# Override any value by setting the corresponding env var or a .env file.

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    # Solver
    # Tried in order; first one that is available is used.
    solver_preference: list[str] = field(
        default_factory=lambda: list(
            filter(None, os.getenv("SOLVER_PREFERENCE", "gurobi,scip").split(","))
        )
    )

    # Location used for automatic sunset calculation (day_end fallback)
    location_name: str = field(default_factory=lambda: os.getenv("LOCATION_NAME", "Berlin"))
    location_region: str = field(default_factory=lambda: os.getenv("LOCATION_REGION", "Germany"))
    location_timezone: str = field(default_factory=lambda: os.getenv("LOCATION_TIMEZONE", "Europe/Berlin"))
    location_lat: float = field(default_factory=lambda: float(os.getenv("LOCATION_LAT", "52.52")))
    location_lon: float = field(default_factory=lambda: float(os.getenv("LOCATION_LON", "13.40")))

    # Physical constants
    seconds_per_hour: int = 3600

    # PostgreSQL / TimescaleDB
    postgres_user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "pymfm"))
    postgres_password: str = field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "password"))
    postgres_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "localhost"))
    postgres_port: int = field(default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432")))
    postgres_db: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "pymfm-meas"))

    @property
    def db_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))

    # HTTP Basic Auth
    auth_username: str = field(default_factory=lambda: os.getenv("BALANCING_USERNAME", "admin"))
    auth_password: str = field(default_factory=lambda: os.getenv("BALANCING_PASSWORD", "admin"))

settings = Settings()
