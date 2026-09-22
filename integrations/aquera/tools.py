from __future__ import annotations

from typing import Any, Dict, List, Optional

from .client import AqueraClient
from .auth import enforce_permission
from .models import UserContext, HarvestCreate


class AqueraTools:
    """Aquera Tools orchestrator for Hermes Agent.
    
    Translates Aquera API capabilities into function tools for Hermes.
    Guarantees:
    - Pre-execution RBAC enforcement (server-side, never trusting LLM decisions)
    - Input validation on mutations before hitting the backend
    - Accurate endpoint mappings to Aquera App Router API (/api/v1/*)
    """

    def __init__(self, client: AqueraClient):
        self.client = client

    # -------------------------------------------------------------------------
    # Health Check (Phase 1)
    # -------------------------------------------------------------------------
    async def get_health(self) -> Dict[str, Any]:
        """Check Aquera API service and database connectivity health."""
        return await self.client.request("GET", "/api/v1/health")

    # -------------------------------------------------------------------------
    # Organization & Members (Phase 2 & 3)
    # -------------------------------------------------------------------------
    async def get_organization(self, context: UserContext) -> Dict[str, Any]:
        """Retrieve details of the active organization."""
        enforce_permission(context, "organization.read")
        return await self.client.request(
            "GET",
            "/api/v1/organization",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id},
        )

    async def get_members(self, context: UserContext) -> Dict[str, Any]:
        """Retrieve team members and pending invites for the organization."""
        enforce_permission(context, "team.read")
        return await self.client.request(
            "GET",
            "/api/v1/team",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id},
        )

    async def get_user_context(self, context: UserContext) -> Dict[str, Any]:
        """Retrieve authenticated profile, organization, and role details."""
        return await self.client.request(
            "GET",
            "/api/v1/user-context",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id, "user_id": context.user_id or ""},
        )

    # -------------------------------------------------------------------------
    # Ponds (Phase 4)
    # -------------------------------------------------------------------------
    async def get_ponds(self, context: UserContext) -> Dict[str, Any]:
        """Retrieve list of all shrimp ponds for the organization."""
        enforce_permission(context, "pond.read")
        return await self.client.request(
            "GET",
            "/api/v1/ponds",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id},
        )

    async def create_pond(
        self,
        context: UserContext,
        code: str,
        site_id: str,
        name: Optional[str] = None,
        pond_type: str = "hdpe",
        area_m2: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a new pond in a specified farm site."""
        enforce_permission(context, "pond.create")
        if not code or not site_id:
            raise ValueError("Fields 'code' and 'site_id' are required")

        payload = {
            "code": code,
            "site_id": site_id,
            "name": name or code,
            "pond_type": pond_type,
            "area_m2": area_m2,
        }
        return await self.client.request(
            "POST",
            "/api/v1/ponds",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id},
            json_data=payload,
        )

    # -------------------------------------------------------------------------
    # Cycles (Phase 5)
    # -------------------------------------------------------------------------
    async def get_cycles(
        self,
        context: UserContext,
        pond_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve cultivation cycles for ponds."""
        enforce_permission(context, "cycle.read")
        params: Dict[str, Any] = {"cid": context.organization_id}
        if pond_id:
            params["pond_id"] = pond_id

        return await self.client.request(
            "GET",
            "/api/v1/cycles",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params=params,
        )

    async def create_cycle(
        self,
        context: UserContext,
        pond_id: str,
        cycle_no: int,
        target_harvest_date: Optional[str] = None,
        initial_count: Optional[int] = None,
        target_size: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Start or register a new cultivation cycle."""
        enforce_permission(context, "cycle.create")
        if not pond_id or cycle_no is None:
            raise ValueError("Fields 'pond_id' and 'cycle_no' are required")

        payload = {
            "pond_id": pond_id,
            "cycle_no": cycle_no,
            "target_harvest_date": target_harvest_date,
            "initial_count": initial_count,
            "target_size": target_size,
        }
        return await self.client.request(
            "POST",
            "/api/v1/cycles",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id},
            json_data=payload,
        )

    # -------------------------------------------------------------------------
    # Sampling (Phase 6)
    # -------------------------------------------------------------------------
    async def get_samplings(
        self,
        context: UserContext,
        cycle_id: Optional[str] = None,
        pond_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve sampling records (ABW, ADG, SR, water quality)."""
        enforce_permission(context, "sampling.read")
        params: Dict[str, Any] = {"cid": context.organization_id}
        if cycle_id:
            params["cycle_id"] = cycle_id
        if pond_id:
            params["pond_id"] = pond_id

        return await self.client.request(
            "GET",
            "/api/v1/sampling",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params=params,
        )

    async def create_sampling(
        self,
        context: UserContext,
        pond_id: str,
        cycle_id: str,
        sample_date: str,
        doc: Optional[int] = None,
        abw_g: Optional[float] = None,
        adg_g: Optional[float] = None,
        sr_percent: Optional[float] = None,
        ph: Optional[float] = None,
        do_ppm: Optional[float] = None,
        temp_c: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Log a new shrimp growth or water quality sampling."""
        enforce_permission(context, "sampling.create")
        if not pond_id or not cycle_id or not sample_date:
            raise ValueError("pond_id, cycle_id, and sample_date are required")

        payload = {
            "pond_id": pond_id,
            "cycle_id": cycle_id,
            "sample_date": sample_date,
            "doc": doc,
            "abw_g": abw_g,
            "adg_g": adg_g,
            "sr_percent": sr_percent,
            "ph": ph,
            "do_ppm": do_ppm,
            "temp_c": temp_c,
        }
        return await self.client.request(
            "POST",
            "/api/v1/sampling",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id},
            json_data=payload,
        )

    # -------------------------------------------------------------------------
    # Harvest (Phase 7 & Phase 9 Mutation)
    # -------------------------------------------------------------------------
    async def get_harvests(
        self,
        context: UserContext,
        pond_id: Optional[str] = None,
        cycle_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve harvest records and biomass data."""
        enforce_permission(context, "harvest.read")
        params: Dict[str, Any] = {"cid": context.organization_id}
        if pond_id:
            params["pond_id"] = pond_id
        if cycle_id:
            params["cycle_id"] = cycle_id

        return await self.client.request(
            "GET",
            "/api/v1/harvest",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params=params,
        )

    async def create_harvest(
        self,
        context: UserContext,
        harvest_data: HarvestCreate,
    ) -> Dict[str, Any]:
        """Record a new harvest (partial or total).
        
        Validates business rules prior to executing the backend request:
        - RBAC authorization check (harvest.create)
        - biomass > 0
        - price_per_kg >= 0
        """
        enforce_permission(context, "harvest.create")
        harvest_data.validate()

        payload = {
            "pond_id": harvest_data.pond_id,
            "cycle_id": harvest_data.cycle_id,
            "harvest_type": harvest_data.harvest_type,
            "total_biomass": harvest_data.total_biomass,
            "total_price": harvest_data.total_price,
            "size_count": harvest_data.size_count,
            "notes": harvest_data.notes,
        }
        return await self.client.request(
            "POST",
            "/api/v1/harvest",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id},
            json_data=payload,
        )

    # -------------------------------------------------------------------------
    # Reports & Summary (Phase 8)
    # -------------------------------------------------------------------------
    async def get_summary(self, context: UserContext) -> Dict[str, Any]:
        """Retrieve high-level farm operational metrics summary."""
        enforce_permission(context, "report.read")
        return await self.client.request(
            "GET",
            "/api/v1/summary",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params={"cid": context.organization_id},
        )

    async def get_report(
        self,
        context: UserContext,
        cycle_id: Optional[str] = None,
        pond_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve comprehensive operational and financial report."""
        enforce_permission(context, "report.read")
        params: Dict[str, Any] = {"cid": context.organization_id}
        if cycle_id:
            params["cycle_id"] = cycle_id
        if pond_id:
            params["pond_id"] = pond_id

        return await self.client.request(
            "GET",
            "/api/v1/reports",
            organization_id=context.organization_id,
            user_id=context.user_id,
            params=params,
        )
