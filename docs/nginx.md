# NGINX

Configure NGINX to emit planned IPv4-unavailability signaling per
[draft-martin-retry-over-ipv6](../draft-martin-retry-over-ipv6.md).

Shared requirements, response body, verification, and checklist:
[README.md](README.md).

## 1. Map: policy flag and IPv4 detection

Add to `http { }` (for example in `/etc/nginx/conf.d/retry-over-ipv6.conf`):

```nginx
# Manual override: set a host to 1 for an ad-hoc drill, else leave 0.
map $host $ipv4_outage_manual {
    default                 0;
    # example.com             1;
}

# Recurring: enable on the 6th of every month (local time of $time_iso8601).
# Prefer TZ=UTC for the nginx process so all nodes agree on "the 6th".
# Format of $time_iso8601: 2026-06-06T12:00:00+00:00
map $time_iso8601 $ipv4_outage_day6 {
    default                 0;
    "~^\d{4}-\d{2}-06T"     1;
}

# Enabled if manual override OR day-6 schedule.
map "$ipv4_outage_manual:$ipv4_outage_day6" $ipv4_outage_enabled {
    default     0;
    "~^1:"      1;
    "~^.:1$"    1;
}

# 1 = client-facing IPv4 that should receive 503 + headers (skip loopback).
map $remote_addr $ipv4_outage_client {
    default                 0;
    "~^127\."               0;
    "~^\d+\.\d+\.\d+\.\d+$" 1;
}

# Combine policy + address family.
map "$ipv4_outage_enabled:$ipv4_outage_client" $send_ipv4_unavailable {
    default     0;
    "1:1"       1;
}

# Prefer signaling on safe/idempotent methods during drills.
map $request_method $ipv4_outage_method_ok {
    default     0;
    GET         1;
    HEAD        1;
    OPTIONS     1;
    PUT         1;
    DELETE      1;
    # Omit POST/PATCH unless the application deduplicates retries.
}

log_format ipv6_recovery '$remote_addr [$time_local] "$request" '
                         'status=$status '
                         'recovery="$http_retry_over_ipv6_recovery" '
                         'af=$server_addr';
```

## 2. Server block: emit `503` + headers on IPv4, serve on IPv6

```nginx
server {
    listen 80;
    listen [::]:80;
    listen 443 ssl;
    listen [::]:443 ssl;
    # http2 on;  # if enabled, emit the same signal on every IPv4 connection

    server_name example.com;

    # Optional: short-lived opaque token (nginx $request_id when available).
    # Quote per draft: Retry-Over-IPv6-Token is a quoted-string.
    set $retry_token '"$request_id"';

    # For a full-day drill on the 6th, Until is start of the 7th (update or
    # compute via cron/njs; static example below is illustrative only).
    set $ipv4_until "Sun, 07 Jun 2026 00:00:00 GMT";

    # Seconds until outage end for legacy Retry-After (optional).
    # For a day-long drill, ~seconds remaining in the UTC day is better than a fixed value.
    set $retry_after_secs "3600";

    access_log /var/log/nginx/access.log ipv6_recovery;

    # --- Planned IPv4 unavailability ---------------------------------
    location / {
        if ($send_ipv4_unavailable = 0) {
            break;
        }
        if ($ipv4_outage_method_ok = 0) {
            break;
        }

        # Named location keeps headers + body together.
        error_page 503 = @ipv4_unavailable;
        return 503;
    }

    location @ipv4_unavailable {
        internal;
        default_type application/problem+json;
        add_header Retry-Over-IPv6 "?1" always;
        add_header IPv4-Unavailable-Until $ipv4_until always;
        add_header Retry-Over-IPv6-Token $retry_token always;
        add_header Cache-Control "private, no-store" always;
        add_header Retry-After $retry_after_secs always;
        # Body: inline JSON, or alias a file via root + try_files.
        return 503 '{"type":"urn:ietf:params:problem:ipv4-unavailable","title":"IPv4 Unavailable","status":503,"detail":"IPv4 unavailable until 2026-06-07T00:00:00Z; retry over IPv6.","ipv4UnavailableUntil":"2026-06-07T00:00:00Z"}';
    }

    # --- Normal application (IPv6 and when outage disabled) ----------
    location /app/ {
        # proxy_pass http://upstream;
        # or root /var/www/html;
    }
}
```

