from dotenv import load_dotenv
import argparse
import datetime
import os
import subprocess

parser = argparse.ArgumentParser(
    description="Creates a backup file with a date key in the file name"
)

parser.add_argument("--env", help="Env full file path")
parser.add_argument("--backup", help="Backup directory path")

args = parser.parse_args()

load_dotenv(args.env)

date_str = datetime.datetime.now().strftime("%Y%m%d")

backup_file = f"{args.backup}/backup{date_str}.sql"
mysql_password = os.getenv("DB_PASSWORD")

cmd = [
    "docker",
    "exec",
    "hypertrophy-mysql",
    "mysqldump",
    "-u",
    "root",
    f"-p{mysql_password}",
    "--all-databases",
]

with open(backup_file, "w") as f:
    subprocess.run(cmd, stdout=f, check=True)
