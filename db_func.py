import os
import json
import pandas as pd
import geopandas as gp
from shapely import Point
import sqlalchemy as alch
import numpy as np
from matplotlib.patches import Ellipse
from shapely.geometry import Polygon,shape 
import geopandas as gp
from datetime import datetime
from sshtunnel import SSHTunnelForwarder
import psycopg2
import pyproj
from shapely.ops import transform

def convertCoordinates(polygon):
    transformer = pyproj.Transformer.from_proj(pyproj.Proj(init='epsg:4326'), pyproj.Proj(init='epsg:27700'), always_xy = True)
    projected = transform(transformer.transform, polygon)
    return projected


cloud = os.environ.get('DBCON')
print('Cloud DB:',cloud)
class dbexe:
    def __init__(self):
        if cloud:
            self.PORT=5432
            self.DATABASE =  os.environ.get('DATABASE')
            self.DB_USERNAME =  os.environ.get('DB_USERNAME')
            self.DB_PWD =  os.environ.get('DB_PWD')
            self.DB_ADDRESS =  os.environ.get('DB_ADDRESS')
            self.connection_string = 'postgresql://{user}:{pwd}@{host}:{port}/{dbname}'.format(user = self.DB_USERNAME,pwd = self.DB_PWD,host = self.DB_ADDRESS, port=self.PORT,dbname=self.DATABASE)
        else:    
            self.PORT=5432
            self.REMOTE_USERNAME =  os.environ.get('DB_USERNAME')
            self.REMOTE_PASSWORD =  os.environ.get('REMOTE_PASSWORD')
            self.REMOTE_HOST =  os.environ.get('REMOTE_HOST')
            self.REMOTE_SSH_PORT = 22
            self.DATABASE =  os.environ.get('DATABASE')
            self.DB_USERNAME =  os.environ.get('DB_USERNAME')
            self.DB_PWD =  os.environ.get('DB_PWD')
            self.DB_ADDRESS =  os.environ.get('DB_ADDRESS')

            self.server = SSHTunnelForwarder((self.REMOTE_HOST, self.REMOTE_SSH_PORT),
            ssh_username=self.REMOTE_USERNAME,
            ssh_password=self.REMOTE_PASSWORD,
            remote_bind_address=(self.DB_ADDRESS, self.PORT))
            self.server.start()
            self.connection_string = 'postgresql://{user}:{pwd}@{host}:{port}/{dbname}'.format(user = self.DB_USERNAME,pwd = self.DB_PWD,host = self.server.local_bind_host, port=self.server.local_bind_port,dbname=self.DATABASE)
 
        self.engine = alch.create_engine(self.connection_string,pool_size=20, max_overflow=0) 
        self.conn = self.engine.connect()
    
    def close_connection(self):
        self.conn.close()
        self.engine.dispose()

    def call_layer(self,name):
        print(name)
        query = "SELECT name::text,geom,uuid::text, fid::text FROM weblayers.all_layers WHERE name = '{0}'".format(name)
        layer = gp.read_postgis(query, self.conn).to_json()
        return layer
    

    def get_user_data(self,draw_geom):
        print('from_db', draw_geom)
        geom_poly = str(convertCoordinates(Polygon(draw_geom[0])))
        print(geom_poly)
        # try:
        query = f"SELECT * FROM weblayers.comm_council_v2 WHERE st_intersects(geom,ST_setSRID(ST_GeomFromText('{geom_poly}'),27700))"
        user_layer = gp.read_postgis(query, self.conn)
        # print(user_layer)

        query2 = f"SELECT * FROM weblayers.all_fcf_tree_attribs WHERE st_intersects(geom,ST_setSRID(ST_GeomFromText('{geom_poly}'),27700))"
        tree_layer = gp.read_postgis(query2, self.conn)
        # print(tree_layer)

        query3 = f"SELECT a.prob, a.geom, st_area(a.geom) AS area FROM weblayers.flood_water_extent a, (SELECT * FROM weblayers.comm_council_v2 WHERE st_intersects(geom,ST_setSRID(ST_GeomFromText('{geom_poly}'),27700))) b\
                    WHERE st_intersects(st_setSRID(b.geom,27700), a.geom);"
        flood_layer = gp.read_postgis(query3, self.conn)

        return tree_layer, user_layer, flood_layer.groupby(['prob'])['area'].sum().transform(lambda x: x/x.sum()).to_frame().reset_index()
        #     pass
    
    def get_localities_data(self,lat,lon):
        point = str(convertCoordinates(Point(lon,lat)))
        print('Localities', point)
        # try:
        query = f"SELECT * FROM weblayers.scott_localities_2020 WHERE st_contains(geometry,ST_setSRID(ST_GeomFromText('{point}'),27700))"
        local_layer = gp.read_postgis(query, self.conn, geom_col='geometry')
        print(local_layer)

        query2 = f"SELECT a.label,a.tree_area,a.landparcel, a.geom FROM weblayers.all_fcf_tree_attribs a, (SELECT * FROM weblayers.scott_localities_2020 WHERE st_contains(geometry,ST_setSRID(ST_GeomFromText('{point}'),27700))) b WHERE st_intersects(st_setSRID(b.geometry,27700), a.geom);"

        # query2 = f"SELECT * FROM weblayers.all_fcf_tree_attribs WHERE cc_id = '{cc_layer['id'].values[0]}'"
        tree_layer = gp.read_postgis(query2, self.conn)

        query3 = f"SELECT a.prob, a.geom, st_area(a.geom) AS area FROM weblayers.flood_water_extent a, (SELECT * FROM weblayers.comm_council_v2 WHERE st_contains(geom,ST_setSRID(ST_GeomFromText('{point}'),27700))) b\
                    WHERE st_intersects(st_setSRID(b.geom,27700), a.geom);"
        flood_layer = gp.read_postgis(query3, self.conn)

        return tree_layer, local_layer, flood_layer.groupby(['prob'])['area'].sum().transform(lambda x: x/x.sum()).to_frame().reset_index()
        # except:
        #     pass
    
    def get_council_data(self,lat,lon):
        point = str(convertCoordinates(Point(lon,lat)))
        try:
            query = f"SELECT * FROM weblayers.comm_council_v2 WHERE st_contains(geom,ST_setSRID(ST_GeomFromText('{point}'),27700))"
            cc_layer = gp.read_postgis(query, self.conn)
            print(cc_layer['id'].values[0])

            query2 = f"SELECT * FROM weblayers.all_fcf_tree_attribs WHERE cc_id = '{cc_layer['id'].values[0]}'"
            tree_layer = gp.read_postgis(query2, self.conn)

            query3 = f"SELECT a.prob, a.geom, st_area(a.geom) AS area FROM weblayers.flood_water_extent a, (SELECT * FROM weblayers.comm_council_v2 WHERE st_contains(geom,ST_setSRID(ST_GeomFromText('{point}'),27700))) b\
                    WHERE st_intersects(st_setSRID(b.geom,27700), a.geom);"
            flood_layer = gp.read_postgis(query3, self.conn)

            return tree_layer, cc_layer, flood_layer.groupby(['prob'])['area'].sum().transform(lambda x: x/x.sum()).to_frame().reset_index()
        except:
            pass
    
    def get_simd_data(self,lat,lon):
        # try:
        query = f"SELECT * FROM weblayers.simd_v2 WHERE st_contains(geom,st_setSRID(st_MakePoint({lon},{lat}),4326))"
        simd_layer = gp.read_postgis(query, self.conn)
        print(simd_layer['fid'].values[0])
    
        query2 = f"SELECT * FROM weblayers.all_fcf_tree_attribs WHERE simd_id = '{simd_layer['fid'].values[0]}'"
        tree_layer = gp.read_postgis(query2, self.conn)
       
        query3 = f"SELECT a.prob, a.geom,st_area(a.geom) AS area FROM weblayers.flood_water_extent a, (SELECT * FROM weblayers.simd_v2 WHERE st_contains(geom,st_setSRID(st_MakePoint({lon},{lat}),4326))) b\
                    WHERE st_intersects(st_transform(st_setSRID(b.geom,4326),27700), a.geom);"
        flood_layer = gp.read_postgis(query3, self.conn)
            # flood_layer = flood_layer.groupby(['prob']).sum()
        print(flood_layer)
        return tree_layer, simd_layer, flood_layer.groupby(['prob'])['area'].sum().transform(lambda x: x/x.sum()).to_frame().reset_index()
        # except:
        #     pass
        
    
    def tree_layer(self, lat, lon):
        point = str(convertCoordinates(Point(lon,lat)))
        try:
            print('clicked', point)
            query = f"SELECT uuid::text, geom FROM weblayers.all_fcf_trees WHERE st_contains(geom, ST_setSRID(ST_GeomFromText('{point}'),27700));"
            tree_layer = gp.read_postgis(query, self.conn)
            print(tree_layer['uuid'].values[0])
                
            query2 = "SELECT * FROM weblayers.all_fcf_tree_attribs WHERE tree_uuid = '{0}'".format(tree_layer['uuid'].values[0])
            attr_layer = gp.read_postgis(query2, self.conn)
            return attr_layer, tree_layer
        except:
            pass
       
        
    
    def retrieve_scratch_layer(self,id):
        query = "SELECT name::text,geom,uuid::text, fid::text FROM weblayers.all_layers WHERE uuid = '{0}'".format(id)
        layer = gp.read_postgis(query, self.conn).to_json()
        return layer
    
    def get_species(self):
        query = "SELECT species FROM weblayers.tree_species"
        data = pd.read_sql(query,con=self.conn)['species'].values.tolist()
        data = json.dumps({'trees': data})
        return data

    def get_dashboard_results(self, args):
        print(args['method'])
        if args['method'] == 'id':
            for_uuid = "SELECT building_id, tree_uuid, tree_area, height_range,building_distance, risk_to_building, road_id, road_distance, risk_to_road , rail_id, rail_distance, risk_to_rail, img_path,tree_species, validated, notes, landparcel, overlaying.feature_area, overlaying.name district_layer, overlaying.fid district_name, overlaying.feature_uuid::text as district_uuid FROM (SELECT a.geom,b.* FROM (\
                SELECT *  FROM weblayers.all_layers WHERE name = 'Trees') a JOIN (SELECT * FROM weblayers.tree_attributes) b ON a.uuid = b.tree_uuid\
        ) trees JOIN (SELECT uuid feature_uuid, fid,name,area as feature_area, geom overlaying_geom FROM weblayers.all_layers WHERE uuid = '{uuid_0}') overlaying ON \
            st_intersects(overlaying.overlaying_geom,trees.geom)".format(uuid_0 = args['id'])
            query = for_uuid
            # print(query)
        
        if args['method'] == 'geometry':
            for_geometry = "SELECT building_id, tree_uuid, tree_area, height_range,building_distance, risk_to_building, road_id, road_distance, risk_to_road , rail_id, rail_distance, risk_to_rail, img_path,tree_species, validated, notes, landparcel, area feature_area, 'Region of interest' as district_layer, 'Region of interest' district_name,  null district_uuid FROM \
                (SELECT a.*,b.* FROM (\
	            SELECT uuid, fid, name, st_area(st_transform(st_SETSRID(ST_GeomFromGeoJSON('{geom}'),4326),27700)) area \
	            FROM weblayers.all_layers a WHERE name = 'Trees' AND st_intersects(st_SETSRID(ST_GeomFromGeoJSON('{geom}'),4326),a.geom)) a \
                JOIN (SELECT * FROM weblayers.tree_attributes) b ON a.uuid = b.tree_uuid) trees".format(geom = args['geometry'])
            query = for_geometry
        
        print(query)
        
        layer = pd.read_sql(query, self.conn)
        
        tots = layer.shape[0]
        building = layer.loc[layer['risk_to_building'] == 'high',['risk_to_building']].shape[0]
        road = layer.loc[layer['risk_to_road'] == 'high',['risk_to_road']].shape[0]
        rail = layer.loc[layer['risk_to_rail'] == 'high',['risk_to_rail']].shape[0]
        print(building)
        building = round((building/tots)*100,2)
        road = round((road/tots)*100,2)
        rail = round((rail/tots)*100,2)
        counts, breaks = np.histogram(layer['tree_area'], bins = np.arange(0,900,100))
        
        risk_barchart = {'risk': ['Buildings', 'Roads','Rail network' ],'value':[building,road,rail]}
        tree_area_stats_gauge = {'tot_tree' : tots, 'total_area_of_district_ha':round(layer['feature_area'][0]*0.0001,2),'total_tree_covered_area_ha' : round(layer['tree_area'].sum()*0.0001,2),'percentage_tree_coverage':round((layer['tree_area'].sum()/layer['feature_area'][0])*100,2)}  
        tree_size_stats = {'breaks': [int(item) for item in breaks],'counts':[int(item) for item in counts]}
        
        greenspace = layer.loc[:,['tree_uuid','landparcel']].groupby(['landparcel']).count().reset_index().rename(columns={'tree_uuid':'percentage'})
        greenspace['percentage'] = round((greenspace['percentage']/greenspace['percentage'].sum())*100,2)
        greenspace = greenspace.to_dict(orient='list')

        packet = {}
        packet['district_uuid'] = layer['district_uuid'][0]
        packet['district_name'] = layer['district_name'][0]
        packet['district_layer'] = layer['district_layer'][0]

        packet['tree_size_stats'] = tree_size_stats
        packet['risk_barchart'] = risk_barchart
        packet['tree_area_stats_gauge'] = tree_area_stats_gauge
        packet['greenspace'] = greenspace

        return packet

    def find_closest_layers(self,ext, zoomLevel, activeLayers, lat, lon,width):
        print(activeLayers)
        query = "SELECT info.*, look.action FROM (SELECT st_distance(geom,st_setSRID(st_MakePoint({0},{1}),4326))/{2} as relative_dist_edge, st_distance(centroid,st_setSRID(st_MakePoint({0},{1}),4326))/{2} as relative_dist_centroid, st_contains(geom,st_setSRID(st_MakePoint({0},{1}),4326)) as contains, a.fid as id_name ,uuid::text,st_x(centroid) x, st_y(centroid) y ,name,  geom FROM weblayers.all_layers a WHERE st_intersects(st_makeEnvelope({3},4326),a.geom) AND (a.minzoom <= {4} AND a.maxzoom >= {4}) AND (name in {5}) ORDER BY relative_dist_edge ASC LIMIT 1) info JOIN weblayers.click_lookup_table look ON info.name = look.name".format(lon,lat,width,ext, zoomLevel,activeLayers)
        print(query)
        # Return empty packet if no active layers
        if len(activeLayers) != 0:
            # take out brackets if there is data
            if len(activeLayers) == 1:
                query = query.replace(',)',')')
            # Send query
            result = gp.read_postgis(query, self.conn)
            print(result)
            if result.shape[0] > 0:
                if not result['contains'].values[0]:
                    if result['relative_dist_edge'].values[0] < 0.001:
                        # print('hit return data') 
                        hit = True
                    else:
                        hit = False
                else:
                    hit = True
            else:
                hit = False
            
            
            if hit:

                if result['action'].values[0] == 'popout':
                    packet = {'status': 1, 'uuid_0' : result['uuid'].values[0],'action':result['action'].values[0], 'id_name':result['id_name'].values[0], 'layer_name':result['name'].values[0] ,'lon' : result['x'].values[0], 'lat' : result['y'].values[0]}
                    query = "SELECT * FROM weblayers.tree_attributes WHERE tree_uuid = '{0}'".format(result['uuid'].values[0])
                    print(query)
                    data = pd.read_sql(query,con=self.conn)
                    print(data)
                    if data.shape[0] > 0:
                        data = pd.read_sql(query,con=self.conn).round(1).to_dict(orient='records')[0]
                        packet['data'] = data
                        print('attaching data')
                    else:
                        packet = {'status': 0, 'uuid_0' : 'null', 'data': 'null'}
                else:
                    packet = {'status': 1, 'uuid_0' : result['uuid'].values[0],'action':result['action'].values[0], 'id_name':result['id_name'].values[0], 'layer_name':result['name'].values[0] ,'lon' : result['x'].values[0], 'lat' : result['y'].values[0]}
            
                    

            else:
                packet = {'status': 0, 'uuid_0' : 'null', 'data': 'null'}
        else:
                packet = {'status': 0, 'uuid_0' : 'null', 'data': 'null'}
        
        return packet


    def get_picture_path(self,uuid_0):
        query = "SELECT img_path FROM weblayers.tree_attributes WHERE tree_uuid = '{0}'".format(uuid_0)
        data = pd.read_sql(query,con=self.conn).to_dict(orient='records')[0]
        return data 
    
    def update_tree_details(self,tree_height,img_path,tree_species,validated, uuid_0):
        query = "UPDATE weblayers.tree_attributes SET height_range = ARRAY[{0},{1}], img_path = '{2}', tree_species = '{3}', validated = {4} WHERE tree_uuid = '{5}'".format(tree_height[0],tree_height[1],img_path,tree_species,validated, uuid_0)
        self.conn.execute(query)

    def invalidate_tree(self,notes, uuid_0):
        notes = json.dumps(notes)
        query = "UPDATE weblayers.tree_attributes SET notes = '{0}', validated = 0 WHERE tree_uuid = '{1}'".format(notes,uuid_0)
        self.conn.execute(query)

    def add_feature_to_db(self,tree_height,img_path,tree_species,validated, uuid_0,geom):
        print(geom)

        d = {'id': [1]}
        d = pd.DataFrame(data=d)
        d['geometry'] = shape(json.loads(geom))
        
        df = gp.GeoDataFrame(d,geometry='geometry')
        centroid = df['geometry'].centroid
        ellipse_table = df.bounds
        
        ellipse_table['width'] = ellipse_table['maxx']-ellipse_table['minx']
        ellipse_table['height'] = ellipse_table['maxy']-ellipse_table['miny']
        ellipse = Ellipse((centroid.x, centroid.y), ellipse_table['width'][0], ellipse_table['height'][0], 0) 
        vertices = ellipse.get_verts()     # get the vertices from the ellipse object
        bubble = Polygon(vertices).wkt
        
        # There are triggers built into DB to calulate risk attributes 
        timestamp = datetime.now().isoformat()
        query = "INSERT INTO weblayers.all_layers (ingestion_timestamp, change_timestamp, uuid,fid,type,name,geom, centroid,area, minzoom,maxzoom)\
             VALUES ('{0}','{0}','{1}',NULL,'polygon','Trees',st_SETSRID(ST_GeomFromTEXT('{2}'),4326),st_centroid(st_SETSRID(ST_GeomFromTEXT('{2}'),4326)),st_area(st_transform(st_SETSRID(ST_GeomFromTEXT('{2}'),4326),27700)),16,27)".format(timestamp,uuid_0,bubble)
        print(query)
        self.conn.execute(query)
        # Update tree attributes table
        # sleep(1)
        query = "UPDATE weblayers.tree_attributes SET height_range = ARRAY[{0},{1}],  img_path = '{2}', tree_species = '{3}', validated = {4} WHERE tree_uuid = '{5}'".format(tree_height[0],tree_height[1],img_path,tree_species,validated, uuid_0)
        self.conn.execute(query)           


    def return_geoms(self, variable, category,geom):
            
            if variable == 'landparcel':
                query = "SELECT a.tree_uuid::text,b.geom FROM (SELECT * FROM weblayers.tree_attributes WHERE {0} = '{1}') a LEFT JOIN (SELECT uuid as tree_uuid,geom FROM weblayers.all_layers WHERE st_intersects(st_SETSRID(ST_GeomFromGeoJSON('{2}'),4326),geom)) b ON a.tree_uuid = b.tree_uuid".format(variable,category,geom)
            
            if variable == 'risk':
                if category == 'Rail network':
                    category = 'risk_to_rail'
                if category == 'Roads':
                    category = 'risk_to_road'
                if category == 'Buildings':
                    category = 'risk_to_building'
                query = "SELECT a.tree_uuid::text,b.geom FROM (SELECT * FROM weblayers.tree_attributes WHERE {0} = 'high') a LEFT JOIN (SELECT uuid as tree_uuid,geom FROM weblayers.all_layers WHERE st_intersects(st_SETSRID(ST_GeomFromGeoJSON('{1}'),4326),geom)) b ON a.tree_uuid = b.tree_uuid".format(category,geom)
            
            layer = gp.read_postgis(query, self.conn)
            return layer.to_json()
