from dotenv import load_dotenv
import datetime
import os
import subprocess

load_dotenv("./.env")

date_str = datetime.datetime.now().strftime("%Y%m%d")

backup_file = f"./backup{date_str}.sql"
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
