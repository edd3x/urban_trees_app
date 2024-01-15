import leafmap.leafmap as leafmap
from pyproj import Geod
import ipyleaflet
import pandas as pd
import numpy as np
from rasterio.mask import mask
import solara.express as px
import solara
from shapely import Point, Polygon
from db_func import dbexe
import geopandas as gpd
import rasterio
import json
import pyproj
from shapely.ops import transform
import ipywidgets as widgets
import reacton.ipyvuetify as v

# geoserver_wms = "http://139.153.146.198:8080/geoserver/FORTHERA_GEO/wms"
geoserver_wms = "https://era-geoserver.azurewebsites.net/geoserver/FORTHERA_GEO/wms"
geoserver_ows = "https://era-geoserver.azurewebsites.net/geoserver/FORTHERA_GEO/ows"

zoom = solara.reactive(14.5)
center = solara.reactive((56.122495, -3.807203))
base_layer = solara.reactive("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}.png")

sim_geom = gpd.read_file('./features/simd_v2.geojson', engine='fiona')
cc_geom = gpd.read_file('./features/comm_council_v2.geojson',engine='fiona')
locals_geom = gpd.read_file('./features/scott_localities_2020.geojson',engine='fiona')

heat_map_clacks = rasterio.open('./features/HeatHazardIndex/4EI_Clacks_HeatHazard_30m_OSGB36_BNG.tif')
heat_map_falkirk = rasterio.open('./features/HeatHazardIndex/4EI_Falkirk_HeatHazard_30m_OSGB36_BNG.tif')
heat_map_stirling = rasterio.open('./features/HeatHazardIndex/4EI_Stirling_HeatHazard_30m_OSGB36_BNG.tif')

wms_url = solara.reactive(geoserver_wms)
ows_url = solara.reactive(geoserver_ows)

tree_layer = solara.reactive("FORTHERA_GEO:all_fcf_trees")

# tree_layer_stir = solara.reactive("FORTHERA_GEO:all_fcf_trees_stirling")
# tree_layer_clacks = solara.reactive("FORTHERA_GEO:all_fcf_trees_clacks")
# tree_layer_falkirk = solara.reactive("FORTHERA_GEO:all_fcf_trees_falkirk")

tree_mask_stir = solara.reactive("FORTHERA_GEO:tree_masks_stirling")
tree_mask_clacks = solara.reactive("FORTHERA_GEO:tree_masks_clackmannan")
tree_mask_falkirk = solara.reactive("FORTHERA_GEO:tree_masks_falkirk")

tree_masks = solara.reactive("FORTHERA_GEO:tree_masks")
heat_index = solara.reactive("FORTHERA_GEO:Heat_Index_Maps")

simd_bounds = solara.reactive("FORTHERA_GEO:simd_v2")
cc_bounds = solara.reactive("FORTHERA_GEO:comm_council_v2")
flood_bounds = solara.reactive("FORTHERA_GEO:flood_water_extent")

stir_rgb = solara.reactive("FORTHERA_GEO:AerialRGB")
clacks_rgb = solara.reactive("FORTHERA_GEO:Clacks_RGB")
falkirk_rgb = solara.reactive("FORTHERA_GEO:Falk_RGB")

simd_props = solara.reactive(None)
popup_point = solara.reactive(None)
draw_feats = solara.reactive(None)

sub_census_df = solara.reactive(None)
sub_council_df = solara.reactive(None)
sub_locals_df = solara.reactive(None)

show_dialog = solara.reactive(False)
show_update_dialog = solara.reactive(False)
disable_fields = solara.reactive(False)

tree_df = solara.reactive(None)
flood_agg_df = solara.reactive(None)
flood_agg_cc_df = solara.reactive(None)
called_layer_df = solara.reactive(None)
heat_layer_df = solara.reactive(None)
heat_layer_user = solara.reactive(None)

switch_msg = solara.reactive(True)
show_switch_msg = solara.reactive('None')
show_update_fields = solara.reactive('block')

tree_id = solara.reactive(None)
tree_uuid = solara.reactive(None)
tree_species = solara.reactive("Unknown")
tree_height = solara.reactive(2.0)
tree_age = solara.reactive(10)

flood_legend = solara.reactive('')
draw_features = solara.reactive(None)

sim_on = solara.reactive(False)
cc_on = solara.reactive(False)
local_on = solara.reactive(False)

geom_type = solara.reactive('cc')
geom_area = solara.reactive(None)

map_layer_state = solara.reactive(False)
show_info_dlog = solara.reactive(True)


def close_dash():
    print('close')
    sub_census_df.set(None)
    sub_council_df.set(None)
    sub_locals_df.set(None)

def no_tree_msg():
    # print(switch_msg.value)
    if switch_msg.value == False:
        show_switch_msg.set('block')
        disable_fields.set(True)
    elif switch_msg.value == True:
        show_switch_msg.set('None')
        disable_fields.set(False)

def check_active_roi(tree_layers, roi_center):
    for lay, cen in zip(tree_layers, roi_center):
        if lay.visible ==True:
            roi = lay.name
    print(roi)
    return roi

def clear_called_layer(m):
    for layer in m.layers:
        if layer.name =='Called Layer':
            layer.visible = False


def clear_legend(mod, layer):
    for obj in mod.controls:
        if (obj.has_trait('widget')): 
            if (isinstance(obj.trait_values()['widget'], widgets.widgets.widget_output.Output)):
                if len(obj.trait_values()['widget'].outputs)==0:
                    pass
                elif (layer in obj.trait_values()['widget'].outputs[0]['data']['text/plain']):
                    obj.widget.layout.display = 'none'
                    # print(obj.widget.layout)

