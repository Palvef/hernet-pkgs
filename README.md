# HerNet packages

Actions builds eight patched dynamic modules against the **signed official** NGINX mainline binary, initially 1.31.6. It never replaces/rebuilds the NGINX core. Targets are Debian bookworm/trixie and Ubuntu jammy/noble/resolute, amd64. Signed repository: https://hernet-pkgs.palve.moe.

Each container verifies the nginx.org repository key fingerprint and source tarball signature, selects the exact available official package, mirrors its configure flags, compiles the modules, patches GeoIP2, builds njs and its unit tests, packages and installs the resulting deliverables, then performs real Lua/njs HTTP and rsync queue TCP checks. Unavailable official versions produce an availability record and no modules. Other errors fail publication.

Packages:

- `nginx-module-extras-ha`: NDK, Lua, fancyindex, HTTP/stream GeoIP2, VTS.
- `nginx-module-njs-ha`: HTTP/stream njs (Palvef rsync queue patches).
- `njs-cli-ha`: patched njs interpreter.
- `nginx-lua-libraries-ha`: Actions-compiled OpenResty cjson and pinned resty-core/lrucache/redis. Dependency downloads and local Lua requirements are listed in [plain text](docs/lua-dependencies.txt), linked on the repository index.

Module packages require `nginx (= EXACT_PACKAGE_VERSION)` and install under `/usr/lib/nginx/ha-modules/EXACT_PACKAGE_VERSION/`. No automatic `load_module` configuration is installed. NDK must load before Lua. Deployments using the rate-limit fallback need `lua_shared_dict rate_limit_fallback 64m;` in the HTTP context.

## Source and patch policy

`sources.json` locks all Git commits; production njs/fancyindex/vts/GeoIP2 revisions are retained. Lua NGINX v0.10.29, NDK v0.3.3 and companion resty libraries are pinned. No uncommitted local source enters the build. Source locks and upstream licenses travel with every package.

GeoIP2 is fixed to `445df24ef3781e488cee3dfe8a1e111997fc1dfe`. After compilation `patch_geoip.py` finds the ELF64 symbol `ngx_http_geoip2_init`, maps its address to a file section, requires one `48 81 c7 78 02 00 00` instruction in that symbol and changes it to `48 81 c7 e8 00 00 00` (LOG to POST_READ). It checks post-patch disassembly and records both SHA256 values and actual instruction address. Ambiguous, missing or already patched binaries fail. Addresses such as 0x131d/0x227d are never hardcoded. No unrelated GeoIP2 source change is bundled with this binary patch. Database reload/cache semantics are documented separately in `docs/geoip2-reload.md`.

## Actions publishing setup

Pages must use **GitHub Actions**. Set repository secrets `APT_SIGNING_KEY` (ASCII-armored private signing key) and optionally `APT_SIGNING_PASSPHRASE`. Set repository variable `APT_SIGNING_FINGERPRINT` to its full fingerprint. Published fingerprint: `FC18C0BCE21885538FFA4010B5687B8D0182B312` ([public key](docs/hernet-pkgs.asc)). Private keys are imported into an ephemeral GNUPGHOME only in the publication job. Set no key file in Git. Configure DNS for `hernet-pkgs.palve.moe` to the GitHub Pages domain; CNAME is included.

Publication exports public `.asc`/`.gpg` keys, creates Packages/Packages.gz and SHA256 Release indexes, signs both InRelease and Release.gpg and verifies signatures before deployment. The `apt-archive` branch preserves historical package payloads; same filename with a different checksum fails rather than replacing a published package. Set/increase repository variable `BUILD_REVISION` (default 1) after an intentional package change/rebuild. The archive commit happens before Pages deployment so retries cannot lose history.

## Local validation

```sh
python3 -m unittest discover -s tests -v
mkdir -p out
docker run --rm --platform linux/amd64 -v "$PWD:/repo:ro" -v "$PWD/out:/out" ubuntu:noble bash /repo/scripts/build.sh
```

CI tests the installed package payload, not only uninstalled build objects. `out` contains availability, NGINX configure flags, source tarball checksum, GeoIP2 disassembly/hashes, njs unit results, real protocol smoke results and package SHA256SUMS. No production service is modified by these tests.

Scheduled builds fix SOURCE_DATE_EPOCH to the locked njs commit and normalize package file mtimes, so rebuilding unchanged inputs can reuse immutable artifacts. If toolchain/dependency changes alter a same-version payload, publication fails until BUILD_REVISION is deliberately increased. The clean pinned njs Git checkout SHA256 `974de8770b284ff1a2befbcd004069dacba725077522c94bc79516f3991225ae` is checked independently of its Git revision. The production Git archive SHA256 `210cb681a7bb438f732deb07b19d3411dfad54188555c175c3daceceeaec594d` is also verified: Git archive honors export-ignore and therefore differs from a full clean checkout.
