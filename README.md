[![](https://github.com/qwc-services/qwc-3d-tile-info-service/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-3d-tile-info-service/actions)
[![docker](https://img.shields.io/docker/v/sourcepole/qwc-3d-tile-info-service?label=Docker%20image&sort=semver)](https://hub.docker.com/r/sourcepole/qwc-3d-tile-info-service)

QWC 3D Tile Info Service
========================

Provides additional data for 3D tiles tilesets, sourced from a GeoPackage or Postgres dataset:

- Object info, via `/objinfo?tileset=<tileset_name>&objectid=<object_id>`
- 3D tiles stylesheets, generated from 2D SLD styles, via `/stylesheet?tileset=<tileset_name>&stylename=<stylename>`

This service implements a backend which can be referenced as `tileInfoServiceUrl` in the QWC View3D plugin configuration, `tileset_name` being the name of the tileset as configured in the `tiles3d` dataset entries in the themes configuration, see [View3D configuration](https://qwc-services.github.io/master/references/qwc2_plugins/#view3d).

Configuration
-------------

The static config files are stored as JSON files in `$CONFIG_PATH` with subdirectories for each tenant,
e.g. `$CONFIG_PATH/default/*.json`. The default tenant name is `default`.

### TileInfo Service config

* [JSON schema](schemas/qwc-3d-tile-info-service.json)
* File location: `$CONFIG_PATH/<tenant>/tileinfoConfig.json`

Example:

```json
{
  "$schema": "https://raw.githubusercontent.com/qwc-services/qwc-3d-tile-info-service/master/schemas/qwc-3d-tile-info-service.json",
  "service": "mapinfo",
  "config": {
    "info_datasets": {
      "<tileset_name>" : {
        "dataset": "<dataset path or DB URL>",
        "type": "<gpkg|postgres>",
        "layername": "<layer name in dataset>",
        "idfield": "<id field name in dataset>",
        "attribute_aliases": {
          "<fieldname>": "<displayname>",
          ...
        },
        "attribute_blacklist": [
          "<fieldname>"
        ],
        "styles": {
          "<stylename>": {
            "query": "SELECT styleSLD FROM layer_styles WHERE f_table_name = '<layer name>'",
            // or
            "filename": "<sld path>"
          }
        }
      }
    }
  }
}
```

### Environment variables

Config options in the config file can be overridden by equivalent uppercase environment variables.

Usage
-----

Run as

    python src/server.py

API documentation:

    http://localhost:5016/api/
    
Docker usage
------------

See sample [docker-compose.yml](https://github.com/qwc-services/qwc-docker/blob/master/docker-compose-example.yml) of [qwc-docker](https://github.com/qwc-services/qwc-docker).

Development
-----------

Install dependencies and run service:

    uv run src/server.py

With config path:

    CONFIG_PATH=/PATH/TO/CONFIGS/ uv run src/server.py