@solara.component
def show_portal_info():
    close_btn = v.Btn(color='primary', children=['X'], small=True, min_width=0.00, rounded=True,style_='float: right')
        
    dialog = v.Dialog(class_='tree-dlog', width='750',
            v_model='dialog',overlay_opacity='0.2',
            children=[
                v.Card(style_='padding:10px', children=[close_btn, 
                    v.CardTitle(class_='headline gray lighten-2', primary_title=True,
                                children=["Welcome to the Forth Valley Tree Map Portal"]),

                    v.CardText(children=[solara.HTML(tag="div", unsafe_innerHTML="<h3>Click on the 'Show Layer' icon (<i class='fa fa-bars'></i>) in the top right corner to see the various data layers</h3>")]),
                    v.CardText(children=[solara.HTML(tag="div", unsafe_innerHTML="<h3>Check the 'Tree Map' box to see all the individual trees identified by our deep learning model</h3>")]),
                    v.CardText(children=[solara.HTML(tag="div", unsafe_innerHTML="<h3>Use the radio buttons under the tree map box to switch between the regions of interest. Information on the individual trees can seen or updated by \
                                                     clicking on a tree bubble.</h3>")]),
                    v.CardText(children=[solara.HTML(tag="div", unsafe_innerHTML="<h3>The quantity of trees and other spatial statistics for a given area within a region of interest can be accessed by adding the SIMD boundary \
                                                     layer or the Community Council boundary layer and clicking in the boundary of choice. </h3>")]),
                    v.CardText(children=[solara.HTML(tag="div", unsafe_innerHTML="<h3> Information on user defined regions can also be seen by using the drawing tools on the left side of the screen to draw a boundary over a chosen area. </h3>")])
                ]),
            ])
       
        
    def dlog_close(*args):
        print('close')
        show_info_dlog.set(False)
    v.use_event(close_btn, 'click', dlog_close)
    

@solara.component
def tree_dialog():
    try:
        df = tree_df.value
        print(df.columns)
        tree_uuid.set(df.tree_uuid.values[0])
        tree_uid = df.tree_uuid.values[0].split('-')[0]
        tree_id.set(tree_uid)
        print(tree_id)
        
        if df.building_distance.values[0] == None:
            build_dist = None
        else:
            build_dist = df.building_distance.values[0].round(2)
        print('load --1')
        close_btn = v.Btn(color='primary', children=['X'], small=True, min_width=0.00, rounded=True,style_='float: right')
        update_btn = v.Btn(color='primary', children=['Update'])
        
        dialog = v.Dialog(class_='tree-dlog', width='550',
            v_model='dialog',overlay_opacity='0.2',
            children=[
                v.Card(style_='padding:10px', children=[close_btn, 
                    v.CardTitle(class_='headline gray lighten-2', primary_title=True,
                                children=[f"{df.cc_name.values[0]} (Tree ID: {tree_uid})"]),
                    v.Img(lazy_src=df.img_path.values[0]),
                    v.CardText(children=[f"Space Occupied: {df.landparcel.values[0]}"],style_='font-size: 17px'),
                    v.CardText(children=[f"Height: {round(df.tree_height.values[0]/2,2)}"],style_='font-size: 17px'),
                    v.CardText(children=[f"Crown Size: {round(df.tree_area.values[0]/10000,2)}"],style_='font-size: 17px'),
                    v.CardText(children=[f"Tree Species: {df.tree_species.values[0]}"],style_='font-size: 17px'),
                    v.CardText(children=[f"Tree Age: {df.tree_age.values[0]}"],style_='font-size: 17px'),
                    v.CardText(children=[f"Distance to Building: {round(build_dist/10000,2)}"],style_='font-size: 17px'),
                    update_btn, 
                ]),
            ])
        # dialog.v_model = show_dialog.value
        print('load --2')
        def dlog_close(*args):
            print('close')
            show_dialog.set(False)

        def dlog_update(*args):
            show_dialog.set(False)
            show_update_dialog.set(True)

        v.use_event(close_btn, 'click', dlog_close)
        v.use_event(update_btn, 'click', dlog_update)
    except:
        print('No tree found here')
        pass
    

@solara.component
def update_tree_dialog():
    conn = dbexe()
    species = json.loads(conn.get_species())['trees']
    print(species)
    tid = tree_id.value
    tuid = tree_uuid.value
    
    close_btn = v.Btn(color='primary', children=['X'], small=True, min_width=0.00, rounded=True,style_='float: right')
    submit_btn = v.Btn(color='primary', children=['Submit Update'])
    
    dialog = v.Dialog(class_='tree-dlog', width='550',
        v_model='dialog',overlay_opacity='0.2',
        
        children=[
            v.Card(style_='padding:10px', children=[close_btn, 
                v.CardTitle(class_='headline gray lighten-2', primary_title=True,
                            children=[f"Updating Tree ID: {tid}"]),
                
                v.CardText(children=[f'Is this object a tree?',
                                     solara.Switch(label='Yes',value=switch_msg, disabled=False)],style_='font-size: 17px'),
                v.CardText(children=[f'Select tree species',
                                     solara.Select(label='Species', value=tree_species, values=species, disabled=disable_fields.value)], style_=f'font-size: 17px;'),
                v.CardText(children=['Set estimated tree height',
                                     solara.SliderFloat(label='Tree Height (Meters)', value=tree_height, min=1.5, max=20.0, disabled=disable_fields.value)], style_=f'font-size: 17px;'),
                v.CardText(children=['Tree Age',
                                     solara.SliderInt(label='Tree Age (Years)', value=tree_age, min=1, max=300, disabled=disable_fields.value)], style_=f'font-size: 17px;'),
                v.CardText(children=[solara.Warning('The seleted objected will be removed from the database on submit')], style_=f'font-size: 17px; display:{show_switch_msg.value}'),
                                       
            ]),     

        submit_btn])
    # dialog.v_model = show_dialog.value

    def dlog_close2(*args):
        print('close')
        show_update_dialog.set(False)

    def dlog_submit(*args):
        print(tuid, 'Flag',switch_msg.value, 'spp',tree_species.value,'Est Hght',tree_height.value, 'Age',tree_age.value)
        print('Loaded')
        show_update_dialog.set(False)

    v.use_event(close_btn, 'click', dlog_close2)
    v.use_event(submit_btn, 'click', dlog_submit)

