-------------------------------
--Rémi-C
--Thales IGN 02/2015
-------------------------------

/** This script create a postgis table that can be used for tracking with QGIS plugin "Interactive Map Tracking"
How to use it : 
 - execute this script in your PostGIS server. It will create a new table tracking.camera_position
 - install "Interactive Map Tracking" from qgis plugin repository or "https://github.com/Remi-C/interactive_map_tracking/"
 - start an empty QGIS project, or open an existing one
 - configure the plugin by clicking on its icon ( T )
   + enable plugin and tracking by checking boxes
   + go in tracking tab
     _ select camera_position positon as the tracking layer. If it doesn't appear in the list, refresh the list
     _ set the threshold. It is a scale. You wil track camera position if 1/camera scale is _below_ the threshold
 - Now move your camera (left/right + zomm/dezoom). If you are zoomed enough
   + your camera position wiil be added to camera_tracking
   + the user_id (your session name + IP) will be filled
   + the w_time (current time up to milliseconds) will be filled
   + any other field of tracking table will be put to NULL
 - (MULTI USER)
   + do the same think for many users, using the same postgis table
   + you will see the position and history of position for each user that has activated tracking.
*/
 --checking that postgis is installed
 CREATE EXTENSION IF NOT EXISTS postgis ;
 
 --creating a schema to put our tracking table
 CREATE SCHEMA IF NOT EXISTS tracking ;

 --creating the minimal tracking table, other column can be added at will
 DROP TABLE IF EXISTS tracking.camera_position ;
 CREATE TABLE IF NOT EXISTS tracking.camera_position ( 
	gid SERIAL PRIMARY KEY --mandatory
	,geom geometry(polygon,4326)  --use your custom SRID here
	,user_id text --mandatory
	,w_time timestamp with time zone  --mandatory
 ); 
--creating index is not mandatory but will speed up all usual operations on those columns
CREATE INDEX ON tracking.camera_position USING GIST(geom) ; 
CREATE INDEX ON tracking.camera_position (user_id ) ; 
CREATE INDEX ON tracking.camera_position (w_time ) ; 


--creating a view that will warn the users when there is a conflict
DROP VIEW IF EXISTS  tracking.camera_position_multi_user_conflict ;
CREATE VIEW tracking.camera_position_multi_user_conflict AS
	SELECT row_number() over(order by c1.gid, c2.gid) as ngid
		, c1.gid as gid_user1
		, c2.gid as gid_user2
		, ST_Multi(ST_Union(c1.geom,c2.geom))::geometry(multipolygon,4326) AS geom
		, format('WARNING :User %s and user %s are in conflict here, 
		same edition separated by %s sec 
		(only allowed if edits are separated by > 5min)',c1.user_id, c2.user_id, abs(extract(EPOCH FROM c1.w_time-c2.w_time)))::text as warn
	FROM tracking.camera_position AS c1
		,tracking.camera_position AS c2
	WHERE c1.user_id<> c2.user_id --we want conflict between different users
		AND c1.gid < c2.gid -- (gid2,gid2) is identical for us here too (gid2,gid1)
		AND ST_Intersects(c1.geom, c2.geom) --conflict is when tracking at the same place (place sharing space)
		AND abs(extract(EPOCH FROM c1.w_time-c2.w_time))< 5*60 --conflict is when it is recent. Old editing canbe reviewed without error
		;

DROP VIEW IF EXISTS  tracking.camera_position_single_user_conflict ;
CREATE VIEW tracking.camera_position_single_user_conflict AS
	SELECT row_number() over(order by c1.gid, c2.gid) as ngid
		, c1.gid as gid_user1
		, c2.gid as gid_user2
		, ST_Multi(ST_Union(c1.geom,c2.geom))::geometry(multipolygon,4326) AS geom
		, format('WARNING : You, %s ,
		 just edited something that you already edited %s ago
		 You can re-edit area if you edited it less than 5 minutes ago 
		)',c1.user_id , abs(extract(EPOCH FROM c1.w_time-c2.w_time)))::text as warn
	FROM tracking.camera_position AS c1
		,tracking.camera_position AS c2
	WHERE c1.user_id = c2.user_id --we want conflict between different users
		AND c1.gid < c2.gid -- (gid2,gid2) is identical for us here too (gid2,gid1)
		AND ST_Intersects(c1.geom, c2.geom) --conflict is when tracking at the same place (place sharing space)
		AND abs(extract(EPOCH FROM c1.w_time-c2.w_time))> 5*60 --conflict is when it is recent. Old editing canbe reviewed without error
		;

 SELECT *
 FROM tracking.camera_position_single_user_conflict ;
--checking that the table was correctly created
 SELECT *
 FROM tracking.camera_position;  

--creating a function that will be called by the trigger
 CREATE OR REPLACE FUNCTION rc_correct_gid_on_insert(  )
  RETURNS  trigger  AS
$BODY$ 
/** @brief : this trigger insert the correct gid into table if QGIS provides 0 or NULL gid (default behaviour). 
*/ 
	DECLARE
	_getting_next_val text;  
	_q text ; 
	_next_val int;  
	BEGIN  
		 
		IF NEW.gid <=0 OR NEW.gid IS NULL THEN --case when inserted gid is not valid
			SELECT  column_default INTO _getting_next_val --getting the next value of serial field
			from information_schema.columns 
			WHERE table_schema = TG_TABLE_SCHEMA --the schema name is accessbile at execution time, no need to hard code it
				AND table_name=TG_TABLE_NAME --same for table name
				AND column_name = 'gid';
			_q := 'SELECT '||_getting_next_val ; 
			EXECUTE _q INTO _next_val ; 
			
			NEW.gid := _next_val; 	
		END IF;   
		return NEW ; 
	END ;
	$BODY$
  LANGUAGE plpgsql VOLATILE;
  
 --now associating the function to any UPDATE OR INSERT happening on teacking table.
DROP TRIGGER IF EXISTS rc_correct_gid_on_insert ON  tracking.camera_position; 
CREATE TRIGGER rc_correct_gid_on_insert 
BEFORE  UPDATE OR INSERT
ON tracking.camera_position
FOR ROW 
EXECUTE PROCEDURE rc_correct_gid_on_insert() ;
 