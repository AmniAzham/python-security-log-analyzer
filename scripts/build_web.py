"""Build Firebase assets against an explicit public API. Never deploys resources."""
import argparse
import ipaddress
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


def public_api_url(value: str) -> str:
    value = value.strip().rstrip('/')
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.path or parsed.query or parsed.fragment):
            raise ValueError
        # Accessing .port also validates malformed port strings.
        _ = parsed.port
        host = parsed.hostname.lower()
        if host == 'localhost' or host.endswith(('.localhost', '.local')) or '.' not in host:
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError
        if address is None and (len(host) > 253 or not all(
                re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                for label in host.split('.'))):
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError('Use the public API HTTPS origin, without paths, credentials, or local addresses') from None
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-url', required=True, type=public_api_url,
                        help='Real deployed API origin, for example https://your-service.onrender.com')
    args = parser.parse_args()
    frontend = Path(__file__).resolve().parents[1] / 'frontend'
    environment = os.environ.copy()
    environment['VITE_API_BASE_URL'] = args.api_url
    npm = 'npm.cmd' if os.name == 'nt' else 'npm'
    subprocess.run([npm, 'ci', '--include=dev'], cwd=frontend, env=environment, check=True)
    subprocess.run([npm, 'test'], cwd=frontend, env=environment, check=True)
    subprocess.run([npm, 'run', 'build'], cwd=frontend, env=environment, check=True)
    assets = list((frontend / 'dist' / 'assets').glob('*.js'))
    if not any(args.api_url in asset.read_text(encoding='utf-8') for asset in assets):
        raise SystemExit('API origin was not found in built JavaScript; do not deploy this build')
    print(f'Built frontend/dist using API {args.api_url}. No resources created or deployed.')
    print('This checks build configuration, not API reachability. Verify the API before publishing.')


if __name__ == '__main__':
    main()
