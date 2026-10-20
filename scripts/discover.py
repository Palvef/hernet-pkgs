#!/usr/bin/env python3
"""Select official mainline package versions newer than the supported baseline."""
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

TARGETS = {'debian': ['bookworm', 'trixie'], 'ubuntu': ['jammy', 'noble', 'resolute']}
BASELINE = (1, 31, 6)

def eligible(version):
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-|$)', version)
    return bool(match and tuple(map(int, match.groups())) > BASELINE)

def newest(text):
    versions = []
    for paragraph in text.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in paragraph.splitlines() if ': ' in line and not line.startswith(' '))
        if fields.get('Package') == 'nginx' and eligible(fields.get('Version', '')):
            versions.append(fields['Version'])
    winner = None
    for version in versions:
        if winner is None or subprocess.run(['dpkg', '--compare-versions', version, 'gt', winner]).returncode == 0:
            winner = version
    return winner

def main():
    state_path = Path('site/releases.json')
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    matrix = []
    for distro, suites in TARGETS.items():
        for suite in suites:
            url = f'https://nginx.org/packages/mainline/{distro}/dists/{suite}/nginx/binary-amd64/Packages.gz'
            with urllib.request.urlopen(url, timeout=60) as response:
                package = newest(gzip.decompress(response.read()).decode())
            if not package:
                continue
            if os.environ.get('FORCE_BUILD') != 'true' and state.get(suite, {}).get('package') == package:
                continue
            version = re.match(r'\d+\.\d+\.\d+', package).group()
            matrix.append(dict(image=f'{distro}:{suite}', suite=suite, distro=distro, version=version, package=package))
    output = {'include': matrix}
    print(json.dumps(output))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
        out.write('matrix=' + json.dumps(output) + '\n')
        out.write('build=' + str(bool(matrix)).lower() + '\n')

if __name__ == '__main__':
    main()
