// Function round numbers
function roundup(x) {
  return Number.parseFloat(x).toFixed(2);
};

// Function for clearing selected tiles or regions
function removePrevious() {
  map.eachLayer(function(layer) {
    if (layer.options.attribution === "sub_predicted_trees") {
      map.removeLayer(layer)
      console.log('yes')
    }
  });
};

// Basemaps
var streetmap = L.tileLayer('http://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',{
                attribution: '&copy; <a href="https://www.google.co.uk/maps/">Google Maps</a> contributors',
                maxZoom: 30,
                subdomains:['mt0','mt1','mt2','mt3']
        });
var grayscale = L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}', {
                id: 'mapbox/light-v9', 
                maxZoom: 30,
                accessToken:'pk.eyJ1IjoiZWRkM3giLCJhIjoiY2wzYWZqcmx2MDU4NzNkcncxbG8wbmkzZiJ9.0k__Mn5kK4cIKyhrGJnvfg',
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>'
            });
    
var satellite = L.tileLayer('http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',{
                attribution: '&copy; <a href="https://www.google.co.uk/maps/">Google Maps</a> contributors',
                maxZoom: 30,
                subdomains:['mt0','mt1','mt2','mt3']
        });

var map = L.map('map', {
  center: [56.115734, -3.937639],
  zoom: 15,
  layers: [grayscale, streetmap, satellite]
  
});

// Load Bbox as WMS tiles
var wmsLayer = L.Geoserver.wms("http://139.153.226.33:8080/geoserver/FORTHERA_GEO/wms", {
    layers: "FORTHERA_GEO:pred_Buffer",
    transparent: true,
    attribution: "All Predicted Trees"
  });
  wmsLayer.addTo(map);


// Function for fetching WFS layers
function userWFS(tile) {
  var wfsLayer = L.Geoserver.wfs("http://139.153.226.33:8080/geoserver/wfs", {
        layers: "FORTHERA_GEO:pred_Buffer",
        CQL_FILTER: tile,
        plotdivID:'histogram',
        countdivID:'treeStats',
        attribution: "sub_predicted_trees",
        onEachFeature: function (feature, layer) {
          layer.bindPopup(
            "Label: " + feature.properties.label + " <br> Crown Area: " + roundup(feature.properties.area) + " <br> Probability: " + roundup(feature.properties.score * 100),
          );},
        });
        
        wfsLayer.addTo(map)
}


// Function for grid overlay and showing plots/stats on click
var gridLayer = new L.GeoJSON.AJAX('static/shapes/OSGB_Grid_Stirling.geojson', {
  Style: {
    "opacity": 0.4,
    "stroke-opacity": 0.3,
    "stroke-width": 0.5
  },
    
   onEachFeature: function (fData, fLayer) {
    fLayer.on('click', function () {
      document.getElementById("offCanvas")
      // console.log('Clicked feature layer ID: ' + fData.properties.PLAN_NO);
      let tileID = "'" + fData.properties.PLAN_NO+".jpg"+"'";
      console.log(`image_path=${tileID}`)
     userWFS(`image_path=${tileID}`)
    });
  }
});


//Leaflet basemap control
var baselayers = {
    "Streets": streetmap,
    "Satllite": satellite,
    "Grayscale": grayscale
};
// Leaflet Feature layer control
var bboxlayers = {
    'OSGB Grid' :gridLayer,
    "Trees": wmsLayer,
    // "Trees Intrv":wfsLayer
};

//add map scale
L.control.scale({position:'bottomright'}).addTo(map);

L.control.layers(baselayers, bboxlayers, {collapsed:false, position:'topright'}).addTo(map);
map.zoomControl.setPosition('topleft');
