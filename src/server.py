import psycopg2
import psycopg2.extras
import sqlite3
import xml.etree.ElementTree as ET

from flask import Flask, request, jsonify, abort
from flask_restx import Resource, reqparse
from osgeo import ogr
from qwc_services_core.api import Api
from qwc_services_core.api import CaseInsensitiveArgument
from qwc_services_core.app import app_nocache
from qwc_services_core.auth import auth_manager, optional_auth
from qwc_services_core.tenant_handler import (
    TenantHandler, TenantPrefixMiddleware, TenantSessionInterface)
from qwc_services_core.runtime_config import RuntimeConfig


# Flask application
app = Flask(__name__)
app_nocache(app)
api = Api(app, version='1.0', title='3D Tile Info API',
          description="""API for 3D Tile Info service.

Returns infos for 3D Tile objects.
          """,
          default_label='Tile info operations', doc='/api/')
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'

# disable verbose 404 error message
app.config['ERROR_404_HELP'] = False

auth = auth_manager(app, api)

tenant_handler = TenantHandler(app.logger)
app.wsgi_app = TenantPrefixMiddleware(app.wsgi_app)
app.session_interface = TenantSessionInterface()

# request parser
objinfo_parser = reqparse.RequestParser(argument_class=CaseInsensitiveArgument)
objinfo_parser.add_argument('tileset', required=True)
objinfo_parser.add_argument('objectid', required=True)

stylesheet_parser = reqparse.RequestParser(argument_class=CaseInsensitiveArgument)
stylesheet_parser.add_argument('tileset', required=True)
stylesheet_parser.add_argument('stylename', required=False)


# routes
@api.route('/objinfo')
class ObjInfo(Resource):
    """ObjInfo class

    Returns infos for 3D Tile objects.
    """

    @api.doc('objinfo')
    @api.param('tileset', 'The tileset name')
    @api.param('objectid', 'The object id')
    @api.expect(objinfo_parser)
    @optional_auth
    def get(self):
        args = objinfo_parser.parse_args()
        tileset = args["tileset"]
        objectid = args["objectid"]

        tenant = tenant_handler.tenant()
        config_handler = RuntimeConfig("tileinfo", app.logger)
        config = config_handler.tenant_config(tenant)

        info_datasets = config.get("info_datasets", {})
        dataset_config = info_datasets.get(tileset)

        if not dataset_config:
            app.logger.debug("No dataset configured for tileset %s" % tileset)
            return jsonify([])

        attribute_aliases = dataset_config.get("attribute_aliases", {})
        attribute_blacklist = dataset_config.get("attribute_blacklist", [])

        attributes = []
        if dataset_config.get("type") == "gpkg":

            ds = ogr.Open(dataset_config.get("dataset"))
            if ds is None:
                app.logger.warning("Failed to open dataset '%s'" % dataset_config.get("dataset"))
                abort(500)

            # Get the requested layer
            layer = ds.GetLayerByName(dataset_config.get("layername"))
            if layer is None:
                app.logger.warning("Cannot find layer '%s' in dataset '%s'" % (dataset_config.get("layername"), dataset_config.get("dataset")))
                abort(500)

            idfield = dataset_config.get("idfield")
            if not idfield:
                app.logger.warning("No id field configured for dataset '%s'" % dataset_config.get("dataset"))
                abort(500)

            filter_expr = f"{idfield} = '{objectid}'"
            layer.SetAttributeFilter(filter_expr)

            feature = layer.GetNextFeature()
            if not feature:
                app.logger.debug("No matches for %s" % filter_expr)
                return jsonify([])

            defn = layer.GetLayerDefn()
            for i in range(defn.GetFieldCount()):
                field_defn = defn.GetFieldDefn(i)
                field_name = field_defn.GetName()
                if field_name in attribute_blacklist:
                    continue
                attributes.append({
                    "name": field_name,
                    "alias": attribute_aliases.get(field_name, field_name),
                    "value": feature.GetField(field_name)
                })
        elif dataset_config.get("type") == "postgres":
            conn = psycopg2.connect(dataset_config.get("dataset"))
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            # Get name of geometry column
            schema, table = ("public." + dataset_config.get("layername")).split(".")[-2:]
            sql = """
                SELECT f_geometry_column
                FROM geometry_columns
                WHERE f_table_schema = '{schema}'
                AND f_table_name = '{table}'
            """.format(schema=schema, table=table)
            cursor.execute(sql)
            row = cursor.fetchone()
            geom_column = row[0] if row else None
            app.logger.debug("Detected geometry column '%s'" % geom_column)
            sql = "SELECT * from {layername} WHERE {idfield} = %s".format(
                layername=dataset_config.get("layername"),
                idfield=dataset_config.get("idfield")
            )
            cursor.execute(sql, (objectid,))
            row = cursor.fetchone()
            for field_name, value in row.items():
                if field_name in attribute_blacklist or field_name == geom_column:
                    continue
                attributes.append({
                    "name": field_name,
                    "alias": attribute_aliases.get(field_name, field_name),
                    "value": value
                })
            cursor.close()
            conn.close()
        else:
            app.logger.warning("Unsupported dataset type '%s'" % dataset_config.get("type"))
            abort(500)

        return jsonify(attributes)


