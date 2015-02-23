---------------------------
--Rémi Cura, 02/205, IGN THALES 
---------------------------

--LIMIT 100
CREATE SCHEMA IF NOT EXISTS test ;  


	DROP TABLE IF EXISTS  test.editing_duration_map;
	CREATE TABLE test.editing_duration_map AS 
		WITH camp_pos AS (--getting the tracking data, filtering to create map only for one user 
			SELECT *
			FROM tracking.camera_position  
			WHERE user_id = 'Remi (192.168.1.2)'
			ORDER BY w_time ASC, gid asc
		)
		,duration AS ( --computer the duration of each editing by taking the next camera position time and substract it from current camera tie
			SELECT *,  lead(w_time ,1) over(ORDER BY w_time ASC , gid asc)  -w_time  as duration 
			FROM camp_pos
		)
		, edit_time as ( --convert the time interval into seconds (decimal), to be able to work with it
			SELECT gid, extract(EPOCH  from duration) as edit_time
			FROM duration
		)
		, noded_geom AS (--take only the exterior ring of camera geometry, then union and node the geom.
		--nodding means all intersection between lines will happen on a node
			SELECT ST_Node(ST_Union(ST_ExteriorRing(geom))) as n_geom
			FROM camp_pos
		)
		,polygonized_geom AS (--polygonize the linestrings, that is construct all possible minimal polygons from the linestring
			SELECT st_polygonize(n_geom) as p_geom
			FROM noded_geom
		)
		,part_of_camera AS (--extract each individual camera piece
		SELECT row_number() over() as nid, dmp.geom as geom
		FROM polygonized_geom, st_dump(p_geom) as dmp 
		)
		,mapping_partial_full AS ( --this is an inefficient way to compute this,and is only written here as example
			--for each polygon piece, find in which original camera position it is, without having precision issue
			SELECT DiSTINCT  cp.gid, po.nid,ST_Area(ST_Intersection(po.geom, cp.geom)) --distinct works with the order, to avoid precision issue
			FROM part_of_camera AS po,  tracking.camera_position  AS cp
			WHERE cp.user_id = 'Remi (192.168.1.2)'
				AND ST_DWithin(po.geom, cp.geom,1) = TRUE --we don't use st_within because precision
			ORDER BY   cp.gid, po.nid, ST_Area(ST_Intersection(po.geom, cp.geom)) DESC --when finding mutliple candidates take the best match
		)
		, grouped_time AS ( --now that each piece of polygon is linnked to an original camera and time, count how much time was spent on each piece of polygon
			SELECT   nid, sum(et.edit_time) as tot_edit_time
			FROM mapping_partial_full
				NATURAL JOIN edit_time as et
			GROUP BY nid
		) --final result : taking previous result, but adding geometry for qgis display
		SELECT nid, geom, tot_edit_time
		FROM grouped_time
			NATURAL join part_of_camera ; 



------
--Second version, compute also the time spend over editing, but on an hexagonal grid
--NOTE : we separate the computing of the grid only for perfomance reason (namely, use of the index)
--need : https://github.com/Remi-C/PPPP_utilities/blob/master/postgis/cdb_Hexagon.sql
------
	DROP TABLE IF EXISTS test.hexagonal_grid ;
	CREATE TABLE test.hexagonal_grid AS
		WITH camp_pos AS (--getting the tracking data, filtering to create map only for one user 
			SELECT *
			FROM tracking.camera_position  
			WHERE user_id = 'Remi (192.168.1.2)'
			ORDER BY w_time ASC, gid asc
		)
		, extent_of_tracking_data AS ( --simply getting the extent of all tracked data, that is the minimal rectangle (aligned with NS, EW) covering it
			SELECT ST_Extent(geom) as geom
			FROM camp_pos
			--WHERE ST_DWithin(ST_SetSRID(ST_MakePoint(4818,18218),932011),geom, 800)
			LIMIT 1 --security
		)
		--,generating_hexagonal_grid as (
		--need : https://github.com/Remi-C/PPPP_utilities/blob/master/postgis/cdb_Hexagon.sql
			SELECT row_number() over() AS nid, ST_SetSRID(hex,932011) as hex, 0.0 AS total_time_spent 
			FROM extent_of_tracking_data, CDB_HexagonGrid(geom, 10) as hex; 

		--some indexes, the geometric index is essential
		CREATE INDEX ON test.hexagonal_grid USING GIST(hex); 
		CREATE INDEX ON test.hexagonal_grid (total_time_spent); 
		ALTER TABLE test.hexagonal_grid ADD primary key (nid) ; 
			 
		WITH camp_pos AS (--getting the tracking data, filtering to create map only for one user 
			SELECT *
			FROM tracking.camera_position  
			WHERE user_id = 'Remi (192.168.1.2)'
				AND ST_DWithin(ST_SetSRID(ST_MakePoint(4818,18218),932011),geom, 800)
			ORDER BY w_time ASC, gid asc
		)
		,edit_time AS ( --computer the duration of each editing by taking the next camera position time and substract it from current camera tie
			SELECT *,  LEAST(extract(EPOCH  from lead(w_time ,1) over(ORDER BY w_time ASC , gid asc)  -w_time)  ,100) as edit_time 
			FROM camp_pos 
		)     
		,mapping_grid_to_edit_time AS (--edit the way it should be done
			SELECT gh.nid, et.gid, et.edit_time
			FROM test.hexagonal_grid  as gh, edit_time as et
			WHERE ST_Intersects(gh.hex,et.geom )= TRUE
				--AND edit_time BETWEEN 0 AND 10
		)
		, grouped_time AS ( --now that each piece of polygon is linnked to an original camera and time, count how much time was spent on each piece of polygon
			SELECT   nid, sum(edit_time) as tot_edit_time
			FROM mapping_grid_to_edit_time 
			GROUP BY nid
		) --finale, put the right information into hexagional table
		UPDATE 	test.hexagonal_grid as hg SET total_time_spent = 
		tot_edit_time
		FROM grouped_time as gt
		WHERE gt.nid = hg.nid ; 

