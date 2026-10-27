import os
from pathlib import Path
import subprocess
import sys
import unittest

class ExplicitMigrationStartup(unittest.TestCase):
    def test_normal_import_cannot_open_database_or_run_schema_ddl(self):
        backend=Path(__file__).resolve().parents[1]
        script="import pymysql; pymysql.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('Unexpected database startup')); import app; print('No startup database mutation')"
        result=subprocess.run([sys.executable,'-c',script],cwd=backend,env={**os.environ,'DERMAMATRIX_INITIALISE_SCHEMA':'false','DERMAMATRIX_CONSUMER_ENABLED':'false'},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('No startup database mutation',result.stdout)
