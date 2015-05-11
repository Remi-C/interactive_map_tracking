-------------------------------
--Lionel-A
--SIDT IGN 04/2015
-------------------------------

------
-- for TrafiPollu soft.
-- retrieve (dump) 'informations' from edges selected in QGIS client
-- url: http://www.postgis.org/docs/ST_AsEWKB.html

SELECT
--
  DISTINCT edges.edge_id                AS str_edge_id
  ,edges.ign_id                         AS str_ign_id
  ,edges.start_node                     AS ui_start_node
  ,edges.end_node                       AS ui_end_node
  ,ST_AsEWKB(edges.geom)                AS wkb_edge_center_axis
  ,ST_AsEWKB(axis.intersection_limit1)  AS wkb_amont
  ,ST_AsEWKB(axis.intersection_limit2)  AS wkb_aval
  ,axis.road_width                      AS f_road_width
  ,axis.lane_number                     AS ui_lane_number
FROM
  test.edges_selected AS edges
  JOIN
  street_amp.visu_result_axis AS axis
ON
  edges.edge_id = axis.edge_id
ORDER BY edges.edge_id
