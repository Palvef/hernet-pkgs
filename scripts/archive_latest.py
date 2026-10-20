#!/usr/bin/env python3
"""Publish complete independently tested module sets in distro-specific APT trees."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from archive import PACKAGES, RTMP_PACKAGES, copy_immutable
from discover import TARGETS, eligible


def publish(artifacts, site):
    state_file = site / 'releases.json'
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    staged = []
    evidence = []
    for distro, suites in TARGETS.items():
        for suite in suites:
            source = artifacts / ('packages-' + suite)
            if not source.exists():
                continue
            expected = json.loads((source / 'target.json').read_text())
            package = expected['package']
            if not eligible(package):
                raise ValueError('Unsupported NGINX version: ' + package)
            packages = list(source.glob('*.deb'))
            names = set()
            for p in packages:
                name, version, architecture = subprocess.check_output(['dpkg-deb', '-f', str(p), 'Package', 'Version', 'Architecture'], text=True).splitlines()
                name, version, architecture = [x.split(': ', 1)[-1] for x in (name, version, architecture)]
                if '+nginx' + package not in version or architecture != 'amd64':
                    raise ValueError('Package target mismatch: ' + p.name)
                names.add(name)
                staged.append((p, site / 'mainline' / distro / 'pool' / name / suite / p.name))
            if names != PACKAGES | RTMP_PACKAGES or len(packages) != len(names):
                raise ValueError('Incomplete module set: ' + suite)
            state[suite] = {'package': package, 'distro': distro}
            evidence.append((source, site / 'build-evidence' / distro / suite / package))
    for source, dest in staged:
        copy_immutable(source, dest)
    for source, dest in evidence:
        dest.mkdir(parents=True, exist_ok=True)
        for p in source.iterdir():
            if p.is_file() and p.suffix != '.deb':
                shutil.copy2(p, dest / p.name)
    for old in (site / 'mainline').glob('*/dists/*/evidence'):
        dest = site / 'build-evidence' / old.parts[-4] / old.parts[-2]
        shutil.copytree(old, dest, dirs_exist_ok=True)
        shutil.rmtree(old)
    # Only explicitly obsolete releases/layouts are removed. Retain all >1.31.6 releases.
    for p in (site / 'mainline').rglob('*.deb'):
        match = re.search(r'\+nginx(\d+\.\d+\.\d+)', p.name)
        if not match or not eligible(match.group(1)):
            p.unlink()
    for name in ['pool', 'dists', 'modules', 'dependencies', 'tools', 'evidence']:
        if (site / name).exists():
            shutil.rmtree(site / name)
    for suite in list(state):
        if not eligible(state[suite]['package']):
            del state[suite]
    state_file.write_text(json.dumps(state, indent=2) + '\n')

if __name__ == '__main__':
    publish(Path(sys.argv[1]), Path(sys.argv[2]))
