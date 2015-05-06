-------------------------------
--Lionel-A
--SIDT IGN 04/2015
-------------------------------

------
-- for TrafiPollu soft.
-- add a table to get edges selected from QGIS client

DROP VIEW IF EXISTS test.edges_selected;
CREATE VIEW test.edges_selected
AS (
  SELECT
    edge_id
    ,ign_id
    ,start_node
    ,end_node
    ,geom
  FROM
    bdtopo_topological.edge_data as ed
  WHERE
    (
      ST_Intersects(ST_MakePolygon(ST_GeomFromText(%(gPolylineWkt)s, %(extent_postgisSrid)s)), geom)
      OR
      ST_Contains(ST_MakePolygon(ST_GeomFromText(%(gPolylineWkt)s, %(extent_postgisSrid)s)), geom)
    )
    AND
        -- s'assure que les elements selectionnes sont (updatés) dans SG3 (visul_result_axis)
        EXISTS(SELECT 1 FROM street_amp.visu_result_axis as v_r_a WHERE v_r_a.edge_id = ed.edge_id)
  ORDER BY edge_id
);

DROP VIEW IF EXISTS test.nodes_selected;
CREATE VIEW test.nodes_selected
AS (
  SELECT
    DISTINCT node_id
  FROM
    bdtopo_topological.node as n
  WHERE
    (
      ST_Intersects(ST_MakePolygon(ST_GeomFromText(%(gPolylineWkt)s, %(extent_postgisSrid)s)), geom)
      OR
      ST_Contains(ST_MakePolygon(ST_GeomFromText(%(gPolylineWkt)s, %(extent_postgisSrid)s)), geom)
    )
    AND
        -- s'assure que les elements selectionnes sont (updatés) dans SG3 (visul_result_axis)
        EXISTS(SELECT 1 FROM street_amp.visu_result_intersection as v_r_i WHERE v_r_i.node_id = n.node_id)
  ORDER BY node_id
);
