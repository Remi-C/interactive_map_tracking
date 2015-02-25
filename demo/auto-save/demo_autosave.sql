-------------------------------
--Rémi-C
--Thales IGN 02/2015
-------------------------------

------
-- this example create a table with 2 geometry columns
-- one is a linestring, the other a polygon
-- the aim is that when the linestring is changed, the polygon is automatically updated
-- we use a trigger for that
-- the same can be done for geometries in 2 or more different tables
-- here for demonstration purpose, we compute poly as a random buffer of line

/** Instruction : 

  + execute this sql script. It will create a new table auto_save.line_to_poly_sync in your PostGIS database
  + create an empty QGIS 2.6 project, load the 2 geometrical layers of auto_save.line_to_poly_sync.
    - You have now 2 postgis layers in your qgis project
  + Get the extension "Interactive Map Tracking"  from QGIS plug-in repository or this github : https://github.com/Remi-C/interactive_map_tracking
  + Launch the extension by clicking on the icon ( T ), and enable it and auto-save by checking the comboboxes.

  + Edit the line layer. you can insert, delete, update the geometry, translate, etc
  + Each time you edit the line, the poly layer is automatically updated, and QGIS rendering refreshed
  + The poly associated to the line you changed is updated (with a random buffer so you see that something changed) instantaneously !

  + It still works without the plugin, but after each edit, you have to save it and refresh (for instance move camera, or zoom/dezoom)
*/
 
 --checking that postgis is installed
 CREATE EXTENSION IF NOT EXISTS postgis ;
 
 --creating a schema to put our tracking table
 CREATE SCHEMA IF NOT EXISTS auto_save ;

 --creating the minimal tracking table, other column can be added at will
 DROP TABLE IF EXISTS auto_save.line_to_poly_sync ;
 CREATE TABLE IF NOT EXISTS auto_save.line_to_poly_sync ( 
	gid SERIAL PRIMARY KEY --mandatory
	, line geometry(linestring, 4326) -- use your custom SRID here
	, poly geometry(polygon,4326)  --use your custom SRID here 
 ); 
--creating index is not mandatory but will speed up all usual operations on those columns
CREATE INDEX ON auto_save.line_to_poly_sync USING GIST(line) ; 
CREATE INDEX ON auto_save.line_to_poly_sync USING GIST(poly) ; 

--checking that the table was correctly created
 SELECT *
 FROM auto_save.line_to_poly_sync;  

--creating a function that will be called by the trigger
 CREATE OR REPLACE FUNCTION rc_buffer_line_on_insert_or_update(  )
  RETURNS  trigger  AS
$BODY$ 
/** @brief : this trigger compute the buffer of line (random()/10) and save it at each change (insert/update)
*/ 
	DECLARE 
	BEGIN   
		NEW.poly = ST_Buffer(NEW.line,random()/10.0);
		RETURN NEW ;
	END ;
	$BODY$
 LANGUAGE plpgsql VOLATILE;
  
 --now associating the function to any UPDATE OR INSERT happening on auto_save.line_to_poly_sync table.
DROP TRIGGER IF EXISTS rc_buffer_line_on_insert_or_update ON  auto_save.line_to_poly_sync; 
CREATE TRIGGER rc_buffer_line_on_insert_or_update 
BEFORE  UPDATE OR INSERT --here we define when the function should be called. No need to call it on DELETE ! 
ON auto_save.line_to_poly_sync
FOR ROW --for each changed row, the function will be called
EXECUTE PROCEDURE rc_buffer_line_on_insert_or_update() ;