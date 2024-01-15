function roundup(x) {
  return Number.parseFloat(x).toFixed(2);
}

// adding mapbox tilelayer 
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

//add map scale
L.control.scale().addTo(map);

var wmsLayer = L.Geoserver.wms("http://139.153.226.33:8080/geoserver/FORTHERA_GEO/wms", {
    layers: "FORTHERA_GEO:predicted_bbox",
    transparent: true,
    attribution: "Predicted Trees"
  });
//   wmsLayer.addTo(map);
var arealist = [];
var wfsLayer = L.Geoserver.wfs("http://139.153.226.33:8080/geoserver/wfs", {
    layers: "FORTHERA_GEO:predicted_bbox",
    CQL_FILTER: "image_path='NS8093'",
    onEachFeature: function (feature, layer) {
      // console.log(feature);
      console.log(feature.properties.area);
      // arealist.push(feature.properties.area);
      layer.bindPopup(
        "Label: " + feature.properties.label + " || Crown Area: " + roundup(feature.properties.area) + " || Probability: " + roundup(feature.properties.score * 100),
      );},
    });
  wfsLayer.addTo(map)

// console.stdlog = console.log.bind(console);

console.log = function(){
  var dat = Array.from(arguments);
    arealist.push(dat[0]);
    // console.stdlog.apply(console, arguments);
}
console.log(arealist.length)
// var arr = [126.5, 289, 259.625, 146.875, 310.25, 494.5, 129.25, 107.5, 172.25, 206.625, 272.1875]
// var trace = {
//     x: arealist,
//     type: 'histogram',
//   };
// Plotly.newPlot("histogram", [trace]);

document.getElementById("treeStats").innerHTML = "Total Number of Trees:" + arealist ;

//Leaflet layer control
var baselayers = {
    "Streets": streetmap,
    "Satllite": satellite,
    "Grayscale": grayscale
};

var bboxlayers = {
    "Trees": wmsLayer,
    "Trees Intrv":wfsLayer
};

L.control.layers(baselayers, bboxlayers, {collapsed:false, position:'topright'}).addTo(map);
// var layerControl = L.control.layers(baselayers).addTo(map);
// layerControl.addBaseLayer(satellite, "Satllite");
map.zoomControl.setPosition('topleft');
// basemaps.Satelite.addTo(map);