# @solara.component
def council_dashboard():
    if (sub_council_df.value is not None) & (flood_agg_cc_df.value is not None):
        df = sub_council_df.value
        pie_df = df.groupby(['landparcel']).count()/len(df)
        pie_df = pie_df.reset_index()
        
        if geom_type.value == 'cc':
            heat_dict = heat_layer_df.value.to_dict()[0]
        
        if geom_type.value == 'user':
            heat_dict = heat_layer_user.value.to_dict()[0]
        
        # flood_df = flood_agg_cc_df.value
    
        greens_data = []
        for value, name in zip(pie_df['label'].to_list(), pie_df['landparcel'].to_list()):
            greens_data.append({'value': round(value*100,2), 'name': name})

        flood_data = []
        for value, name in zip(flood_agg_cc_df.value['area'].to_list(), flood_agg_cc_df.value['prob'].to_list()):
            flood_data.append({'value': round(value*100,2), 'name': name})
        heat_data = []
        for value, name in zip(heat_dict.values(), heat_dict.keys()):
            heat_data.append({'value': round(value,2), 'name': name})

        options = {
                    "green_pie": {
                        "legend": {"data": [l['name'] for l in greens_data]},
                        "tooltip": {},
                        "series": [
                            {
                                "name": "greens",
                                "type": "pie",
                                "radius": ["30%", "70%"],
                                "data": greens_data,
                                "universalTransition": True,
                            }
                        ],
                    },
                    "flood_pie": {
                        "legend": {"data": [l['name'] for l in flood_data]},
                        "tooltip": {},
                        "series": [
                            {
                                "name": "flood",
                                "type": "pie",
                                "radius": ["30%", "70%"],
                                "data": flood_data,
                                "universalTransition": True,
                            }
                        ],
                    },
                    "heat_pie": {
                        "legend": {"data": [l['name'] for l in heat_data]},
                        "tooltip": {},
                        "series": [
                            {
                                 "name": "heat",
                                "type": "pie",
                                "color":['#fff5f0','#fcbea5','#fb7050','#d32020','#67000d'],
                                "radius": ["30%", "70%"],
                                "data": heat_data,
                                "universalTransition": True,
                            }
                        ],
                    },
                }
        
        solara.Button(label="close", on_click=lambda: close_dash(), color='#1976d2', style={"color": "#fff"})
        with solara.Column(classes=['dashboard']):
            solara.Card(title=f"{df.local_auth.unique()[0]}  ({df.cc_name.unique()[0]})", elevation=0, classes=['dashhead'])
            with solara.Columns(widths=[1,1,1]):
                with solara.Card(title='Number of Trees', classes=['dashtext']):
                    solara.Text(str(len(df)), style={"font-size": "25px", "color":"#212528"})
                if geom_type.value == 'cc':
                    with solara.Card(title='Council Area (Ha)', classes=['dashtext']):
                        solara.Text(str(round(df['cc_area'].unique()[0]/10000,2)), style={"font-size": "25px", "color":"#212528"})
                else:
                    with solara.Card(title='Boundary Area (Ha)', classes=['dashtext']):
                        solara.Text(str(round(geom_area.value/10000,2)), style={"font-size": "25px", "color":"#212528"})
                with solara.Card(title='Total Tree Cover (Ha)', classes=['dashtext']):
                    solara.Text(str(round(df['tree_area'].sum()/10000,2)), style={"font-size": "25px" , "color":"#212528"})
            if geom_type.value == 'cc':
                with solara.Columns(widths=[1,1,1]):
                    with solara.Card(title='Tree Crown Dist.', classes=['dashtext']):
                        px.histogram(df, 'tree_area')
                    with solara.Card(title='Trees In Green Spaces (%).', classes=['dashtext']):
                        solara.FigureEcharts(option=options['green_pie'])
                    with solara.Card(title='Probability of Floods (%)', classes=['dashtext']):
                        solara.FigureEcharts(option=options['flood_pie'])
            if geom_type.value == 'user':
                with solara.Columns(widths=[1,1,1,1]):
                    with solara.Card(title='Tree Crown Dist.', classes=['dashtext']):
                        px.histogram(df, 'tree_area')
                    with solara.Card(title='Trees In Green Spaces (%).', classes=['dashtext']):
                        solara.FigureEcharts(option=options['green_pie'])
                    with solara.Card(title='Probability of Floods (%)', classes=['dashtext']):
                        solara.FigureEcharts(option=options['flood_pie'])
                    with solara.Card(title='Heat Sensitivity (%)', classes=['dashtext']):
                        solara.FigureEcharts(option=options['heat_pie'])

