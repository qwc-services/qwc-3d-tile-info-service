import unittest
from urllib.parse import urlencode

from flask import Response, json
from flask.testing import FlaskClient
from flask_jwt_extended import JWTManager

import server

JWTManager(server.app)

class ApiTestCase(unittest.TestCase):
    """Test case for server API"""

    def setUp(self):
        server.app.testing = True
        self.app = FlaskClient(server.app, Response)

    def tearDown(self):
        pass

    # Test GPKG
    def test_existing_tileinfo_gpkg(self):
        response = self.app.get('/objinfo?' + urlencode({'tileset': 'buildings', 'objectid': 'DEHE06200002zcog'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        aliases = list(map(lambda entry: entry['alias'], result))
        self.assertIn('Beschreibung', aliases)
        self.assertIn('Dokumentation', aliases)
        self.assertIn('Gebäudefunktion', aliases)
        self.assertNotIn('gml_id', result)

    def test_missing_tileinfo_gpkg(self):
        response = self.app.get('/objinfo?' + urlencode({'tileset': 'trees', 'objectid': '1234'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        self.assertEqual(result, [])

    def test_existing_default_stylesheet_gpkg(self):
        response = self.app.get('/stylesheet?' + urlencode({'tileset': 'buildings'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        self.assertIn('color', result)

    def test_existing_named_stylesheet_gpkg(self):
        response = self.app.get('/stylesheet?' + urlencode({'tileset': 'buildings', 'stylename': 'default'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        self.assertIn('color', result)

    def test_missing_default_stylesheet_gpkg(self):
        response = self.app.get('/stylesheet?' + urlencode({'tileset': 'trees'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        self.assertEqual(result, {})

    def test_missing_named_stylesheet_gpkg(self):
        response = self.app.get('/stylesheet?' + urlencode({'tileset': 'buildings', 'stylename': 'otherstyle'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        self.assertEqual(result, {})

    # Test postgres
    def test_existing_tileinfo_postgres(self):
        response = self.app.get('/objinfo?' + urlencode({'tileset': 'countries', 'objectid': '6'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        aliases = list(map(lambda entry: entry['alias'], result))
        self.assertIn('GDP per Year', aliases)
        self.assertIn('economy', aliases)
        self.assertIn('name', aliases)
        self.assertNotIn('ogc_fid', aliases)
        self.assertNotIn('level', aliases)

    def test_existing_named_stylesheet_postgres(self):
        response = self.app.get('/stylesheet?' + urlencode({'tileset': 'countries', 'stylename': 'countrycolor'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        self.assertIn('color', result)
