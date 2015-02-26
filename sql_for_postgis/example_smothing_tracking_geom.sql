-------------------------------
--Rémi-C
--Thales IGN 02/2015
-------------------------------

------
-- this example create a tracking table, and add a trigger to it, so that saved camera position appear smoother than rectangle
 
 CREATE SCHEMA IF NOT EXISTS tracking ;

 DROP TABLE IF EXISTS tracking.camera_position ;
 CREATE TABLE IF NOT EXISTS tracking.camera_position ( --creating the minimal tracking table, other column can be added at will
	gid SERIAL PRIMARY KEY
	,geom geometry(polygon,4326)
	,user_id text
	,w_time timestamp with time zone  
 ); 
CREATE INDEX ON tracking.camera_position USING GIST(geom) ; 
CREATE INDEX ON tracking.camera_position (user_id ) ; 
CREATE INDEX ON tracking.camera_position (w_time ) ; 

--checking
 SELECT *
 FROM tracking.camera_position;  


 CREATE OR REPLACE FUNCTION rc_correct_gid_on_insert(  )
  RETURNS  trigger  AS
$BODY$ 
/** @brief : this trigger insert the correct gid into table if QGIS provides 0 or NULL gid (default behaviour).
It also smooth the inserted geometry
*/ 
	DECLARE
	_getting_next_val text;  
	_q text ; 
	_next_val int; 
	
	_width FLOAT ;
	_height FLOAT; 
	_mindim FLOAT; 
	_radius_percent FLOAT := 0.9 ; --between 0 and 1. The radius will be this percent of min(width,height) 
	BEGIN  
		 
		IF NEW.gid <=0 OR NEW.gid IS NULL THEN --case when inserted gid is not valid
			SELECT  column_default INTO _getting_next_val
			from information_schema.columns 
			where table_name='camera_position'
				AND column_name = 'gid';
			_q := 'SELECT '||_getting_next_val ; 
			EXECUTE _q INTO _next_val ; 
			
			NEW.gid := _next_val; 	
		END IF;  

				--computing width and height of geom
		SELECT ST_XMax(geom) - ST_XMin(geom) , ST_YMax(geom) - ST_YMin(geom) INTO _width , _height
		FROM (SELECT NEW.geom) AS geom  ;

		_mindim := LEAST(_width , _height) ; 
		NEW.geom := ST_Buffer(ST_Buffer(ST_Buffer(NEW.geom, -_mindim*(_radius_percent/2.0)), _mindim*(_radius_percent/2.0)) ,-_mindim*0.10) ; 
		--RAISE EXCEPTION '%', ST_AsText(NEW.geom) ; 
		return NEW ; 
	END ;
	$BODY$
  LANGUAGE plpgsql VOLATILE;
  

DROP TRIGGER IF EXISTS rc_correct_gid_on_insert ON  tracking.camera_position; 
CREATE TRIGGER rc_correct_gid_on_insert 
BEFORE  UPDATE OR INSERT
ON tracking.camera_position
FOR ROW 
EXECUTE PROCEDURE rc_correct_gid_on_insert(  ) ;
 
 
