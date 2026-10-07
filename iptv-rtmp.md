# NGINX 1.31.6 RTMP / HLS

`nginx-module-rtmp-ha` is the third-party arut RTMP module v1.2.2 built against the exact signed official NGINX package. NGINX itself has no official RTMP module. Official `stream` is already built into nginx.org packages; it supports TCP/UDP forwarding, not RTMP-to-HLS conversion. This package implements the user's explicit `rtmp { application live { ... } }` request.

Install both module packages from the signed HerNet repository:

```sh
apt install nginx-module-rtmp-ha nginx-module-stream-ha
```

`nginx-module-stream-ha` is a dependency package binding the exact official core that already contains `--with-stream`. It ships no replacement `.so`: loading a second stream module into that core would duplicate the existing module. It provides TCP/UDP transport; it is not a standalone RTSP server or RTSP-to-HLS converter.

Configuration is separate: obtain `config/iptv/` from this source repository, or the `iptv-nginx-config.tar.gz` build artifact. Neither DEB contains configuration, and installing them does not alter or reload running NGINX. Back up the existing configuration, web code, certificates and loaded modules before migrating. Replace `@RTMP_MODULE@` in the loader fragment with the path listed by `dpkg -L nginx-module-rtmp-ha`. Create `/tmp/hls`, owned by the configured NGINX worker user, before starting and after each boot (use a systemd tmpfiles rule).

Layout:

```text
nginx.conf
modules-enabled/50-rtmp.conf
conf.d/iptv.conf
rtmp-conf.d/live.conf
snippets/iptv-hls.conf
snippets/iptv-sensitive-endpoints.conf
snippets/iptv-tls.conf.example
stream-conf.d/rtsp.conf.example
```

`live.conf` retains `listen 1935`, `application live`, `live on`, `record off`, `hls on`, `hls_path /tmp/hls` and `hls_fragment 3s`. Publish to `rtmp://SERVER/live/CHANNEL`; HTTP playback is `http://SERVER/hls/CHANNEL.m3u8`. Restrict publishing at the firewall or with RTMP `allow publish` / `deny publish` rules before exposing the listener.

The original `/usr/local/nginx/html/iptv` is the HTTP root. Existing IPTV relay URLs use the separate `livetv` and `hls` applications and `/dev/shm` nested playlists. The supplied `live` example does not replace those applications: retain their original configuration, upstream pulls and HTTP `/hls` mapping when migrating the existing service. The original private server configuration is backed up separately and is not bundled into the public repository.

The optional TLS fragment requires real certificate files. The optional RTSP example must be assigned a real backend and renamed to `.conf` to enable it; it forwards TCP only and requires RTP interleaved over TCP. Default examples are inactive.

Run `nginx -t`, test RTMP publishing and advancing HLS playlists, then gracefully reload. Keep core NGINX and the module at their exact matching versions; `load_module` in the separate template must name the versioned release path. Tests exercise the installed DEBs with synthetic RTMP publishing, HTTP HLS delivery, playlist advancement and actual video/audio decoding.