@api.route("/stylesheet")
class Stylesheet(Resource):

    @api.doc('stylesheet')
    @api.param('tileset', 'The tileset name')
    @api.param('stylename', 'The style name, defaults to "default"')
    @api.expect(stylesheet_parser)
    @optional_auth
    def get(self):
        args = stylesheet_parser.parse_args()
        tileset = args["tileset"]
        stylename = args["stylename"] or "default"

        tenant = tenant_handler.tenant()
        config_handler = RuntimeConfig("tileinfo", app.logger)
        config = config_handler.tenant_config(tenant)

        info_datasets = config.get("info_datasets", {})
        dataset_config = info_datasets.get(tileset)

        if not dataset_config:
            app.logger.debug("No dataset configured for tileset %s" % tileset)
            return jsonify({})

        style_config = dataset_config.get("styles", {}).get(stylename)
        if not style_config:
            app.logger.debug("No style with name %s configured for tileset %s" % (stylename, tileset))
            return jsonify({})

        # Read SLD via query / filename
        sld_xml = None
        if style_config.get("query"):
            if dataset_config.get("type") == "gpkg":
                conn = sqlite3.connect(dataset_config.get("dataset"))
            elif dataset_config.get("type") == "postgres":
                conn = psycopg2.connect(dataset_config.get("dataset"))
            else:
                app.logger.warning("Querying style via SQL only supported for gpkg/postgres")
                return jsonify({})
            cursor = conn.cursor()
            try:
                cursor.execute(style_config["query"])
                row = cursor.fetchone()
                sld_xml = row[0] if row else None
            except:
                app.logger.warning("Failed to query stylesheet from tileset '%s' via '%s'" % (tileset, style_config["query"]))
            conn.close()
        elif style_config.get("filename"):
            try:
                with open(style_config["filename"]) as fh:
                    sld_xml = fh.read()
            except Exception as e:
                app.logger.debug(str(e))
                app.logger.warning("Failed to query stylesheet from tileset '%s' from filename '%s'" % (tileset, style_config["filename"]))

        if sld_xml is None:
            app.logger.warning("No stylesheet found for tileset '%s'" % tileset)
            return jsonify({})

        # Convert SLD to 3d tiles style language
        namespaces = {
            'sld': 'http://www.opengis.net/sld',
            'se': 'http://www.opengis.net/se',
            'ogc': 'http://www.opengis.net/ogc',
            'xlink': 'http://www.w3.org/1999/xlink',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }
        root = ET.fromstring(sld_xml)
        conditions = []

        have_true = False
        for rule in root.findall('.//se:Rule', namespaces):
            # Determine fill color
            color_elem = rule.find('.//se:Fill/se:SvgParameter[@name="fill"]', namespaces)
            fill_color = color_elem.text.strip() if color_elem is not None else "#ffffff"

            # Check for filters
            filter_elem = rule.find('ogc:Filter', namespaces)
            else_filter = rule.find('se:ElseFilter', namespaces)

            if filter_elem is not None and len(filter_elem) > 0:
                condition_str = self.parse_ogc_filter(filter_elem[0], namespaces)
            elif else_filter is not None:
                condition_str = "true"
                have_true = True
            else:
                condition_str = "true"
                have_true = True

            conditions.append([condition_str, f"color('{fill_color}')"])

        # Add a fallback
        if not have_true:
            conditions.append(["true", "color('white')"])

        style_json = {
            "defines": {},
            "color": {
                "conditions": conditions
            }
        }

        return jsonify(style_json)

    def parse_ogc_filter(self, filter_elem, ns):
        """Convert basic OGC filters to 3D Tiles style condition strings."""
        if filter_elem.tag == "{%s}Or" % ns["ogc"]:
            return "(" + " || ".join(
                self.parse_ogc_filter(child, ns) for child in filter_elem
            ) + ")"
        elif filter_elem.tag == "{%s}And" % ns["ogc"]:
            return "(" + " && ".join(
                self.parse_ogc_filter(child, ns) for child in filter_elem
            ) + ")"
        elif filter_elem.tag == "{%s}Not" % ns["ogc"] and len(filter_elem) == 1:
            return "!(" + self.parse_ogc_filter(child, ns) + ")"
        else:
            prop_name = filter_elem.find('ogc:PropertyName', ns).text

            if filter_elem.tag == "{%s}PropertyIsEqualTo" % ns["ogc"]:
                operator = "==="
            elif filter_elem.tag == "{%s}PropertyIsNotEqualTo" % ns["ogc"]:
                operator = "!=="
            elif filter_elem.tag == "{%s}PropertyIsLessThan" % ns["ogc"]:
                operator = "<"
            elif filter_elem.tag == "{%s}PropertyIsGreaterThan" % ns["ogc"]:
                operator = ">"
            elif filter_elem.tag == "{%s}PropertyIsLessThanOrEqualTo" % ns["ogc"]:
                operator = "<="
            elif filter_elem.tag == "{%s}PropertyIsGreaterThanOrEqualTo" % ns["ogc"]:
                operator = ">="
            elif filter_elem.tag == "{%s}PropertyIsBetween" % ns["ogc"]:
                lower = filter_elem.find('ogc:LowerBoundary', ns).text
                upper = filter_elem.find('ogc:UpperBoundary', ns).text
                return f"(${{{prop_name}}} >= ${lower} && === ${{{prop_name}}} <= ${upper})"
            elif filter_elem.tag == "{%s}PropertyIsNull" % ns["ogc"]:
                return f"${{{prop_name}}} === null"
            else:
                return "false"

            literal = filter_elem.find('ogc:Literal', ns).text
            return f"${{{prop_name}}} {operator} {literal}"

""" readyness probe endpoint """
@app.route("/ready", methods=['GET'])
def ready():
    return jsonify({"status": "OK"})


""" liveness probe endpoint """
@app.route("/healthz", methods=['GET'])
def healthz():
    return jsonify({"status": "OK"})


# local webserver
if __name__ == "__main__":
    from flask_cors import CORS
    CORS(app)
    app.run(host='localhost', port=5016, debug=True)
