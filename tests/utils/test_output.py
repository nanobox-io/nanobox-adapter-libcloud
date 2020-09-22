from nanobox_libcloud.utils import output
from tests import NanoboxLibcloudTestCase


class OutputUtilTestCase(NanoboxLibcloudTestCase):
    def test_success(self):
        with self.subTest(check='Empty Success'):
            out, code, headers = output.success('')
            self.assertEqual('""', out)
            self.assertEqual(200, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Success String'):
            out, code, headers = output.success('test')
            self.assertEqual('"test"', out)
            self.assertEqual(200, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Success Object'):
            out, code, headers = output.success({'id': 'test'})
            self.assertIn('"id":', out)
            self.assertEqual(200, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Success Object with 201'):
            out, code, headers = output.success({'id': 'test'}, 201)
            self.assertIn('"id":', out)
            self.assertEqual(201, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Redirect'):
            out, code, headers = output.success(None, 302)
            self.assertEqual('null', out)
            self.assertEqual(302, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

    def test_failure(self):
        with self.subTest(check='Empty Failure'):
            out, code, headers = output.failure('')
            self.assertEqual('{\n  "errors": [\n    ""\n  ]\n}', out)
            self.assertEqual(400, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Failure String'):
            out, code, headers = output.failure('test')
            self.assertEqual('{\n  "errors": [\n    "test"\n  ]\n}', out)
            self.assertEqual(400, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Failure Object'):
            out, code, headers = output.failure({'id': 'test'})
            self.assertEqual('{\n  "errors": {\n    "id": "test"\n  }\n}', out)
            self.assertEqual(400, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Failure Exception'):
            out, code, headers = output.failure(Exception('test'))
            self.assertEqual('{\n  "errors": "Exception(\'test\',)"\n}', out)
            self.assertEqual(400, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Failure Object with 401'):
            out, code, headers = output.failure({'id': 'test'}, 401)
            self.assertEqual('{\n  "errors": {\n    "id": "test"\n  }\n}', out)
            self.assertEqual(401, code)
            self.assertIn(('Content-Type', 'application/json'), headers)

        with self.subTest(check='Redirect'):
            out, code, headers = output.failure(None, 302)
            self.assertEqual('{\n  "errors": null\n}', out)
            self.assertEqual(302, code)
            self.assertIn(('Content-Type', 'application/json'), headers)
