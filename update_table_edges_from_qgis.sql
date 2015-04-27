-------------------------------
--Lionel-A
--SIDT IGN 04/2015
-------------------------------

------
-- for TrafiPollu soft.
-- add a table to get edges selected from QGIS client

DROP TABLE IF EXISTS test.edges_selected;
CREATE TABLE test.edges_selected
AS (
  SELECT
    edge_id
    ,ign_id
    ,start_node
    ,end_node
    ,geom
  FROM
    bdtopo_topological.edge_data
  WHERE
    ST_Intersects(ST_MakePolygon(ST_GeomFromText(%(gPolylineWkt)s, %(extent_postgisSrid)s)), geom)
    OR
    ST_Contains(ST_MakePolygon(ST_GeomFromText(%(gPolylineWkt)s, %(extent_postgisSrid)s)), geom)
  ORDER BY edge_id
);
