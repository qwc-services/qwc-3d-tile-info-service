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
        self.assertIn('Beschreibung', result)
        self.assertIn('Dokumentation', result)
        self.assertIn('Gebäudefunktion', result)
        self.assertNotIn('gml_id', result)

    def test_missing_tileinfo_gpkg(self):
        response = self.app.get('/objinfo?' + urlencode({'tileset': 'trees', 'objectid': '1234'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        self.assertEqual(result, {})

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
        self.assertIn('GDP per Year', result)
        self.assertIn('economy', result)
        self.assertIn('name', result)
        self.assertNotIn('ogc_fid', result)
        self.assertNotIn('level', result)

    def test_existing_named_stylesheet_postgres(self):
        response = self.app.get('/stylesheet?' + urlencode({'tileset': 'countries', 'stylename': 'countrycolor'}))
        self.assertEqual(200, response.status_code, "Status code is not OK")
        result = json.loads(response.data)
        self.assertIn('color', result)
