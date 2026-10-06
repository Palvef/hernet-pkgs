# GeoIP2 database reload and cache

Upstream commit 445df24 caches both the last IP address and MMDB_lookup_result_s. Successful auto_reload closes the old mapped database and replaces the MMDB handle, but does not invalidate this cached result. A consecutive request from the same IP can reuse an entry from the closed mapping. Moving the handler from LOG to POST_READ makes correct invalidation essential before request variable evaluation.

`patch_geoip_cache.py` is a separate, auditable source correction, applied to HTTP and stream: add cache_valid, force lookup when invalid, mark valid only after MMDB_SUCCESS, and reset both validity and cached result after a successful reload. Failed reloads retain the live database/cache. This also forces a lookup for an initial all-zero address. The resulting source diff is published as evidence/VER/geoip2-cache.patch; it does not modify phase registration.

The mandatory phase change remains a post-compilation symbol-bounded binary patch with before/after hashes and disassembly. Full same-IP database replacement testing requires real MMDB fixtures; the container verifies module compilation/loading and real Lua/njs/rsync requests, while the source transform fails closed if pinned code changes.
