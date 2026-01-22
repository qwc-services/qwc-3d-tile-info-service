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

### JSON config

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

See the [schema definition](schemas/qwc-3d-tile-info-service.json) for the full set of supported config variables.

### Environment variables

Config options in the config file can be overridden by equivalent uppercase environment variables.

Run locally
-----------

Install dependencies and run:

    # Install python3-gdal in system package
    apt/dnf install python3-gdal
    
    # Setup venv with --system-site-packages for python3-gdal
    uv venv --system-site-packages .venv
    
    export CONFIG_PATH=<CONFIG_PATH>
    uv run src/server.py

To use configs from a `qwc-docker` setup, set `CONFIG_PATH=<...>/qwc-docker/volumes/config`.

Set `FLASK_DEBUG=1` for additional debug output.

Set `FLASK_RUN_PORT=<port>` to change the default port (default: `5000`).

API documentation:

    http://localhost:$FLASK_RUN_PORT/api/
    
Docker usage
------------

The Docker image is published on [Dockerhub](https://hub.docker.com/r/sourcepole/qwc-3d-tile-info-service).

See sample [docker-compose.yml](https://github.com/qwc-services/qwc-docker/blob/master/docker-compose-example.yml) of [qwc-docker](https://github.com/qwc-services/qwc-docker).