def locals_dashboard():
    if (sub_locals_df.value is not None) & (heat_layer_df.value is not None) & (flood_agg_cc_df.value is not None):
        df = sub_locals_df.value
        pie_df = df.groupby(['landparcel']).count()/len(df)
        pie_df = pie_df.reset_index()
        heat_dict = heat_layer_df.value.to_dict()[0]
        
        greens_data = []
        for value, name in zip(pie_df['label'].to_list(), pie_df['landparcel'].to_list()):
            greens_data.append({'value': round(value*100,2), 'name': name})

        flood_data = []
        for value, name in zip(flood_agg_cc_df.value['area'].to_list(), flood_agg_cc_df.value['prob'].to_list()):
            flood_data.append({'value': round(value*100,2), 'name': name})

        heat_data = []
        for value, name in zip(heat_dict.values(), heat_dict.keys()):
            heat_data.append({'value': round(value,2), 'name': name})

        options = {
                    "green_pie": {
                        "legend": {"data": [l['name'] for l in greens_data]},
                        "tooltip": {},
                        "series": [
                            {
                                "name": "greens",
                                "type": "pie",
                                "radius": ["30%", "70%"],
                                "data": greens_data,
                                "universalTransition": True,
                            }
                        ],
                    },
                    "flood_pie": {
                        "legend": {"data": [l['name'] for l in flood_data]},
                        "tooltip": {},
                        "series": [
                            {
                                "name": "flood",
                                "type": "pie",
                               "radius": ["30%", "70%"],
                                "data": flood_data,
                                "universalTransition": True,
                            }
                        ],
                    },
                    "heat_pie": {
                        "legend": {"data": [l['name'] for l in heat_data]},
                        "tooltip": {},
                        "series": [
                            {
                                 "name": "heat",
                                "type": "pie",
                                "color":['#fff5f0','#fcbea5','#fb7050','#d32020','#67000d'],
                                "radius": ["30%", "70%"],
                                "data": heat_data,
                                "universalTransition": True,
                            }
                        ],
                    },
                }
        
        solara.Button(label="close", on_click=lambda: close_dash(), color='#1976d2', style={"color": "#fff"})
        with solara.Column(classes=['dashboard']):
            solara.Card(title=f"{called_layer_df.value.name[0]}", elevation=0, classes=['dashhead'])
            with solara.Columns(widths=[1,1,1]):
                with solara.Card(title='Number of Trees', classes=['dashtext']):
                    solara.Text(str(len(df)), style={"font-size": "25px", "color":"#212528"})
                
                with solara.Card(title='Council Area (Ha)', classes=['dashtext']):
                    solara.Text(str(round(called_layer_df.value["Shape_Area"].values[0]/10000,2)), style={"font-size": "25px", "color":"#212528"})
                
                with solara.Card(title='Total Tree Cover (Ha)', classes=['dashtext']):
                    solara.Text(str(round(df['tree_area'].sum()/10000,2)), style={"font-size": "25px" , "color":"#212528"})
            with solara.Columns(widths=[1,1,1,1]):
                with solara.Card(title='Tree Crown Dist.', classes=['dashtext']):
                    px.histogram(df,'tree_area')
                with solara.Card(title='Trees In Green Spaces (%).', classes=['dashtext']):
                    solara.FigureEcharts(option=options['green_pie'])
                with solara.Card(title='Probability of Floods (%)', classes=['dashtext']):
                    solara.FigureEcharts(option=options['flood_pie'])
                with solara.Card(title='Heat Sensitivity (%)', classes=['dashtext']):
                    solara.FigureEcharts(option=options['heat_pie'])
                      

# @solara.component
def census_dashboard():
    if (sub_census_df.value is not None) & (flood_agg_df.value is not None):
        df = sub_census_df.value
        pie_df = df.groupby(['landparcel']).count()/len(df)
        pie_df = pie_df.reset_index()
        # heat_dict = head_layer_df.value.to_dict()[0]
    
        
        greens_data = []
        for value, name in zip(pie_df['label'].to_list(), pie_df['landparcel'].to_list()):
            greens_data.append({'value': round(value*100,2), 'name': name})

        flood_data = []
        for value, name in zip(flood_agg_df.value['area'].to_list(), flood_agg_df.value['prob'].to_list()):
            flood_data.append({'value': round(value*100,2), 'name': name})

        # heat_data = []
        # for value, name in zip(heat_dict.values(), heat_dict.keys()):
        #     heat_data.append({'value': round(value,2), 'name': name})

        # print([l['name'] for l in greens_data])
        options = {
                    "green_pie": {
                        "legend": {"data":[l['name'] for l in greens_data] },
                        "tooltip": {},
                        "series": [
                            {
                                "name": "greens",
                                "type": "pie",
                                "radius": ["30%", "70%"],
                                "data": greens_data,
                                "universalTransition": True,
                            }
                        ],
                    },
                    "flood_pie": {
                        "legend": {"data": [l['name'] for l in flood_data]},
                        "tooltip": {},
                        "series": [
                            {
                                "name": "flood",
                                "type": "pie",
                                "radius": ["30%", "70%"],
                                "data": flood_data,
                                "universalTransition": True,
                            }
                        ],
                    },
                }
        solara.Button(label="close", on_click=lambda: close_dash(), color='#1976d2', style={"color": "#fff"})
        with solara.Column(classes=['dashboard']):
            solara.Card(title=f"{df.local_auth.unique()[0]}  ({df.cc_name.unique()[0]})", elevation=0, classes=['dashhead'])
            with solara.Columns(widths=[1,1,1]):
                with solara.Card(title='Number of Trees', classes=['dashtext']):
                    solara.Text(str(len(df)), style={"font-size": "25px", "color":"#212528"})
                with solara.Card(title='Census Area (Ha)', classes=['dashtext']):
                    solara.Text(str(round(df['simd_area'].unique()[0]/10000,2)), style={"font-size": "25px", "color":"#212528"})
                with solara.Card(title='Total Tree Cover (Ha)', classes=['dashtext']):
                    solara.Text(str(round(df['tree_area'].sum()/10000,2)), style={"font-size": "25px" , "color":"#212528"})
            with solara.Columns(widths=[1,1,1,1]):
                with solara.Card(title='Tree Crown Dist.', classes=['dashtext']):
                    px.histogram(df, 'tree_area')
                with solara.Card(title='Trees In Green Spaces (%).', classes=['dashtext']):
                    solara.FigureEcharts(option=options['green_pie'])
                with solara.Card(title='Probability of Floods (%)', classes=['dashtext']):
                    solara.FigureEcharts(option=options['flood_pie'])
                with solara.Card(title='Multiple Deprivation Indices', classes=['dashtext']):
                    solara.DataFrame(simd_props.value)
                
                

