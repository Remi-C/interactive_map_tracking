##interactive_map_tracking
![](https://raw.githubusercontent.com/wiki/Remi-C/interactive_map_tracking/images/plugin/logo_LQ.png) A QGIS 2.6 plugin to track camera of user , AND/OR to autocommit/refresh edit on PostGIS vector layer
This QGIS 2.6 plug-in has been developed by Lionel Atty from IGN (France).

Go to the [project wiki](https://github.com/Remi-C/interactive_map_tracking/wiki) for more information !

This plug-in was designed to allow __concurrent editing awareness or history of editing__ (tracking), and to enable QGIS to play well with PostGIS database using trigger to __reconstruct geometry on the fly__
###feature
This plug-in add 2 features to QGIS, the user choose what feature he uses



![](/Remi-C/interactive_map_tracking.wiki/images/plugin/multi_user_tracking_edited_LQ.png)

![](/Remi-C/interactive_map_tracking.wiki/images/plugin/edition_time_with_hexagonal_grid_LQ.png)

![](/Remi-C/interactive_map_tracking.wiki/images/plugin/auto_save_combined.png)


####tracking the position 
* each time the user change its position on QGIS map canvas, the screen rectangle is saved along with a user id and a timestamp. That is, if the user zoom level is compatible with edition (parameter)
* with correct QGIS styling, this enable to see : 
  + where the other users __are editing__ so two people won't hopefully edit the same area
  + where the other users (and self) __were editing__, so an user won't come and edit the same area twice
* Moreover, this tracking data can be analysed to produce : 
  + a map of editing time (gives the place where editing was short/long)
  + Reliable stats on editing time and area edited per user, which is essential in a benchmark

####autosave and refresh after an edit
* QGIS uses a sophisticated Do/Undo mechanism with a delayed writing system. However, when working with a data base that generates geometry on the fly (trigger), it is essential to commit each change immediately.
* The plug-in does exactly that : each modification (geometry or attribute) is saved immediately to the layer, and the canvas is re-rendered.
* this instantaneous commit allow to __create new user interaction__ that are within the database, as opposed to be within QGIS. Thus, this interactions can be used in other GIS software, and can be much more complex.
 
