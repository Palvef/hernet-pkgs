# Hernet Packages

Independent patched module packages for official NGINX mainline, **versions newer than 1.31.6 only**, on amd64.

GitHub Actions checks official package indexes daily at 03:17 UTC. Each target builds against its own latest official NGINX package. Successful versions are recorded in `releases.json`; missing or failed releases are retried. Pushes check for missing versions and publish website changes without rebuilding completed versions. Use the manual rebuild input to rebuild existing eligible packages. Increase `BUILD_REVISION` / `RTMP_BUILD_REVISION` before changing an already published payload: published package bytes are immutable.

Supported targets:

| Distribution | Releases | Repository |
|---|---|---|
| Debian | bookworm, trixie | `https://hernet-pkgs.palve.moe/mainline/debian` |
| Ubuntu | jammy, noble, resolute | `https://hernet-pkgs.palve.moe/mainline/ubuntu` |

Each repository contains standard `dists/<codename>/` and `pool/<package>/<codename>/` directories. Versions at or below 1.31.6 and the previous root-level repository directories are removed when publishing. If no eligible official version exists, the signed repository is empty until one is released.

## Install

Configure the [official NGINX mainline repository](https://nginx.org/en/linux_packages.html), then:

```sh
curl -fsS https://hernet-pkgs.palve.moe/hernet-pkgs.gpg | sudo tee /usr/share/keyrings/hernet-pkgs.gpg >/dev/null
. /etc/os-release
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/hernet-pkgs.gpg] https://hernet-pkgs.palve.moe/mainline/$ID $VERSION_CODENAME main" | sudo tee /etc/apt/sources.list.d/hernet-pkgs.list
sudo apt update
sudo apt install nginx-module-lua-ha nginx-module-http-njs-ha nginx-module-http-geoip2-ha
```

Modules are independent packages: `ndk`, `lua`, `fancyindex`, `http-geoip2`, `stream-geoip2`, `vts`, `http-njs`, `stream-njs`, `rtmp`, and `stream`, named `nginx-module-<name>-ha`. The `stream` package depends on the official NGINX binary's built-in stream support. Lua installs matching NDK and `nginx-lua-libraries-ha` dependencies. `njs-cli-ha` provides the CLI. Modules require the exact official NGINX package version used to build them.

Locate module paths using `dpkg -L <package>` and configure `load_module` in the main NGINX context. Load NDK before Lua. Check with `nginx -t` before reloading. Package source manifests contain the selected NGINX version and module directory. No production configuration is overwritten.

The website provides directory indexes, `install.txt`, and `lua-dependencies.txt` containing package download URLs. All module sets must pass installation and live module tests before publication. Original sources are pinned in `sources.json` and `rtmp-sources.json`; NGINX source signatures and official APT signatures are verified during builds. An incompatible patch fails the build and prevents publishing an incomplete set.

## Actions settings

- Secrets: `APT_SIGNING_KEY`, optional `APT_SIGNING_PASSPHRASE`.
- Variables: `APT_SIGNING_FINGERPRINT`, optional `BUILD_REVISION` and `RTMP_BUILD_REVISION`.
- GitHub Pages: GitHub Actions deployment, custom domain `hernet-pkgs.palve.moe`.
- `apt-archive` stores signed repositories and version state. One workflow builds all module families and serializes publication.

Pages exports only the website, DEBs, signed APT metadata, public keys and installation/dependency TXT files. Publication state and build evidence remain in the archive branch; CNAME and internal files are excluded from the public export.
