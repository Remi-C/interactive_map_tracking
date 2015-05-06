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
  e_s.edge_id,
  lane.lane_side,
  lane.lane_position,
  ST_AsEWKB(lane.lane_center_axis) AS lane_center_axis
FROM
  test.edges_selected AS e_s
  INNER JOIN
  street_amp.visu_result_lane AS lane
    ON
      e_s.edge_id = lane.edge_id
ORDER BY e_s.edge_id
