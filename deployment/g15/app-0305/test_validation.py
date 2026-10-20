import importlib.util
import os
import pathlib
import sys
import types
import unittest


def load_server():
    if 'psycopg' not in sys.modules:
        psycopg = types.ModuleType('psycopg')
        psycopg.connect = None
        psycopg.errors = types.SimpleNamespace(UniqueViolation=RuntimeError)
        rows = types.ModuleType('psycopg.rows')
        rows.dict_row = object()
        json_types = types.ModuleType('psycopg.types.json')
        json_types.Jsonb = lambda value: value
        sys.modules.update({'psycopg': psycopg, 'psycopg.rows': rows, 'psycopg.types': types.ModuleType('psycopg.types'), 'psycopg.types.json': json_types})
    os.environ.update(GROUP_NAME='group15', APP_SECRET='test-secret', POSTGRES_HOST='db', POSTGRES_PORT='5432', POSTGRES_DB='test', POSTGRES_USER='test', POSTGRES_PASSWORD='test')
    spec = importlib.util.spec_from_file_location('module_0305_server', pathlib.Path(__file__).with_name('server.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = load_server()


class ValidationTests(unittest.TestCase):
    def test_demo_total_is_discount_then_tax(self):
        clean, errors = server.validate(server.demo(1))
        self.assertEqual({}, errors)
        self.assertEqual('100000.00', str(clean['subtotal']))
        self.assertEqual('95000.00', str(clean['subtotal'] - clean['discount_amount']))
        self.assertEqual('99750.00', str(clean['total']))

    def test_rejects_cross_field_and_format_errors(self):
        data = server.demo(1)
        data.update(application_no='abc', end_date='2026-01-01', budget=-1, meeting_value='http://unsafe.example', tax_id='123', confirmed=False)
        _, errors = server.validate(data)
        for key in ('application_no', 'end_date', 'budget', 'meeting_value', 'tax_id', 'confirmed'):
            self.assertIn(key, errors)

    def test_rejects_more_than_twelve_details(self):
        data = server.demo(1)
        data['details'] = data['details'] * 13
        _, errors = server.validate(data)
        self.assertIn('details', errors)


if __name__ == '__main__':
    unittest.main()
