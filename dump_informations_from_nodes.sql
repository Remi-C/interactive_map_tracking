-------------------------------
--Lionel-A
--SIDT IGN 04/2015
-------------------------------

------
-- for TrafiPollu soft.
-- retrieve (dump) 'informations' from nodes selected in QGIS client

SELECT
--
  DISTINCT oepnp.node_id
  ,oepnp.edge_id1
  --oepnp.edge_id2,
  --oepnp.clockwise_order
FROM 
  bdtopo_topological.ordered_edges_per_node_pair as oepnp
JOIN
  test.nodes_selected AS nodes_selected
ON 
  nodes_selected.node_id = oepnp.node_id
ORDER BY oepnp.node_id