def hide_features_onload(m):
    m.find_layer('SIMD Boundaries').visible = False
    m.find_layer('Community Councils').visible=False
    
def convertCoordinates(polygon):
    transformer = pyproj.Transformer.from_proj(pyproj.Proj(init='epsg:4326'), pyproj.Proj(init='epsg:27700'), always_xy = True)
    projected = transform(transformer.transform, polygon)
    return projected

def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

def get_raster_stats(datasets, shp):
    shp_rp = shp.to_crs(27700)
    print(shp_rp)
    out_ls = {'Heat Category 1':[],'Heat Category 2':[],'Heat Category 3':[],'Heat Category 4':[],'Heat Category 5':[]}
    for m in datasets:
        print(m.name)
        try:
            out, _ = mask(dataset=m, shapes=getFeatures(shp_rp), all_touched=True, crop=True, nodata=9)
            # print(out)
            counts = np.unique(out, return_counts=True)
            # print(counts[0])
            if (len(counts[0]) != 1) & (np.sum(counts[1][:-1])>10):
                ind_dict = {n:(v/np.sum(counts[1][:-1]))*100 for  n, v in zip(counts[0][:-1], counts[1][:-1])}
                print(ind_dict)
                for b in [1,2,3,4,5]:
                    if b in ind_dict.keys():
                        out_ls[f'Heat Category {b}'].append(ind_dict[b])
                    else:
                        out_ls[f'Heat Category {b}'].append(0.0)
            else:
                pass
        except:
            pass

    return pd.DataFrame(out_ls).T

