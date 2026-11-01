"""Shared fixture loaders (real TKGM parcel with neighbour evidence, synthetic regression parcels)."""

from brain.catalog import ROOT, load_default_rules, load_parcel, load_zoning_params

RULES = load_default_rules()
__all__ = ["ROOT", "RULES", "load_real_parcel", "load_synthetic", "load_demo_zoning"]


def load_real_parcel():
    return load_parcel("karatay-buyuksinan-1495-26")


def load_synthetic(name: str):
    return load_parcel(name.removesuffix(".manual.json"))


def load_demo_zoning():
    return load_zoning_params("demo")
