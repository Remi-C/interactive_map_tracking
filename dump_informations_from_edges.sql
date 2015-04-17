-------------------------------
--Lionel-A
--SIDT IGN 04/2015
-------------------------------

------
-- for TrafiPollu soft.
-- retrieve (dump) 'informations' from edges selected in QGIS client

SELECT 
  DISTINCT edges.edge_id,
  lane.lane_side,
  edges.start_node,
  edges.end_node,
  ST_asText(axis.intersection_limit1) AS Point_Amont,
  ST_asText(axis.intersection_limit2) AS Point_Aval,
  axis.road_width,
  axis.lane_number,
  lane.lane_position
FROM 
  test.edges_selected AS edges
JOIN 
  street_amp.visu_result_axis AS axis  
NATURAL JOIN 
  street_amp.visu_result_lane AS lane  
ON 
  edges.edge_id = axis.edge_id
ORDER BY edges.edge_id, lane.lane_side
