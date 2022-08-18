from pathlib import Path
from shapely.geometry import Polygon
import pandas as pd
import geopandas as gpd
import swifter
import numpy as np
import h3.api.numpy_int as h3
from pyquadkey2 import quadkey as qk
from stc_unicef_cpi.utils import geospatial as geo

base_dir = Path(...)
rwi_path = base_dir / "NGA_relative_wealth_index.csv"
rwi_df = pd.read_csv(rwi_path)

nga_hexes = geo.get_hexes_for_ctry("Nigeria", 7)
nga_hexes = pd.DataFrame(nga_hexes, columns=["hex_code"])
nga_hexes["hex_poly"] = nga_hexes.hex_code.swifter.apply(
    lambda hhex: Polygon(h3.h3_to_geo_boundary(hhex))
)

# qk.to_geo() also returns in lat long order, so should be consistent
top_left = qk.TileAnchor.ANCHOR_NW
top_right = qk.TileAnchor.ANCHOR_NE
bottom_right = qk.TileAnchor.ANCHOR_SE
bottom_left = qk.TileAnchor.ANCHOR_SW


def qk_to_poly(qkey):
    square = [
        qk.from_str(str(qkey)).to_geo(anchor=point)
        for point in [top_left, top_right, bottom_right, bottom_left]
    ]
    return Polygon(square)


rwi_df["qk_poly"] = rwi_df.quadkey.apply(qk_to_poly)
rwi_gdf = gpd.GeoDataFrame(rwi_df, geometry="qk_poly")
hex_gdf = gpd.GeoDataFrame(nga_hexes, geometry="hex_poly")

joined = hex_gdf.sjoin(rwi_gdf)
joined["qk_poly"] = joined.quadkey.apply(qk_to_poly)

joined["pc_area"] = (
    joined["hex_poly"].intersection(gpd.GeoSeries(joined["qk_poly"])).area
    / joined["hex_poly"].area
)
joined["weighted_rwi"] = joined["pc_area"] * joined["rwi"]

new_rwi_df = joined.groupby("hex_code", as_index=False).agg(
    {"rwi": "mean", "error": "mean", "weighted_rwi": "sum"}
)
new_rwi_df.to_csv("../data/validation/nga_rwi_hex.csv", index=False)

