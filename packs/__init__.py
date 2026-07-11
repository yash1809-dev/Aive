"""
packs/__init__.py
=================
AIVE Domain Intelligence Pack Registry.
Provides a unified interface for discovering and loading all active packs.
"""

from packs.base_pack import BasePack
from packs.edtech_pack import EdtechPack
from packs.healthcare_pack import HealthcarePack
from packs.climate_pack import ClimatePack
from packs.manufacturing_pack import ManufacturingPack

# Registry of all active intelligence packs
ACTIVE_PACKS: list[BasePack] = [
    EdtechPack(),
    HealthcarePack(),
    ClimatePack(),
    ManufacturingPack(),
]

__all__ = [
    "BasePack",
    "EdtechPack",
    "HealthcarePack",
    "ClimatePack",
    "ManufacturingPack",
    "ACTIVE_PACKS",
]
