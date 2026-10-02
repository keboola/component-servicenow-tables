import csv
import json
import os
import tempfile
import unittest

import mock

from keboola.component.exceptions import UserException

from component import Component


def _write_config(data_dir, parameters):
    os.makedirs(os.path.join(data_dir, "out", "tables"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "in"), exist_ok=True)
    with open(os.path.join(data_dir, "config.json"), "w") as f:
        json.dump({"parameters": parameters, "storage": {}, "image_parameters": {}, "action": "run"}, f)


class TestFieldSizeLimit(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        _write_config(self.tmp.name, {"user": "u", "#password": "p", "server": "https://example.invalid",
                                      "table": "incident"})

    def tearDown(self):
        self.tmp.cleanup()

    def _run_with_fetched_rows(self, rows):
        def fake_fetch_table(table, sysparm_query, sysparm_fields, sysparm_display_value, table_def,
                             temp_folder):
            with open(table_def.full_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["sys_id", "description"])
                writer.writeheader()
                writer.writerows(rows)
            return True

        with mock.patch.dict(os.environ, {"KBC_DATADIR": self.tmp.name}), \
                mock.patch("component.ServiceNowClient") as client_cls:
            client_cls.return_value.fetch_table.side_effect = fake_fetch_table
            comp = Component()
            comp.run()
            return comp

    def test_regular_field_sizes_still_processed(self):
        comp = self._run_with_fetched_rows([{"sys_id": "1", "description": "short"}])
        self.assertEqual(sorted(comp.stored_columns), ["description", "sys_id"])

    def test_field_over_csv_limit_raises_user_exception(self):
        oversized = "x" * (csv.field_size_limit() + 1)
        with self.assertRaises(UserException) as ctx:
            self._run_with_fetched_rows([{"sys_id": "1", "description": oversized}])
        self.assertIn("sysparm_fields", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
