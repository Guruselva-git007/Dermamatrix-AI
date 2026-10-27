"""Reused PID regression: fake binaries, isolated temporary directories only."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class MySQLLauncherIdentity(unittest.TestCase):
    def test_reused_non_mysql_pid_does_not_skip_start_or_signal_other_process(self):
        source=Path(__file__).resolve().parents[1]/'scripts/run_local_mysql.sh'
        with tempfile.TemporaryDirectory(prefix='dmx-launch-test-') as temp:
            backend=Path(temp);scripts=backend/'scripts';scripts.mkdir()
            shutil.copy2(source,scripts/source.name)
            data=backend/'.local-mysql';(data/'data/mysql').mkdir(parents=True)
            (data/'mysql.pid').write_text(str(os.getpid()))
            (data/'mysql.sock.lock').write_text(str(os.getpid()))
            (backend/'.env').write_text('MYSQL_PASSWORD=synthetic-only\nMYSQL_PORT=0\n')
            called=backend/'called.txt';server=backend/'mysqld';client=backend/'mysql'
            server.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "'+str(called)+'"\n')
            client.write_text('#!/bin/sh\ncat >/dev/null\nexit 0\n');server.chmod(0o700);client.chmod(0o700)
            # SELECT probe has no stdin; fake client must not consume unittest stdin.
            client.write_text('#!/bin/sh\ncase "$*" in *"SELECT 1"*) exit 0;; esac\ncat >/dev/null\nexit 0\n')
            result=subprocess.run(['bash',str(scripts/source.name)],env={**os.environ,'MYSQLD_BIN':str(server),'MYSQL_BIN':str(client)},capture_output=True,text=True,timeout=10,stdin=subprocess.DEVNULL)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(called.is_file())
            self.assertFalse((data/'mysql.sock.lock').exists())
            self.assertIn('--datadir='+str(data/'data'),called.read_text())
            self.assertIn('--mysqlx-socket='+str(data/'mysqlx.sock'),called.read_text())
            os.kill(os.getpid(),0)  # The unrelated recorded process remains alive.
