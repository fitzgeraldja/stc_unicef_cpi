var countries = ee.FeatureCollection("FAO/GAUL/2015/level0").filterBounds(area_including_nigeria).select("ADM0_NAME");
var nigeria = countries.filter(ee.Filter.eq("ADM0_NAME", "Nigeria"));

var start_date = ee.Date('2010-01-01');
var end_date = ee.Date('2020-01-01');

// Resolution scale in meters
var res_scale = 500;

// Visualization
var palette = [
    '000096', '0064ff', '00b4ff', '33db80', '9beb4a',
    'ffeb00', 'ffb300', 'ff6400', 'eb1e00', 'af0000'
];

// I use this dataset just to get the same projection as John
///////////// POPULATION ////////////////
// NB pop_data has ~100m res
var popTot = ee.Image('WorldPop/GP/100m/pop_age_sex/NGA_2020').select(
    'population', 'M_0', 'M_1', 'M_5', 'M_10', 'M_15', 'M_20', 'F_0', 'F_1', 'F_5', 'F_10', 'F_15', 'F_20'
);
popTot;
print('popTot', popTot);

print('pop scale', popTot.select('population').projection().nominalScale())
var export_proj = popTot.select('population').projection().getInfo();



// Precipitation
// GPM: Monthly Global Precipitation Measurement (GPM) v6 
// https://developers.google.com/earth-engine/datasets/catalog/NASA_GPM_L3_IMERG_MONTHLY_V06?hl=en
// 
var precipitation = ee.ImageCollection('NASA/GPM_L3/IMERG_MONTHLY_V06')
    .select('precipitation')
    .filterBounds(nigeria)
    .filterDate(start_date, end_date);

// Display mean and stdDev on the map
var precipitationMeanVis = { min: 0.0, max: 1.5, palette: palette };
Map.addLayer(precipitation.select('precipitation').reduce(ee.Reducer.mean()).resample().clip(nigeria), precipitationMeanVis, 'Precipitation Mean');

var precipitationVis = { min: 0.0, max: 1.5, palette: palette };
Map.addLayer(precipitation.select('precipitation').reduce(ee.Reducer.stdDev()).resample().clip(nigeria), precipitationVis, 'Precipitation SD');


// Export precipitation mean
Export.image.toDrive({
    image: precipitation.select('precipitation').reduce(ee.Reducer.mean()).resample().clip(nigeria),
    description: 'cpiPrecipiMeanData_' + res_scale,
    fileFormat: 'GeoTIFF',
    region: nigeria,
    scale: res_scale,
    crs: export_proj.crs,
    crsTransform: export_proj.transform,
    folder: 'Data',
    maxPixels: 9e8
});

// Export precipitation accumulation
Export.image.toDrive({
    image: precipitation.select('precipitation').reduce(ee.Reducer.stdDev()).resample().clip(nigeria),
    description: 'cpiPrecipiStData_' + res_scale,
    fileFormat: 'GeoTIFF',
    region: nigeria,
    scale: res_scale,
    crs: export_proj.crs,
    crsTransform: export_proj.transform,
    folder: 'Data',
    maxPixels: 9e8
});


///////////////////////////////////////////////////////////////////    
// Precipitation 2
// https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_TERRACLIMATE#bands
var terraClimate = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE')
    .filterBounds(nigeria)
    .filterDate(start_date, end_date);


print('precipitation', terraClimate);


var precipitationVis = { min: 0.0, max: 72450, palette: palette };

// precipitation accumulation, measured in mm
// I take the mean
Map.addLayer(terraClimate.select('pr').reduce(ee.Reducer.mean()).resample().clip(nigeria), precipitationVis, 'Precipitation Acc');

// Palmer Drought Severity Index
var pdsiVis = { min: -4317, max: 3418, palette: palette };
var latestImage = terraClimate.limit(1, 'system:time_start', false).first();
print(latestImage)
Map.addLayer(latestImage.select('pdsi').resample().clip(nigeria), pdsiVis, 'Draught Sev Index');

// Actual evapotranspiration, derived using a one-dimensional soil water balance model
// Compute Mean
var aetVis = { min: 0.0, max: 3140, palette: palette };
Map.addLayer(terraClimate.select('aet').reduce(ee.Reducer.mean()).resample().clip(nigeria), aetVis, 'Evapotransportation');


// Export precipitation accumulation
Export.image.toDrive({
    image: terraClimate.select('pr').reduce(ee.Reducer.mean()).resample().clip(nigeria),
    description: 'cpiPrecipiAccData_' + res_scale,
    fileFormat: 'GeoTIFF',
    region: nigeria,
    scale: res_scale,
    crs: export_proj.crs,
    crsTransform: export_proj.transform,
    folder: 'Data',
    maxPixels: 9e8
});

// Palmer Drought Severity Index
Export.image.toDrive({
    image: latestImage.select('pdsi').resample().clip(nigeria),
    description: 'cpiPDSIData_' + res_scale,
    fileFormat: 'GeoTIFF',
    region: nigeria,
    scale: res_scale,
    crs: export_proj.crs,
    crsTransform: export_proj.transform,
    folder: 'Data',
    maxPixels: 9e8
});

// evapotranspiration
Export.image.toDrive({
    image: terraClimate.select('aet').reduce(ee.Reducer.mean()).resample().clip(nigeria),
    description: 'cpiEvapotransData_' + res_scale,
    fileFormat: 'GeoTIFF',
    region: nigeria,
    scale: res_scale,
    crs: export_proj.crs,
    crsTransform: export_proj.transform,
    folder: 'Data',
    maxPixels: 9e8
});






// // Satellite Images per se
// // ee.ImageCollection("COPERNICUS/S2_SR")
// var cloud_free_image = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")
//       .filterBounds(nigeria)
//       // check them in the last year
//       .filterDate(start_date,end_date)
//       // Pre-filter to get less cloudy granules.
//       .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE',20));
//       // Image with the least cloud cover
//       // .sort('CLOUD_COVER')
//       // .first();


// var visualization = {min : 0, max:3000, bands:['B4', 'B3','B2'], gamma:1.4}
// //   // min: 0.0,
// //   // max: 0.3,
// //   bands: ['B4', 'B3', 'B2'],
// // };


// // Map.addLayer(rgb.select('B8').reduce(ee.Reducer.mean()).clip(nigeria), {}, 'Monochromatic');
// // .select('precipitation').reduce(ee.Reducer.mean()).clip(nigeria), precipitationVis, 'Precipitation');

// Map.addLayer(cloud_free_image.reduce(ee.Reducer.mean()), visualization, 'LandSat Image');



