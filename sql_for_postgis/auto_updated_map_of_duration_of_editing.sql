---------------------------
--Rémi Cura, 02/205, IGN THALES 
---------------------------
/** this example shows a way to create an hexagonal map over a given area, then this map will be automatically updated by the tracking result.
 The way to use it is simple :
 add a polygon to the create_tracking_grid layer.
 It will update the table  hexagonal_tracking.hexagonal_grid  with new hexagonal grid 
Then when an user is tracked within the grid, the status of the concerned cells are automatically updated. 
This needs some custom functions found on https://github.com/Remi-C/PPPP_utilities
 - CDB_HexagonGrid 
 - 
*/
CREATE SCHEMA IF NOT EXISTS hexagonal_tracking ;  

--creating a table to hold the grid
DROP TABLE IF EXISTS hexagonal_tracking.hexagonal_grid ;
CREATE TABLE hexagonal_tracking.hexagonal_grid (
nid SERIAL PRIMARY KEY,
hex geometry,
total_time_spent float,
cell_size float,
info text  
) ; 
--putting some index on the table
CREATE INDEX ON hexagonal_tracking.hexagonal_grid USING GIST(hex); 
CREATE INDEX ON hexagonal_tracking.hexagonal_grid USING GIST(ST_Centroid(hex)); 
CREATE INDEX ON hexagonal_tracking.hexagonal_grid (total_time_spent); 
CREATE INDEX ON hexagonal_tracking.hexagonal_grid (cell_size);  
CREATE INDEX ON hexagonal_tracking.hexagonal_grid (info);  

--creating a table to hold extent inserted by user 
DROP TABLE IF EXISTS hexagonal_tracking.adding_cells_to_hex_grid;
CREATE TABLE  hexagonal_tracking.adding_cells_to_hex_grid   (
	gid SERIAL PRIMARY KEY,
	geom geometry(polygon,932011),
	cell_size float,
	info text
) ; 
CREATE INDEX ON hexagonal_tracking.adding_cells_to_hex_grid USING GIST(geom); 
CREATE INDEX ON hexagonal_tracking.adding_cells_to_hex_grid (cell_size);  
 
 
 CREATE OR REPLACE FUNCTION hexagonal_tracking.rc_sync_hex_cells(  )
  RETURNS  trigger  AS
$BODY$ 
/** @brief : this functin compute an hexagonal grid over the input geom,  then insert it into hexagonal_tracking.hexagonal_grid , 
if same cell doesn"t already exists
*/ 
	DECLARE
		_q text ;
		_inserted_hex bigint;
	BEGIN  
		IF TG_OP = 'DELETE' THEN  --delete old cell that where under the old geom with same cell_size
			DELETE FROM hexagonal_tracking.hexagonal_grid AS to_up 
			WHERE to_up.cell_size = OLD.cell_size AND ST_DWithin(to_up.hex, OLD.geom, OLD.cell_size*1.5)=TRUE ; 
			 
			RETURN OLD ; 
		END IF ; 
		
		IF TG_OP = 'UPDATE' THEN --delete old cell that where under the old geom and that are not under the new one
				 DELETE FROM hexagonal_tracking.hexagonal_grid AS to_up 
				WHERE to_up.cell_size = OLD.cell_size  
					AND ST_DWithin(to_up.hex, OLD.geom, OLD.cell_size*1.5 )=TRUE
					AND ST_DWithin(to_up.hex, NEW.geom, NEW.cell_size *1.5)=FALSE  
				;
		END IF ; 

		IF TG_OP = 'UPDATE' OR TG_OP = 'INSERT' THEN 
			NEW.geom = ST_SnapToGrid(NEW.geom, NEW.cell_size) ; 
			WITH inputs AS ( -- xrapping of input for test of querry outside of plpgsql
				SELECT NEW.geom AS igeom, NEW.cell_size
			)
			, new_cells AS ( -- creating new cells, some may already exists
				SELECT   CDB_HexagonGrid( inputs.igeom , inputs.cell_size) as hex ,inputs.cell_size
				FROM inputs
			)
			, dedup_cells AS ( --keepingon ly new cells that dont exist already
				SELECT nc.*
				FROM new_cells AS nc,inputs
				WHERE ST_DWithin(nc.hex,inputs.igeom, inputs.cell_size) = TRUE
				EXCEPT 
				SELECT hex, cell_size
				FROM hexagonal_tracking.hexagonal_grid as hg 
				
			)
			INSERT INTO hexagonal_tracking.hexagonal_grid (hex ,total_time_spent  ,cell_size)
			SELECT dc.hex, 0.0, dc.cell_size
			FROM dedup_cells AS dc ; 
			RETURN NEW; 

			
		END IF ; 
		RETURN NULL ; --shouldnever be reached
	END ;
	$BODY$
  LANGUAGE plpgsql VOLATILE;
  

