import argparse
import os
import posixpath
import sys
import tarfile
import tempfile
import time
from pathlib import Path

import paramiko
from paramiko.ssh_exception import AuthenticationException


EXCLUDED_DIRS = {
    ".git",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
}

EXCLUDED_FILES = {
    "tsconfig.tsbuildinfo",
}


def safe_print(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
    sys.stdout.flush()


def should_exclude(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts) or path.name in EXCLUDED_FILES


def create_archive(project_dir: Path) -> Path:
    archive_path = Path(tempfile.gettempdir()) / f"vocab-app-{int(time.time())}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        for path in project_dir.rglob("*"):
            relative_path = path.relative_to(project_dir)
            if should_exclude(relative_path):
                continue
            tar.add(path, arcname=str(relative_path))

    return archive_path


def connect(host: str, user: str, password: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=20,
            look_for_keys=False,
            allow_agent=False,
        )
    except AuthenticationException:
        transport = paramiko.Transport((host, 22))
        transport.start_client(timeout=20)

        def handler(title, instructions, prompts):
            return [password for _prompt, _echo in prompts]

        transport.auth_interactive(user, handler)
        client._transport = transport

    return client


def run(client: paramiko.SSHClient, command: str, input_text: str | None = None) -> str:
    stdin, stdout, stderr = client.exec_command(command, get_pty=False)
    if input_text is not None:
        stdin.write(input_text)
        stdin.flush()
        stdin.channel.shutdown_write()
    exit_code = stdout.channel.recv_exit_status()
    output = stdout.read().decode("utf-8", errors="replace")
    error = stderr.read().decode("utf-8", errors="replace")

    if exit_code != 0:
        raise RuntimeError(
            f"Command failed with exit code {exit_code}\nCOMMAND:\n{command}\nSTDOUT:\n{output}\nSTDERR:\n{error}"
        )

    return output + error


def deploy(host: str, user: str, password: str, project_dir: Path, remote_dir: str) -> None:
    archive_path = create_archive(project_dir)
    remote_archive = posixpath.join("/tmp", archive_path.name)
    release_dir = f"{remote_dir}.release"
    backup_dir = f"{remote_dir}.backup"

    print(f"Created archive: {archive_path}")
    client = connect(host, user, password)

    try:
        print("Connected to server")
        run(client, "docker --version")
        run(client, "docker compose version")

        with client.open_sftp() as sftp:
            print(f"Uploading archive to {remote_archive}")
            sftp.put(str(archive_path), remote_archive)

        deploy_command = f"""
set -e
sudo -S -p '' true
rm -rf {release_dir}
mkdir -p {release_dir}
tar -xzf {remote_archive} -C {release_dir}
if [ -d {remote_dir} ]; then
  rm -rf {backup_dir}
  mv {remote_dir} {backup_dir}
fi
mv {release_dir} {remote_dir}
cd {remote_dir}
sudo docker compose -f docker-compose.server.yml up -d --build
sudo docker compose -f docker-compose.server.yml ps
""".strip()

        print("Running remote Docker deployment")
        safe_print(run(client, deploy_command, password + "\n"))
    finally:
        client.close()
        archive_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy vocab-app to a remote Ubuntu server.")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--remote-dir", default="/home/ubuntu/vocab-app")
    args = parser.parse_args()

    password = os.environ.get("DEPLOY_PASSWORD")
    if not password:
        raise SystemExit("DEPLOY_PASSWORD environment variable is required.")

    project_dir = Path(__file__).resolve().parents[1]
    deploy(args.host, args.user, password, project_dir, args.remote_dir)


if __name__ == "__main__":
    main()
