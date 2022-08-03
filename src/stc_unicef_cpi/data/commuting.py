# -*- coding: utf-8 -*-
"""Commuting.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1lxJmJVdQzPVRzOCsj4wF8bon3rzFmzig
"""

pip install h3

import numpy as np
import pandas as pd
import h3.api.numpy_int as h3



path = '/content/drive/MyDrive/DSSG (STC   UNICEF)/data'

commuting = pd.read_csv(path + '/raw/commuting/data-for-good-at-meta-commuting-zones-july-2021.csv')
nga_clean = pd.read_csv(path + '/clean/training_data/nga_clean_v1.csv')

print(commuting.shape)
commuting.head(2)

"""# Visualization for Nigeria"""

commuting_nga = commuting[commuting['country']=='Nigeria']
commuting_nga.shape

# pip install keplergl

import keplergl
import geopandas as gpd
from shapely.geometry import Polygon

# This is needed for visualization in colab
from google.colab import output
output.enable_custom_widget_manager()

# Create the map
kepler_map = keplergl.KeplerGl(height=400)

# Add data on the map
# kepler_map.add_data(data=gpd.GeoDataFrame(commuting_nga), name="Commuting Nigeria")
kepler_map.add_data(data=commuting_nga, name="Commuting Nigeria")

kepler_map

"""# Extract data"""

import shapely.wkt

from shapely import geometry
from shapely.geometry import Polygon

def cover_polygon_h3(polygon: Polygon, resolution: int):
    '''
    Return the set of H3 cells at the specified resolution which centroids belong to the input polygon.
    https://github.com/uber/h3/issues/275
    '''
    result_set = set()
    # Hexes for vertices
    vertex_hexes = [h3.geo_to_h3(t[1], t[0], resolution) for t in list(polygon.exterior.coords)]

    ## Uncommenting this part I would get
    # Hexes for edges (inclusive of vertices)
    # for i in range(len(vertex_hexes)-1):
    #     result_set.update(h3.h3_line(vertex_hexes[i], vertex_hexes[i+1]))

    # Hexes for internal area
    result_set.update(list(h3.polyfill(geometry.mapping(polygon), resolution, geo_json_conformant=True)))
    return result_set

def commuting_zone(index, commuting, resolution = 7):
  '''
  Return dataframe with hexagon belonging to that commuting zone 
  and the other information about that commuting zone
  '''

  geom = shapely.wkt.loads(commuting.loc[index]['geometry'])

  # Handle difference between polygon and multipolygon
  if geom.geom_type == 'MultiPolygon':
    # Create a list of polygons included in multipolygon
    list_polygons = list(geom.geoms)
  elif geom.geom_type == 'Polygon':
    list_polygons = [geom]
  else:
    raise IOError('Shape is not a polygon.')

  # Set of hexagons covering that area
  set_hex = set()
  for polygon in list_polygons:
    set_hex = set_hex.union(cover_polygon_h3(polygon, resolution = resolution))

  # Create a Dataframe
  df = pd.DataFrame(set_hex)
  df.rename(columns = {0:'hex_code'}, inplace=True)

  # Add information about commuting zone
  df['name_commuting_zone'] = commuting.loc[index]['name']
  df['population_commuting'] = commuting.loc[index]['win_population']
  df['road_len_commuting'] = commuting.loc[index]['win_roads_km']
  df['area_commuting'] = commuting.loc[index]['area']

  return df

def extract_commuting(data, communting, country, resolution = 7):
  '''Extract and merge commuting zone of a specific country
  data - data to aggregate with hex code information
  commuting - data about commuting zones extracted from META
  country - string
  '''

  commuting_country = commuting[commuting['country']==str(country)]

  df = pd.DataFrame()
  for i in commuting_country.index:
    # Deal with Multypolygon
    temp = commuting_zone(i, commuting_country, resolution = resolution)
    df = df.append(temp)
    
  data = pd.merge(data, df, how='left', on='hex_code')

  return data

nga_clean = extract_commuting(nga_clean, commuting, 'Nigeria', resolution = 7)
nga_clean

nga_clean.to_csv('nga_clean_commuting.csv', index=False)