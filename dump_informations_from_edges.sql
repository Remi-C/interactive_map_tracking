-------------------------------
--Lionel-A
--SIDT IGN 04/2015
-------------------------------

------
-- for TrafiPollu soft.
-- retrieve (dump) 'informations' from edges selected in QGIS client

SELECT
--
  DISTINCT
  edges.edge_id,
  edges.ign_id
--,
  edges.start_node,
edges.end_node
-- url: http://www.postgis.org/docs/ST_AsEWKB.html,
ST_AsEWKB(edges.geom)               AS linez_geom
--,
  ST_AsEWKB(axis.intersection_limit1) AS point_amont,
ST_AsEWKB(axis.intersection_limit2) AS point_aval
--,
  axis.road_width,
axis.lane_number
FROM
  test.edges_selected AS edges
  JOIN
  street_amp.visu_result_axis AS axis
ON
  edges.edge_id = axis.edge_id
ORDER BY edges.edge_id