DROP TRIGGER IF EXISTS rc_sync_hex_cells ON  hexagonal_tracking.adding_cells_to_hex_grid; 
CREATE TRIGGER rc_sync_hex_cells 
AFTER UPDATE OR INSERT OR DELETE
ON hexagonal_tracking.adding_cells_to_hex_grid
FOR ROW 
EXECUTE PROCEDURE hexagonal_tracking.rc_sync_hex_cells(  )  ; 



--adding a triger on the tracking layer to update the time spend on hex 
 CREATE OR REPLACE FUNCTION hexagonal_tracking.rc_update_hex_edit_time(  )
  RETURNS  trigger  AS
$BODY$ 
/** @brief : when a new tracing geom is added/removed/updated, update accordingly the hex grid if it exists
*/ 
	DECLARE
		_q text ; 
		_duration float; 
		_do_delete_insert BOOLEAN := FALSE  ; 
		_geom geometry ;
	BEGIN  
	--tacking the previously inserted camera, comput edit duration
		IF TG_OP = 'UPDATE' THEN --we shall remove time for the previous position, then add time for the new position, that is perform a delete and an insert
			_do_delete_insert := TRUE ; 
		END IF ; 
		
		IF TG_OP = 'DELETE' OR _do_delete_insert = TRUE THEN 
			--removing the edit time of input
			--find the next camera, 
			SELECT EXTRACT(EPOCH FROM cp.w_time-OLD.w_time) as duration into _duration
			FROM tracking.camera_position AS cp
			WHERE cp.user_id = OLD.user_id
				AND abs(EXTRACT(EPOCH FROM cp.w_time-OLD.w_time)) < 5*60
				AND  cp.w_time > OLD.w_time
			ORDER BY w_time ASC
			LIMIT 1 ;
			--RAISE EXCEPTION 'duration : %',_duration ; 
			if _duration IS NOT NULL AND _duration >0 THEN 
				--remove found time of concerned hex, if necessary
				UPDATE hexagonal_tracking.hexagonal_grid SET (total_time_spent) = (CASE WHEN total_time_spent-_duration<0 THEN 0 ELSE total_time_spent-_duration END)
				WHERE ST_Intersects(OLD.geom, hex) = TRUE ; 
				IF _do_delete_insert = FALSE THEN 
					RETURN OLD ; 
				END  IF ; 
			END IF ; 
		END IF ; 

		IF TG_OP = 'INSERT' OR _do_delete_insert = TRUE THEN --update value with previous camera
			--we use the previous camera, because for the new one, we can't compute duration
			SELECT  EXTRACT(EPOCH FROM NEW.w_time-cp.w_time) as duration  , geom into _duration, _geom
			FROM tracking.camera_position AS cp
			WHERE cp.user_id = NEW.user_id
				AND abs(EXTRACT(EPOCH FROM NEW.w_time-cp.w_time)) < 5*60
				AND cp.w_time <  NEW.w_time
			ORDER BY w_time DESC
			LIMIT 1 ;

			if _duration IS NOT NULL AND _duration >0  THEN 
				--remove found time of concerned hex, if necessary
				UPDATE hexagonal_tracking.hexagonal_grid SET (total_time_spent) =( total_time_spent+_duration)
				WHERE ST_Intersects(_geom, hex) = TRUE ; 
				IF _do_delete_insert = FALSE THEN
					RETURN NEW ; 
				END IF ; 
			END IF ; 
			
		END IF ; 

		IF _do_delete_insert = TRUE THEN
			RETURN NEW ; 
		END IF ; 
		RETURN NULL ; --shouldnever be reached
	END ;
	$BODY$
  LANGUAGE plpgsql VOLATILE; 

DROP TRIGGER IF EXISTS rc_update_hex_edit_time ON  tracking.camera_position; 
CREATE TRIGGER rc_update_hex_edit_time 
AFTER UPDATE OR INSERT OR DELETE
ON tracking.camera_position
FOR ROW 
EXECUTE PROCEDURE hexagonal_tracking.rc_update_hex_edit_time(  ) ;

  