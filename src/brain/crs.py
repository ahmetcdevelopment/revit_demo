"""WGS84 <-> local metric plane. Turkish TUREF / TM 3-degree zones (EPSG 5253..5259)."""

from __future__ import annotations

from dataclasses import dataclass

from pyproj import Transformer

ZONES = (27, 30, 33, 36, 39, 42, 45)  # central meridians, EPSG = 5253 + index


def tm_epsg_for_lon(lon: float) -> int:
    zone = min(max(round(lon / 3) * 3, ZONES[0]), ZONES[-1])
    return 5253 + (zone - ZONES[0]) // 3


@dataclass(frozen=True)
class LocalFrame:
    """Local ENU-like plane: TM projection shifted so `origin_lonlat` is (0, 0)."""

    origin_lonlat: tuple[float, float]
    epsg: int

    @classmethod
    def at(cls, origin_lonlat: tuple[float, float]) -> LocalFrame:
        return cls(origin_lonlat, tm_epsg_for_lon(origin_lonlat[0]))

    def _fwd(self) -> Transformer:
        return Transformer.from_crs(4326, self.epsg, always_xy=True)

    def _inv(self) -> Transformer:
        return Transformer.from_crs(self.epsg, 4326, always_xy=True)

    def _origin_xy(self) -> tuple[float, float]:
        return self._fwd().transform(*self.origin_lonlat)

    def to_local(self, lon: float, lat: float) -> tuple[float, float]:
        x, y = self._fwd().transform(lon, lat)
        ox, oy = self._origin_xy()
        return (x - ox, y - oy)

    def from_local(self, x: float, y: float) -> tuple[float, float]:
        ox, oy = self._origin_xy()
        return self._inv().transform(x + ox, y + oy)
