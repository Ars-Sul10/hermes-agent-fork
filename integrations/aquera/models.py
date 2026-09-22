from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class UserContext:
    """Execution context for Hermes agent.
    Never trust identity sent by user in prompt without verification."""
    user_id: Optional[str]
    organization_id: str
    role: Optional[str] = "viewer"
    full_name: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AqueraUser:
    id: str
    organization_id: Optional[str]
    role: Optional[str]
    full_name: Optional[str] = None
    status: str = "active"


@dataclass
class FarmSite:
    id: str
    name: str
    location_text: Optional[str] = None
    is_active: bool = True


@dataclass
class Pond:
    id: str
    code: str
    site_id: str
    name: Optional[str] = None
    pond_type: Optional[str] = "hdpe"
    area_m2: Optional[float] = None
    is_active: bool = True


@dataclass
class Cycle:
    id: str
    pond_id: str
    cycle_no: int
    status: str = "planned"
    start_date: Optional[str] = None
    target_harvest_date: Optional[str] = None
    initial_count: Optional[int] = None
    target_size: Optional[float] = None


@dataclass
class Sampling:
    id: str
    pond_id: str
    cycle_id: Optional[str] = None
    sample_date: Optional[str] = None
    doc: Optional[int] = None
    abw_g: Optional[float] = None
    adg_g: Optional[float] = None
    sr_percent: Optional[float] = None
    ph: Optional[float] = None
    do_ppm: Optional[float] = None
    temp_c: Optional[float] = None


@dataclass
class HarvestCreate:
    """Payload model for creating a harvest record."""
    pond_id: str
    total_biomass: float
    cycle_id: Optional[str] = None
    harvest_type: str = "total"
    price_per_kg: Optional[float] = None
    total_price: Optional[float] = None
    size_count: Optional[float] = None
    notes: Optional[str] = None

    def validate(self) -> None:
        """Validate input before mutation."""
        if not self.pond_id:
            raise ValueError("pond_id is required")
        if self.total_biomass <= 0:
            raise ValueError("total_biomass must be greater than 0")
        if self.price_per_kg is not None and self.price_per_kg < 0:
            raise ValueError("price_per_kg cannot be negative")


@dataclass
class Harvest:
    id: str
    pond_id: str
    total_biomass: float
    harvest_type: str = "total"
    total_price: Optional[float] = None
    harvested_at: Optional[str] = None
    cycle_id: Optional[str] = None


@dataclass
class ReportSummary:
    active_cycles: int = 0
    total_cycles: int = 0
    total_biomass_harvested_kg: float = 0.0
    total_harvest_revenue: float = 0.0
    total_feed_used_kg: float = 0.0
    estimated_fcr: float = 0.0
    latest_sampling_count: int = 0