# Layer Controls
def layer_widget(m):
    style = {"description_width":"initial", "width":"80px"}
    layer_icon_close =  widgets.Button(
                button_style = 'info',
                disabled=False,
                tooltip='Close Layers',
                icon='fa-times',
                style={"margin-left":"170px"},
                layout=widgets.Layout(width="50px")
            )
    # layer_icon =  widgets.HTML(
    #         value="<i class='fa fa-bars' style='font-size: 20px;' aria-hidden='true'></i>",
    #         layout=widgets.Layout(width="25px", height='30px', padding="3px"),
    #         )
    tree_section = widgets.HTML(
            value="<b>Tree Layers</b>",
            )
    
    tree_checkbox = widgets.Checkbox(
        value=False,
        description='Tree Map',
        style=style,
        layout=widgets.Layout(width="210px", padding="0px"),
    )

    stir_mask_checkbox = widgets.Checkbox(
        value=False,
        description='Tree Masks',
        style=style,
        layout=widgets.Layout(width="210px", padding="0px"),
    )

    tree_radio_button = widgets.RadioButtons(
        options=['Trees in Clackmannanshire','Trees in Falkirk','Trees in Stirlingshire',],

        style=style,
        layout=widgets.Layout(width="210px", padding="5px 0px 0px 15px"),
    )

    bound_section = widgets.HTML(
            value="<b>Boundary Data</b>",
            )
    
    simd_checkbox = widgets.Checkbox(
        value=False,
        description='SIMD Census Boundaries',
        style=style,
        layout=widgets.Layout(width="210px", padding="0px"),
    )

    cc_checkbox = widgets.Checkbox(
        value=False,
        description='Community Councils',
        style=style,
        layout=widgets.Layout(width="210px", padding="0px"),
    )

    locals_checkbox = widgets.Checkbox(
        value=False,
        description='Localities',
        style=style,
        layout=widgets.Layout(width="210px", padding="0px"),
    )

    heatIndex_checkbox = widgets.Checkbox(
        value=False,
        description='Heat Sensitivity Index',
        style=style,
        layout=widgets.Layout(width="210px", padding="0px"),
    )


    data_section = widgets.HTML(
            value="<b>Spatial Data</b>",
            )
    
    flood_checkbox = widgets.Checkbox(
        value=False,
        description='Floods Layer',
        style=style,
        layout=widgets.Layout(width="210px", padding="0px"),
    )
    output = widgets.Output()

    def show_stir_mask(change):
        tree_layer = m.find_layer('Tree Bounds')
        if change.new:
            tree_layer.visible = True
        elif change.new == False:
            tree_layer.visible = False

    stir_mask_checkbox.observe(show_stir_mask, names='value')
    def show_simd_bounds(change):
        if change.new:
            m.add_gdf(gdf=sim_geom, style={'fillOpacity': 0.1, "stroke": True,"color": "#0cb854","weight": 2}, layer_name='SIMD Boundaries', zoom_to_layer=False, info_mode=None)
            sim_on.set(True)
        if change.new == False:
            sim_on.set(False)
            print('off..')
            simd_layer = m.find_layer('SIMD Boundaries')
            m.remove_layer('SIMD Boundaries')
            for layer in m.layers:
                if layer.name =='SIMD Boundaries':
                    print(layer.name)
                    layer.visible = False
            [print(l.name, l.visible) for l in m.layers]
            print('off..')

    simd_checkbox.observe(show_simd_bounds, names='value')
    
    def show_cc_bounds(change):
        if change.new:
            m.add_gdf(gdf=cc_geom, style={'fillOpacity': 0.1, "stroke": True,"color": "#0000ff","weight": 2}, layer_name='Community Councils', zoom_to_layer=False, info_mode=None)
            cc_on.set(True)
        if change.new == False:
            cc_on.set(False)
            print('off..')
            cc_layer = m.find_layer('Community Councils')
            m.remove_layer('Community Councils')
            for layer in m.layers:
                if layer.name =='Community Councils':
                    print(layer.name)
                    layer.visible = False
            [print(l.name, l.visible) for l in m.layers]
            print('off..')     
    cc_checkbox.observe(show_cc_bounds, names='value')

    def show_local_bounds(change):
        if change.new:
            m.add_gdf(gdf=locals_geom, style={'fillOpacity': 0.1, "stroke": True,"color": "#eda011","weight": 2}, layer_name='Localities', zoom_to_layer=False, info_mode=None)
            local_on.set(True)
            print('Localities on..')
        if change.new == False:
            local_on.set(False)
            local_layer = m.find_layer('Localities')
            m.remove_layer('Localities')
            for layer in m.layers:
                if layer.name =='Localities':
                    print(layer.name)
                    layer.visible = False
            [print(l.name, l.visible) for l in m.layers]
            print('Localities off..')

    locals_checkbox.observe(show_local_bounds, names='value')

    def show_trees_roi(change):
        if change.new:
            value = tree_radio_button.value
            if value == 'Trees in Clackmannanshire':
                center.set((56.122495, -3.807203))

            if value == 'Trees in Stirlingshire':
                center.set((56.116834, -3.937200))

            if value == 'Trees in Falkirk':
                center.set((56.002427, -3.783659))

            print(value)
    tree_radio_button.observe(show_trees_roi, names='value')

    def show_trees(change):
        tree_layer = m.find_layer('Tree Map')
        if change.new:
            tree_layer.visible = True
            m.add_legend(title="Tree Probability", legend_dict={'0.1 - 0.24':'#f7fcf5', '0.24 - 0.39':'#d5efcf', '0.39 - 0.53':'#9ed798', '0.53 - 0.68':'#55b567', '0.68 - 0.82':'#1d8641', '0.82 - 0.97':'#00441b'})
        elif change.new == False:
            tree_layer.visible = False
            clear_legend(m,"Tree Probability" )
            
    tree_checkbox.observe(show_trees, names='value')

    def show_heatIndex(change):
        tree_layer = m.find_layer('Heat Map')
        if change.new:
            tree_layer.visible = True
            m.add_legend(title="Heat Index", legend_dict={'Category 1 (Cool)':'#fff5f0', 'Category 2':'#fcbea5', 'Category 3':'#fb7050', 'Category 4':'#d32020', 'Category 5 (Warm)':'#67000d'})
        elif change.new == False:
            tree_layer.visible = False
            clear_legend(m,"Heat Index" )
            
    heatIndex_checkbox.observe(show_heatIndex, names='value')


    def show_flood(change):
        flood_layer = m.find_layer('Flood Extent')
        if change.new:
            flood_layer.visible = True
            m.add_legend(title="Flood Probability", legend_dict={'High':'#28ceaf', 'Medium':'#ce334d', 'Low':'#adcf6a'}, layer_name="Flood Extent", position='bottomleft',name='Legend')
        elif change.new == False:
            flood_layer.visible = False
            clear_legend(m,"Flood Probability" )
    
    flood_checkbox.observe(show_flood, names='value')

    

    layer_control_box = widgets.VBox(
        [layer_icon_close,
         tree_section, 
         tree_checkbox,
         tree_radio_button,
         stir_mask_checkbox,
         bound_section,
         simd_checkbox,
         cc_checkbox,
         locals_checkbox,
         data_section,
         flood_checkbox,
         heatIndex_checkbox, 
         output]
    )

    setattr(m, 'layer_control_box', layer_control_box)
    
    def close_layer_control(kwargs):
        print(m.layer_control_box.layout.display)
        if m.layer_control_box.layout.display == 'block':
            m.layer_control_box.layout.display = 'none'
            map_layer_state.set(False)
        elif map_layer_state.value == True:
            m.layer_control_box.layout.display = 'none'
            map_layer_state.set(False)
   
    layer_icon_close.on_click(close_layer_control)

def lc_icon(m):
    layer_icon_open =  widgets.Button(
                disabled=False,
                tooltip='Show Layers',
                icon='fa-bars',
                layout=widgets.Layout(width="30px"),
            )
    def show_layer_control(kwargs):
        if map_layer_state.value:
            map_layer_state.set(False)
        print('on', map_layer_state.value)
        if m.layer_control_box.layout.display == 'none':
            m.layer_control_box.layout.display = 'block'
            map_layer_state.set(True)
        elif map_layer_state.value == False:
            m.add_widget(m.layer_control_box, position='topright')
            map_layer_state.set(True)
    
    layer_icon_open.on_click(show_layer_control)
    m.add_widget(layer_icon_open, position='topright')

def info_icon(m):
    info =  widgets.Button(
                disabled=False,
                tooltip='Show Portal Info',
                icon='fa-info',
                layout=widgets.Layout(width="30px"),
            )
    
    def show_info(kwargs):
        show_info_dlog.set(True)

    info.on_click(show_info)
    m.add_widget(info, position='bottomleft')


