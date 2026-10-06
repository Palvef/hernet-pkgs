# HerNet packages

Actions builds eight patched dynamic modules against the **signed official** NGINX mainline binary, initially 1.31.6. It never replaces/rebuilds the NGINX core. Targets are Debian bookworm/trixie and Ubuntu jammy/noble/resolute, amd64. Signed repository: https://hernet-pkgs.palve.moe.

Each container verifies the nginx.org repository key fingerprint and source tarball signature, selects the exact available official package, mirrors its configure flags, compiles the modules, patches GeoIP2, builds njs and its unit tests, packages and installs the resulting deliverables, then performs real Lua/njs HTTP, rsync queue TCP and two-worker GeoIP2/RealIP/rewrite/database replacement checks. Unavailable official versions produce an availability record and no modules. Other errors fail publication.

Each module has its own DEB and download directory:

| Package | Payload | Downloads |
| --- | --- | --- |
| `nginx-module-ndk-ha` | NDK HTTP | [ndk](https://hernet-pkgs.palve.moe/modules/ndk/) |
| `nginx-module-lua-ha` | Lua HTTP | [lua](https://hernet-pkgs.palve.moe/modules/lua/) |
| `nginx-module-fancyindex-ha` | fancyindex HTTP | [fancyindex](https://hernet-pkgs.palve.moe/modules/fancyindex/) |
| `nginx-module-http-geoip2-ha` | GeoIP2 HTTP | [http-geoip2](https://hernet-pkgs.palve.moe/modules/http-geoip2/) |
| `nginx-module-stream-geoip2-ha` | GeoIP2 stream | [stream-geoip2](https://hernet-pkgs.palve.moe/modules/stream-geoip2/) |
| `nginx-module-vts-ha` | VTS HTTP | [vts](https://hernet-pkgs.palve.moe/modules/vts/) |
| `nginx-module-http-njs-ha` | njs HTTP | [http-njs](https://hernet-pkgs.palve.moe/modules/http-njs/) |
| `nginx-module-stream-njs-ha` | njs stream | [stream-njs](https://hernet-pkgs.palve.moe/modules/stream-njs/) |

Directories contain distribution subdirectories and direct DEB links. `njs-cli-ha` is under `tools/njs/<suite>/`. `nginx-lua-libraries-ha` contains Actions-compiled OpenResty cjson and pinned resty-core/lrucache/redis under `dependencies/lua-libraries/<suite>/`. Lua requires the exact same release of both `nginx-module-ndk-ha` and `nginx-lua-libraries-ha`; APT installs those dependencies when only Lua is selected. Dependency download URLs and local Lua requirements are listed in [plain text](docs/lua-dependencies.txt), linked on the repository index.

Every module requires `nginx (= EXACT_PACKAGE_VERSION)`. Packages install under `/usr/lib/nginx/ha-modules/EXACT_PACKAGE_VERSION/hernet-1.0.3-rBUILD_REVISION/`; default revision is 1. Explicit `load_module` paths must point to the selected release directory, and NDK must load before Lua. Deployments using the rate-limit fallback need `lua_shared_dict rate_limit_fallback 64m;` in the HTTP context.

### Install selected modules or all eight

After configuring the signed repository, select only the packages needed. For all eight:

```sh
sudo apt install nginx-module-ndk-ha nginx-module-lua-ha \
  nginx-module-fancyindex-ha nginx-module-http-geoip2-ha \
  nginx-module-stream-geoip2-ha nginx-module-vts-ha \
  nginx-module-http-njs-ha nginx-module-stream-njs-ha
```

Old aggregate DEBs remain in historical `pool/<suite>/` downloads, but new builds do not create them. New packages have distinct release paths and no Breaks/Conflicts/Replaces relationship with old aggregate packages. Existing held aggregate packages and their currently loaded files remain available while selected split packages are installed. Validate the complete new `load_module` set before a graceful reload. Keep the old packages and previous config for rollback; uninstalling a split package does not delete the old release. Optional legacy cleanup can happen after the new config has been verified. Independent GeoIP2 and njs HTTP/stream packages do not force installation of their other family member.

The published `nginx-module-extras-ha` 1.0.2 additionally requires its older `nginx-lua-libraries-ha` at an exact version. Holding that aggregate prevents installation of the newer Lua library package; the earlier 1.0.1 production aggregate has no such library constraint. Before migrating 1.0.2, snapshot the active configuration, Lua libraries and module files. Prepare the complete independent module paths, with NDK before Lua, and remove/unhold the older aggregate when its dependency blocks the selected new packages. Preserve the official NGINX core version and its hold. Run `nginx -t` against the new configuration before a graceful reload, and retain the snapshot for rollback. A successful migration does not require restarting the core service.


## Source and patch policy

`sources.json` locks all Git commits; production njs/fancyindex/vts/GeoIP2 revisions are retained. Lua NGINX v0.10.29, NDK v0.3.3 and companion resty libraries are pinned. No uncommitted local source enters the build. Source locks and upstream licenses travel with every package.

GeoIP2 is fixed to `445df24ef3781e488cee3dfe8a1e111997fc1dfe`. After compilation `patch_geoip.py` finds the ELF64 symbol `ngx_http_geoip2_init`, maps its address to a file section, requires one `48 81 c7 78 02 00 00` instruction in that symbol and changes it to `48 81 c7 e8 00 00 00` (LOG to POST_READ). It checks post-patch disassembly and records both SHA256 values and actual instruction address. Ambiguous, missing or already patched binaries fail. Addresses such as 0x131d/0x227d are never hardcoded. Separate source corrections invalidate reloaded database caches and make the relocated HTTP handler return NGX_DECLINED, preserving subsequent POST_READ handlers including RealIP. Database reload/cache semantics are documented separately in `docs/geoip2-reload.md`.

## Actions publishing setup

Pages must use **GitHub Actions**. Set repository secrets `APT_SIGNING_KEY` (ASCII-armored private signing key) and optionally `APT_SIGNING_PASSPHRASE`. Set repository variable `APT_SIGNING_FINGERPRINT` to its full fingerprint. Published fingerprint: `FC18C0BCE21885538FFA4010B5687B8D0182B312` ([public key](docs/hernet-pkgs.asc)). Private keys are imported into an ephemeral GNUPGHOME only in the publication job. Set no key file in Git. Configure DNS for `hernet-pkgs.palve.moe` to the GitHub Pages domain; CNAME is included.

Publication exports public `.asc`/`.gpg` keys, creates Packages/Packages.gz and SHA256 Release indexes, signs both InRelease and Release.gpg and verifies signatures before deployment. The `apt-archive` branch preserves historical package payloads; same filename with a different checksum fails rather than replacing a published package. Set/increase repository variable `BUILD_REVISION` (default 1) after an intentional package change/rebuild. The archive commit happens before Pages deployment so retries cannot lose history.

## Local validation

```sh
python3 -m unittest discover -s tests -v
mkdir -p out
docker run --rm --platform linux/amd64 -v "$PWD:/repo:ro" -v "$PWD/out:/out" ubuntu:noble bash /repo/scripts/build.sh
```

CI tests the installed package payload, not only uninstalled build objects. `out` contains availability, NGINX configure flags, source tarball checksum, GeoIP2 disassembly/hashes, njs unit results, real protocol smoke results and package SHA256SUMS. The GeoIP2 fixture test covers IPv4/IPv6 RealIP, server rewrite rejection, empty/filled MMDB replacements for the same IP in HTTP and stream, trusted exemptions, and retaining the last valid database after an invalid replacement. No production service is modified by these tests.

Scheduled builds fix SOURCE_DATE_EPOCH to the locked njs commit and normalize package file mtimes, so rebuilding unchanged inputs can reuse immutable artifacts. If toolchain/dependency changes alter a same-version payload, publication fails until BUILD_REVISION is deliberately increased. The clean pinned njs Git checkout SHA256 `974de8770b284ff1a2befbcd004069dacba725077522c94bc79516f3991225ae` is checked independently of its Git revision. The production Git archive SHA256 `210cb681a7bb438f732deb07b19d3411dfad54188555c175c3daceceeaec594d` is also verified: Git archive honors export-ignore and therefore differs from a full clean checkout.
