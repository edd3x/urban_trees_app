
var wfsUrl = "http://139.153.226.33:8080/geoserver/wfs";
var wfslayer =  "FORTHERA_GEO:predicted_bbox";
var wfsCQL_FILTER =  "image_path='NS7993'";
var data_arr = [];
$.ajax(wfsUrl, {
    type: "GET",
    data: {
    request: "GetFeature",
    typename: wfslayer,
    CQL_FILTER: wfsCQL_FILTER,
    },
    dataType: "jsonp",
    success: function (data) {
        count.push(data.features.length)
        
        for (var i = 0; i < data.features.length; i++) {
            // console.log(data.features[i].properties.area)
            data_arr.push(data.features[i].properties.area);
        }

    },
    async: false
});

document.getElementById("treeStats").innerHTML = "Total Number of Trees:" + count ;

var trace = {
      x: data_arr,
      type: 'histogram',
    };
Plotly.newPlot("histogram", [trace]);