# Draw Controls
def draw_tools(m):
    draw_control = ipyleaflet.DrawControl()
    draw_control.polygon = {
        "shapeOptions": {
            "name":"polygon",
            "fillColor": "#6be5c3",
            "color": "#6be5c3",
            "fillOpacity": 0.1
        },
        "drawError": {
            "color": "#dd253b",
            "message": "Oups!"
        },
        "allowIntersection": False
    }
    draw_control.rectangle = {
        "shapeOptions": {
            "name":"rectangle",
            "fillColor": "#fca45d",
            "color": "#fca45d",
            "fillOpacity": 0.1
        }
    }

    draw_control.marker = {
        "shapeOptions": {
            "fillColor": "#fca45d",
            "color": "#fca45d",
            "fillOpacity": 1.0
        }
    }
    
    geo_features = {
    'type': 'FeatureCollection',
    'features': []
    }
    def get_draws_features(target, action, geo_json):
        print('action', action)
        if action == 'created':
            clear_called_layer(m)
            geom_type.set('user')
            trees_stir = m.find_layer('Tree Map')
            # draw_features.set(geo_features)
            geod = Geod(ellps="WGS84")
            bound_area, bound_perimeter = geod.geometry_area_perimeter(Polygon(geo_json['geometry']['coordinates'][0]))
            
            print('From Map', geo_json['properties']['style']['name'])
            geom_area.set(abs(bound_area))
            print(round(geom_area.value/10000, 2))
            if (trees_stir.visible == True) &  ((geo_json['properties']['style']['name']=='polygon') or (geo_json['properties']['style']['name']=='rectangle')):
                gdf = gpd.GeoDataFrame(index=[0], crs='epsg:4326', geometry=[Polygon(geo_json['geometry']['coordinates'][0])])
                gdf = gdf.to_crs(27700)
                hdf = get_raster_stats([heat_map_clacks,heat_map_falkirk,heat_map_stirling], gdf)
                print(hdf)
                heat_layer_user.set(hdf)
                conn = dbexe()
                tdf, cc_df, flood_df = conn.get_user_data(geo_json['geometry']['coordinates'])
                print('tree',tdf)
                print('cc',cc_df)
                conn.close_connection()
                sub_council_df.set(pd.DataFrame(tdf))
                print(flood_df)
                flood_agg_cc_df.set(pd.DataFrame(flood_df))
                

    draw_control.on_draw(get_draws_features)
    m.add_control(draw_control)




