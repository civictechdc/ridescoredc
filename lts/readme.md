# Level of Traffic Stress Implementation

This notebook implements the [Level of Traffic Stress](https://peterfurth.sites.northeastern.edu/2014/05/21/criteria-for-level-of-traffic-stress/) model. Specifically, the [2022 edition](https://bpb-us-e1.wpmucdn.com/sites.northeastern.edu/dist/e/618/files/2014/05/LTS-Tables-v2.2.pdf) though there is more background in the [original model](https://peterfurth.sites.northeastern.edu/level-of-traffic-stress/).

In short, this quantifies how stressful or comfortable a road is to bike on.
* Level 1: Cyclists are not in contact with traffic (except for slow, low volume traffic); comfortable for all level of cycling abilities (including children).
* Level 2: Cyclists have their own space and intersections are easy to navigate; comfortable for adult cyclists.
* Level 3: Cyclists interact with some moderate/multi-lane traffic or close to higher-speed traffic; acceptable for 'enthused and confident' cyclists.
* Level 4: Cyclists interact with or are near high-speed traffic; acceptable for 'strong and fearless' cyclists.

The first step was find correspondence between the descriptions and the available [DC road data](https://opendata.dc.gov/datasets/DCGIS::roadway-block/about).

Then, the LTS descriptions are translated into criteria that can be extracted from the data (see LTS.xlsx)

Lastly, the new per road segment data is added to the postgis database and the function and html files are updated to incorporate the LTS. See 'mvp_map' folder.

Below is a function to get the road information from the database:

```
CREATE OR REPLACE FUNCTION update_score(z integer, x integer, y integer, query_params json)
RETURNS bytea AS $$
DECLARE
  mvt bytea;
  bounds geometry;
BEGIN
  -- Tile bounds in 3857
  bounds := ST_TileEnvelope(z, x, y);

  SELECT INTO mvt
  ST_AsMVT(tile, 'update_score', 4096, 'geom')
  FROM (
    SELECT
      ST_AsMVTGeom(
        ST_Transform(wkb_geometry, 3857),
        bounds,
        4096,
        64,
        true
      ) AS geom,
      (ridescore_v1*(query_params->>'i_ridescore')::int + lts_100*(query_params->>'i_lts_original')::int + speedlimit_score*(query_params->>'i_speedlimit')::int +
num_lanes_score*(query_params->>'i_numlanes')::int+ facility_score*(query_params->>'i_facility')::int+ function_score*(query_params->>'i_function')::int+ road_width_score*(query_params->>'i_roadwidth')::int+ pavement_condition_score*(query_params->>'i_pavement')::int) / ((query_params->>'i_ridescore')::int + (query_params->>'i_lts_original')::int + (query_params->>'i_speedlimit')::int+ (query_params->>'i_numlanes')::int+ (query_params->>'i_facility')::int+ (query_params->>'i_function')::int+ (query_params->>'i_roadwidth')::int+ (query_params->>'i_pavement')::int) AS user_score,
	seg_id,
	route_name,
	bike_facility_type,
	function,
	lts_level,
	num_lanes_raw,
	parking_presence,
	pavement_condition,
	ridescore_v1,
	original_lts,
	road_width,
	speed_limit_raw	
    FROM ridescoredc
    WHERE wkb_geometry &&
          ST_Transform(bounds, 4326)
  ) AS tile
  WHERE geom IS NOT NULL;

  RETURN mvt;
END
$$ LANGUAGE plpgsql STABLE STRICT PARALLEL SAFE;

```