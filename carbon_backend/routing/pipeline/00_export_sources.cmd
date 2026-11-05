@echo off
rem Export the OSM features needed to build the LEZ polygon (uses GDAL shipped with QGIS).
rem   - Old District 1 / District 3 boundaries (boundary=historic, end_date=2025-06-30)
rem   - New Phuong An Khanh boundary (contains the Thu Thiem peninsula)
rem   - Tran Nao road (eastern edge of the Thu Thiem peninsula)
setlocal
if "%QGIS_BIN%"=="" set "QGIS_BIN=C:\Program Files\QGIS 4.2.3\bin"
set "ROOT=%~dp0.."
rem The Vietnam extract (330 MB) is kept outside the repo, e.g. set OSM_PBF=D:\Thesis\vietnam-261012.osm.pbf
if "%OSM_PBF%"=="" (echo Set OSM_PBF to the Geofabrik vietnam-*.osm.pbf file first. & exit /b 1)
set "OUT=%ROOT%\data\sources"
if not exist "%OUT%" mkdir "%OUT%"

call "%QGIS_BIN%\o4w_env.bat" >nul

rem OSM relation ids: 2587287 = Quan 1 (old), 3819816 = Quan 3 (old), 7351897 = Phuong An Khanh (new)
ogr2ogr -f GeoJSON -overwrite "%OUT%\admin_boundaries.geojson" "%OSM_PBF%" multipolygons ^
  -spat 106.64 10.74 106.78 10.83 ^
  -where "osm_id IN ('2587287','3819816','7351897')" -lco RFC7946=YES 2>nul || exit /b 1

ogr2ogr -f GeoJSON -overwrite "%OUT%\tran_nao_candidates.geojson" "%OSM_PBF%" lines ^
  -spat 106.72 10.77 106.74 10.81 ^
  -where "highway IS NOT NULL AND name LIKE 'Tr%%n N%%o'" -lco RFC7946=YES 2>nul || exit /b 1

echo Sources written to %OUT%