# @solara.component
class Map(leafmap.Map):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        show_update_dialog.set(False)
        show_dialog.set(False)
        show_switch_msg.set('None')

        def get_click_event_data(**kwargs):
            # print(kwargs)
            # print({l.name:l.visible  for l in self.layers})
            if kwargs.get('type')=='click':
                print(map_layer_state.value)
                lat = kwargs.get('coordinates')[0]
                lon = kwargs.get('coordinates')[1]
                print(Point(lon, lat))
                print(convertCoordinates(Point(lon, lat)))

                [print(l.name, l.visible) for l in self.layers]

                tree_map = self.find_layer('Tree Map')
                heat_map1 = self.find_layer('Heat Map')
                
                print('SIMD:',sim_on.value, 'CC:',cc_on.value, 'Local:', local_on.value)
                if (sim_on.value == True) and (tree_map.visible==True):
                    clear_called_layer(self)
                    print('SIMD Boundaries')
                   
                    conn = dbexe()
                    sub_attribs, simd_data, flood_data = conn.get_simd_data(lat, lon)
                    names = ['Overall SIMD Rank', 'Population', 'Health Domain Rank', 'Comparative Illness Factor','Anxiety, Depression (Population)', 'Income Rank' ]
                    props = ['rankv2','wape2017','hlthrank','hlthcif','hlthdprspc','incrankv2']
                    simd_df = simd_data.loc[:,props].T
                    simd_df['Description'] = names
                    simd_df = simd_df.reset_index()
                    print(simd_df)
                    simd_df.rename(columns={simd_df.columns[1]:'Rank'}, inplace=True)
                      
                    simd_props.set(simd_df.loc[:,['Description','Rank']])
                    self.add_gdf(gdf=simd_data, style={'fillOpacity': 0.2, "stroke": True,"color": "#f5e357","weight": 2}, layer_name='Called Layer', info_mode=None, zoom_to_layer=False)
                    print(sub_attribs.head())
                    conn.close_connection()
                    sub_census_df.set(pd.DataFrame(sub_attribs))
                    print(flood_data)
                    flood_agg_df.set(pd.DataFrame(flood_data))
                    # head_layer_df.set(get_raster_stats([heat_map_clacks,heat_map_falkirk,heat_map_stirling], simd_data))

                if (cc_on.value == True) and (tree_map.visible==True):
                    clear_called_layer(self)
                    print('Community Councils')
                    conn = dbexe()
                    sub_attribs, cc_data, flood_data = conn.get_council_data(lat, lon)
                    print(sub_attribs.head())
                    self.add_gdf(gdf=cc_data, style={'fillOpacity': 0.2, "stroke": True,"color": "#f5e357","weight": 2}, layer_name='Called Layer', info_mode=None, zoom_to_layer=False)
                    conn.close_connection()
                    sub_council_df.set(pd.DataFrame(sub_attribs))
                    print(flood_data)
                    flood_agg_cc_df.set(pd.DataFrame(flood_data))
                    # head_layer_df.set(get_raster_stats([heat_map_clacks,heat_map_falkirk,heat_map_stirling], cc_data))

                if (local_on.value == True) and (tree_map.visible==True):
                    clear_called_layer(self)
                    print('Localities')
                    conn = dbexe()
                    sub_attribs, local_data, flood_data = conn.get_localities_data(lat, lon)
                    print(sub_attribs.head())
                    self.add_gdf(gdf=local_data, style={'fillOpacity': 0.2, "stroke": True,"color": "#f5e357","weight": 2}, layer_name='Called Layer', info_mode=None, zoom_to_layer=False)
                    # heat_stat_df = get_raster_stats([heat_map_clacks,heat_map_falkirk,heat_map_stirling], local_data)
                    conn.close_connection()
                    sub_locals_df.set(pd.DataFrame(sub_attribs))
                    called_layer_df.set(pd.DataFrame(local_data))
                    flood_agg_cc_df.set(pd.DataFrame(flood_data))
                    hdf = get_raster_stats([heat_map_clacks,heat_map_falkirk,heat_map_stirling], local_data)
                    print(hdf)
                    heat_layer_df.set(hdf)
                    

                if (tree_map.visible==True) and ((cc_on.value == False) and (sim_on.value == False)):
                    clear_called_layer(self)
                    print('Collecting Tree Data')
                    conn = dbexe()
                    attrib_df, tree_gdf= conn.tree_layer(lat, lon)
                    tree_df.set(pd.DataFrame(attrib_df))
                    self.add_gdf(gdf=tree_gdf, style={'fillOpacity': 0.2, "stroke": True,"color": "#f5e357","weight": 2}, layer_name='Called Layer', info_mode=None, zoom_to_layer=False)
                    conn.close_connection()
                    show_dialog.set(True)
        
        draw_tools(self)
        self.add_basemap("Esri.WorldImagery")
        self.add_wms_layer(url=wms_url.value, layers=flood_bounds.value, name="Flood Extent", format='image/png', shown=False)
        self.add_wms_layer(url=wms_url.value, layers=heat_index.value, name="Heat Map", format='image/png', opacity=0.6, shown=False)
        self.add_wms_layer(url=wms_url.value, layers=tree_layer.value, name="Tree Map", format='image/png', shown=False)
        self.add_wms_layer(url=wms_url.value, layers=tree_masks.value, name="Tree Bounds", format='image/png', shown=False)

        # self.add_wms_layer(url=wms_url.value, layers=simd_bounds.value, name="SIMD Boundaries", format='image/png', shown=False)
        # self.add_wms_layer(url=wms_url.value, layers=cc_bounds.value, name="Community Councils", format='image/png', shown=False)
        
        self.add_gdf(gdf=sim_geom, hover_style={'fillOpacity': 0,"color": "#0000ff","weight": 0}, style={'fillOpacity': 0, "stroke": True,"color": "#0000ff","weight": 0}, layer_name='SIMD Boundaries', info_mode=None, zoom_to_layer=False)
        self.add_gdf(gdf=cc_geom, hover_style={'fillOpacity': 0,"color": "#0000ff","weight": 0}, style={'fillOpacity': 0, "stroke": True,"color": "#0cb854","weight": 0}, layer_name='Community Councils', info_mode=None, zoom_to_layer=False)
        hide_features_onload(self)

        # self.add_legend(title="Flood Probability", legend_dict={'High':'#28ceaf', 'Medium':'#ce334d', 'Low':'#adcf6a'}, layer_name="Flood Extent", position='bottomleft',name='Legend')
        # self.add_legend(title="Tree Probability", legend_dict={'0.1 - 0.24':'#f7fcf5', '0.24 - 0.39':'#d5efcf', '0.39 - 0.53':'#9ed798', '0.53 - 0.68':'#55b567', '0.68 - 0.82':'#1d8641', '0.82 - 0.97':'#00441b'}, layer_name="Trees")
        layer_widget(self)
        lc_icon(self)
        info_icon(self)
        self.on_interaction(callback=get_click_event_data)
    
@solara.component
def Page():
    no_tree_msg()
    # print([l.name for l in Map.layers])
    css ="""
    .v-dialog__content--active {
    z-index: 9999999 !important;
    padding: 10px;
    }

    .layers-chks{    
    
    position: absolute;
    z-index: 9999;}

    .dashboard-close {
       display:none;
    }
    .sideboard {
    z-index: 999;
    max-height:100%;
    height:100%;
    max-width: 20%;
    width:200%;
    transition: width 2s;
    }
   .dashboard {
    max-width: 100%;
    height:70%;
    transition: width 2s;
    overflow-x: scroll;
    }
    .dashhead .v-card__title{
    font-size:30px;
    padding:5px;
    height:10px;
    }
    .dashtext{
    font-size:35px;
    }
    * {
        padding: 0;
        margin: 0;
    }

    .v-sheet {row-gap:0px !important;}

    .basemap img {
      width: 100px !important;
      border-radius: 10px !important;

    .jupyter-widgets.leaflet-widgets{
      height: 100% !important;
      
    }

        
        """ 
    with solara.Head():
        solara.Title('Forth Valley Tree Map')
        solara.Style(css)
        # solara.Style(legend_show.value)

    with solara.Column(style={"min-width": "500px", "height": "100vh"," width": "100vw"}, classes=['main']):
       Map.element(  # type: ignore
            zoom=zoom.value,
            on_zoom=zoom.set,
            center=center.value,
            on_center=center.set,
            scroll_wheel_zoom=True,
            toolbar_control = False,
            draw_control = False,
            height = "100%"
            )

       if sub_census_df.value is not None:
           census_dashboard()
       
       if sub_council_df.value is not None:
           council_dashboard()  

       if sub_locals_df.value is not None:
           locals_dashboard()
       
       if show_dialog.value:
           tree_dialog()
       
       if show_update_dialog.value:
           update_tree_dialog()
       
       if show_info_dlog.value:
           show_portal_info()

Page()
