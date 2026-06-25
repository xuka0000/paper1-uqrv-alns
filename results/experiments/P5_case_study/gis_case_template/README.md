# GIS Case Input Schema

Use this folder when replacing the synthetic corridor case with a real or GIS-grounded transmission-line case.

Coordinates must be projected kilometer coordinates (`x`, `y`), not raw longitude/latitude. Convert GIS geometry to a local projected CRS first so that route and energy distances remain meaningful.

Required files:

- `towers.csv`: `id,x,y,risk,value,service_time,payload,segment`
- `stops.csv`: `id,x,y`
- `weather.csv`: `wind_speed,wind_direction,temperature,uncertainty,battery_capacity,vehicle_count,uav_count,vehicle_speed_kmph,drone_speed_kmph`

Evidence boundary: loading a GIS case does not by itself create field validation. Field-validation claims require real flight logs, inspection outcomes, or utility-provided operational records.
