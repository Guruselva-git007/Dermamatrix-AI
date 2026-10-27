"""CMS AES-GCM database backup and guarded empty-synthetic restore exercise.

No scheduler, uploads or cloud storage. Use a reviewed recipient certificate;
keep its private key separate. MySQL credentials use a temporary 0600 option
file, never command arguments. Decryption must authenticate fully before SQL
is passed to MySQL. Restore refuses every nonempty or non-synthetic target.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import pymysql


def settings():
    return dict(host=os.getenv('MYSQL_HOST') or os.getenv('MYSQLHOST') or '127.0.0.1', port=int(os.getenv('MYSQL_PORT') or os.getenv('MYSQLPORT') or '3306'), user=os.getenv('MYSQL_USER') or os.getenv('MYSQLUSER') or 'root', password=os.getenv('MYSQL_PASSWORD') or os.getenv('MYSQLPASSWORD') or '', database=os.getenv('MYSQL_DATABASE') or os.getenv('MYSQLDATABASE') or '')


def option_file(folder, config):
    path=folder/'mysql-options.cnf'
    def escaped(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:
        stream.write('[client]\n'+'\n'.join(f'{key}={escaped(config[key])}' for key in ['host','port','user','password'])+'\n')
    return path


def backup(destination, certificate, config):
    if destination.exists():raise ValueError('Choose a new backup filename; existing files are preserved.')
    executable=shutil.which('mysqldump')
    if not executable:raise ValueError('mysqldump is required.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dmx-backup-') as temp:
        options=option_file(Path(temp),config)
        fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            with os.fdopen(fd,'wb') as encrypted:
                dump=subprocess.Popen([executable,'--defaults-extra-file='+str(options),'--single-transaction','--no-tablespaces','--skip-add-drop-table',config['database']],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                cipher=subprocess.run(['openssl','cms','-encrypt','-aes-256-gcm','-binary','-outform','DER','-recip',str(certificate)],stdin=dump.stdout,stdout=encrypted,stderr=subprocess.PIPE)
                dump.stdout.close();_,errors=dump.communicate()
                if cipher.returncode or dump.returncode:raise ValueError('Encrypted database copy failed; inspect tool configuration. No SQL or credential details are logged.')
        except Exception:
            destination.unlink(missing_ok=True);raise


def restore(source, certificate, private_key, target, config):
    if not re.fullmatch(r'[a-zA-Z0-9_]+_restore_synthetic',target) or target==config['database']:
        raise ValueError('Restore is restricted to a distinct *_restore_synthetic database.')
    target_config={**config,'database':target}
    connection=pymysql.connect(**target_config)
    try:
        with connection.cursor() as cursor:
            cursor.execute('SHOW TABLES')
            if cursor.fetchall():raise ValueError('Restore target must be empty. Existing tables are preserved.')
    finally:connection.close()
    with tempfile.TemporaryDirectory(prefix='dmx-restore-') as temp:
        folder=Path(temp);options=option_file(folder,config);plain=folder/'authenticated.sql'
        fd=os.open(plain,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:
            result=subprocess.run(['openssl','cms','-decrypt','-binary','-inform','DER','-in',str(source),'-recip',str(certificate),'-inkey',str(private_key)],stdout=stream,stderr=subprocess.PIPE)
        if result.returncode:raise ValueError('Backup authentication/decryption failed. No SQL was executed.')
        with plain.open('rb') as stream:
            result=subprocess.run(['mysql','--defaults-extra-file='+str(options),target],stdin=stream,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if result.returncode:raise ValueError('Synthetic restore failed. Preserve evidence and inspect the isolated target; no automatic destructive retry.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['backup','restore'])
    parser.add_argument('--file',required=True,type=Path)
    parser.add_argument('--certificate',required=True,type=Path)
    parser.add_argument('--private-key',type=Path)
    parser.add_argument('--target')
    args=parser.parse_args();config=settings()
    if not config['database']:parser.exit(2,'Explicit source database configuration is required.\n')
    try:
        if args.mode=='backup':backup(args.file,args.certificate,config)
        else:
            if not args.private_key or not args.target:raise ValueError('Restore requires a private key and an explicit empty synthetic target.')
            restore(args.file,args.certificate,args.private_key,args.target,config)
        print('Encrypted copy completed.' if args.mode=='backup' else 'Synthetic restore completed; verify table/row equality separately.')
    except ValueError as error:parser.exit(1,str(error)+'\n')
