import argparse
import os
import sys

from deploy_server import connect, run, safe_print


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a read-only command on the vocab-app server.")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--command", required=True)
    args = parser.parse_args()

    password = os.environ.get("DEPLOY_PASSWORD")
    if not password:
        raise SystemExit("DEPLOY_PASSWORD environment variable is required.")

    client = connect(args.host, args.user, password)
    try:
        safe_print(run(client, args.command))
    except Exception as exc:
        safe_print(str(exc))
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