> **Note on `if`:** NGINX `if` is tricky. Prefer keeping the outage logic in a
> dedicated `server` that only listens on IPv4 (below) when you can split
> listeners.

## 3. Cleaner pattern: separate IPv4 listener

When dual-stack sockets can be split, generate the signal only on the IPv4
`server` and leave the IPv6 `server` untouched:

```nginx
# IPv6: normal service (no IPv4-unavailability signal).
server {
    listen [::]:443 ssl;
    server_name example.com;
    # ... normal config ...
    access_log /var/log/nginx/access.log ipv6_recovery;
}

# IPv4: planned unavailability only.
server {
    listen 443 ssl;
    server_name example.com;

    set $retry_token '"$request_id"';
    set $ipv4_until "Sun, 07 Jun 2026 00:00:00 GMT";

    # Skip loopback health checks on this listener if used locally.
    if ($remote_addr ~ "^127\.") {
        return 200 "ok\n";
    }

    location / {
        if ($request_method !~ ^(GET|HEAD|OPTIONS|PUT|DELETE)$) {
            return 405;
            # Or proxy to origin without the signal if POST must still work on IPv4.
        }
        default_type application/problem+json;
        add_header Retry-Over-IPv6 "?1" always;
        add_header IPv4-Unavailable-Until $ipv4_until always;
        add_header Retry-Over-IPv6-Token $retry_token always;
        add_header Cache-Control "private, no-store" always;
        return 503 '{"type":"urn:ietf:params:problem:ipv4-unavailable","title":"IPv4 Unavailable","status":503,"detail":"IPv4 unavailable until 2026-06-07T00:00:00Z; retry over IPv6.","ipv4UnavailableUntil":"2026-06-07T00:00:00Z"}';
    }
}
```

Enable or disable the IPv4 outage by commenting out the IPv4 `server` block,
removing the IPv4 `listen`, toggling `$ipv4_outage_manual`, or relying on the
day-6 `$ipv4_outage_day6` map (no reload needed when the calendar rolls).

## 4. Calendar schedule and timed windows

### Full day on the 6th (built-in)

The `$ipv4_outage_day6` map above turns signaling on automatically whenever
`$time_iso8601` falls on day `06`. No cron is required. Ensure the nginx
worker timezone is the one you intend (systemd `Environment=TZ=UTC` is a
common choice for multi-node fleets).

For `IPv4-Unavailable-Until` on a recurring day-6 drill, either:

- set it to **00:00:00 GMT on the 7th** each month (cron/njs can rewrite a
  small `include` file), or
- omit the header and state permanence / schedule in the response body.

### Shorter window via cron (optional)

For a one-hour window instead of the whole day, flip a flag file and reload:

```bash
# /etc/cron.d/ipv4-outage-day6  (UTC)
0 9 6 * * root printf 'map $host $ipv4_outage_manual { default 1; }\n' > /etc/nginx/conf.d/ipv4-outage-flag.map && nginx -s reload
0 10 6 * * root printf 'map $host $ipv4_outage_manual { default 0; }\n' > /etc/nginx/conf.d/ipv4-outage-flag.map && nginx -s reload
```

Include that map from `http { }` and keep `$ipv4_outage_day6` at `0` if cron
owns the schedule.

## 5. Enable / reload

```bash
# For a manual drill: set $ipv4_outage_manual (or host map) to 1, then:
sudo nginx -t && sudo systemctl reload nginx
# Day-6 schedule needs no reload when the date changes.
```

| Action | Knob |
|--------|------|
| Start drill | Set `$ipv4_outage_manual` to `1`, enable the IPv4-only `server`, or wait for day 6 |
| End drill | Set manual flag to `0` / remove IPv4 outage `server` (day-6 ends at midnight automatically) |
| Rollback | `nginx -t && systemctl reload nginx` |
