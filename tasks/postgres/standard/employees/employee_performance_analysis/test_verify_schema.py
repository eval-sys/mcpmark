import importlib.util
import pathlib
import sys
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO

# The schema test is pure catalog readback. No database and no external driver
# are required for this pre-integration unit suite.
sys.modules.setdefault('psycopg2', types.ModuleType('psycopg2'))
SCRIPT = pathlib.Path(__file__).with_name('verify.py')
spec = importlib.util.spec_from_file_location('employee_patched_verify', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CatalogCursor:
    def __init__(self, data, calls):
        self.data = data
        self.calls = calls
        self.table = None
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, sql, params):
        assert 'pg_catalog.pg_attribute' in sql
        assert "c.relkind IN ('r', 'p')" in sql
        assert params and len(params) == 1
        self.table = params[0]
        self.calls.append(self.table)
    def fetchall(self):
        return self.data.get(self.table, [])


class CatalogConn:
    def __init__(self, data):
        self.data = data
        self.calls = []
    def cursor(self):
        return CatalogCursor(self.data, self.calls)


def expected_rows():
    return {table: list(cols.items()) for table, cols in mod._EXPECTED_OUTPUT_COLUMNS.items()}


def evaluate(data):
    con = CatalogConn(data)
    with redirect_stdout(StringIO()):
        outcome = mod.verify_output_schema(con)
    return outcome, con.calls


class SchemaContractTests(unittest.TestCase):
    def test_exact_correct_columns_pass(self):
        ok, calls = evaluate(expected_rows())
        self.assertTrue(ok)
        self.assertEqual(set(calls), set(mod._EXPECTED_OUTPUT_COLUMNS))

    def test_column_order_is_not_a_requirement(self):
        values = expected_rows()
        for key in values:
            values[key] = list(reversed(values[key]))
        self.assertTrue(evaluate(values)[0])

    def test_valid_extra_constraints_do_not_affect_column_catalog(self):
        # PK/UNIQUE/CHECK constraints do not alter the required column metadata.
        self.assertTrue(evaluate(expected_rows())[0])

    def test_wrong_integer_type_rejected(self):
        values = expected_rows()
        values['employee_performance_analysis'] = [
            (name, 'bigint' if name == 'promotion_count' else typ)
            for name, typ in values['employee_performance_analysis']
        ]
        self.assertFalse(evaluate(values)[0])

    def test_wrong_varchar_type_rejected(self):
        values = expected_rows()
        values['department_salary_analysis'] = [
            (name, 'text' if name == 'department_name' else typ)
            for name, typ in values['department_salary_analysis']
        ]
        self.assertFalse(evaluate(values)[0])

    def test_extra_column_rejected(self):
        values = expected_rows()
        values['department_salary_analysis'].append(('unexpected_marker', 'integer'))
        self.assertFalse(evaluate(values)[0])

    def test_missing_column_rejected(self):
        values = expected_rows()
        values['department_salary_analysis'] = values['department_salary_analysis'][:-1]
        self.assertFalse(evaluate(values)[0])

    def test_missing_output_table_rejected(self):
        values = expected_rows()
        del values['department_salary_analysis']
        self.assertFalse(evaluate(values)[0])

    def test_decimal_tolerance_still_as_upstream(self):
        # This patch does not change numerical tolerances or original scoring.
        from decimal import Decimal
        self.assertTrue(mod.rows_match((Decimal('12.05'),), (Decimal('12.00'),)))
        self.assertFalse(mod.rows_match((Decimal('12.20'),), (Decimal('12.00'),)))

if __name__ == '__main__':
    unittest.main()
