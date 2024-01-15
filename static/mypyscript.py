import geopandas as gpd
import sqlalchemy as alch

import matplotlib.pyplot as plt

conn = alch.create_engine('postgresql://josh:treecanopy123@139.153.146.92:5432/forthera')

# Get bounding boxes from database
sql = "SELECT * FROM tree_mapping.predicted_bbox"
bounding_boxes = gpd.GeoDataFrame.from_postgis(sql,conn)

sub_tile = bounding_boxes[bounding_boxes['image_path']=='NS8093']

area = sub_tile['area'].values

fig1, ax1 = plt.subplots()
ax1.hist(area)
ax1.set_title('Tree Dstribution')

fig1


