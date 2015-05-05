-------------------------------
--Lionel-A
--SIDT IGN 04/2015
-------------------------------

------
-- for TrafiPollu soft.
-- retrieve (dump) 'informations' from nodes selected in QGIS client

SELECT
  nodes_selected.node_id, array_agg(oepnp.edge_id1) as edge_ids
FROM 
  bdtopo_topological.ordered_edges_per_node_pair as oepnp
JOIN
  test.nodes_selected AS nodes_selected
ON 
  nodes_selected.node_id = oepnp.node_id
GROUP BY nodes_selected.node_id
