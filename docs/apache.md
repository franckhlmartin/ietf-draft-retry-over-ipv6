# Apache HTTP Server

Configure Apache 2.4+ to emit planned IPv4-unavailability signaling per
[draft-martin-retry-over-ipv6](../draft-martin-retry-over-ipv6.md).

Shared requirements, response body, verification, and checklist:
[README.md](README.md).

Requires `mod_rewrite`, `mod_headers`, and (for tokens) `mod_unique_id`.
`mod_setenvif` is used for address-family detection and the day-6
`SetEnvIfExpr` gate. Optional: `mod_lua`.

## 1. Modules

```apache
LoadModule rewrite_module modules/mod_rewrite.so
LoadModule headers_module modules/mod_headers.so
LoadModule setenvif_module modules/mod_setenvif.so
LoadModule unique_id_module modules/mod_unique_id.so
# Optional: LoadModule lua_module modules/mod_lua.so
```

## 2. Shared env and logging

```apache
# Manual override for an ad-hoc drill (set to 1), else leave 0.
# SetEnvIf (not SetEnv) so the value is visible to SetEnvIfExpr / <If>.
SetEnvIf Request_URI "^" IPV4_OUTAGE_MANUAL=0
SetEnvIf Request_URI "^" IPV4_OUTAGE=0

# %{TIME_DAY} is zero-padded (01–31). Prefer TZ=UTC on httpd so nodes agree.
# Requires mod_setenvif (SetEnvIfExpr).
SetEnvIfExpr "%{TIME_DAY} == '06' || %{env:IPV4_OUTAGE_MANUAL} -eq 1" IPV4_OUTAGE=1

# Client-facing IPv4 (dotted-quad), excluding loopback.
SetEnvIf Remote_Addr "^\d+\.\d+\.\d+\.\d+$" IPV4_CLIENT=1
SetEnvIf Remote_Addr "^127\." IPV4_CLIENT=0

# Log recovery on IPv6 retries (do not alter responses based on this header).
LogFormat "%h %l %u %t \"%r\" %>s \"%{Retry-Over-IPv6-Recovery}i\" %{UNIQUE_ID}e" ipv6_recovery
CustomLog logs/ipv6_recovery_log ipv6_recovery
```

Day-of-month gating uses `%{TIME_DAY}` (**`01`–`31`**, with a leading zero).
A common mistake is `RewriteCond %{TIME_DAY} =6`, which never matches day 6
because the value is `06`. Prefer the `IPV4_OUTAGE` flag above, or compare
against `'06'`.

## 3. Emit `503` + headers

A reliable pattern is: rewrite matching IPv4 requests to a dedicated path,
then use a small CGI/PHP handler (or Lua) that returns `503` with the draft
headers. `ErrorDocument 503` can also serve a static body, but a handler is
needed to set `Retry-Over-IPv6` and related fields consistently.

### Option A — CGI handler (portable)

**`/var/www/cgi-bin/ipv4-unavailable.cgi`:**

```sh
#!/bin/sh
# Until = start of tomorrow UTC (fits a full-day drill on the 6th).
if date -u -d 'tomorrow 00:00' '+%a, %d %b %Y %H:%M:%S GMT' >/dev/null 2>&1; then
  UNTIL_HTTP=$(date -u -d 'tomorrow 00:00' '+%a, %d %b %Y %H:%M:%S GMT')
  UNTIL_ISO=$(date -u -d 'tomorrow 00:00' '+%Y-%m-%dT00:00:00Z')
else
  # BSD/macOS date(1)
  UNTIL_HTTP=$(date -u -v+1d '+%a, %d %b %Y 00:00:00 GMT')
  UNTIL_ISO=$(date -u -v+1d '+%Y-%m-%dT00:00:00Z')
fi
TOKEN="${UNIQUE_ID:-$(openssl rand -hex 8)}"
# Rough seconds remaining in the UTC day for legacy clients.
RETRY_AFTER=$(($(date -u -d 'tomorrow 00:00' +%s 2>/dev/null || date -u -v+1d +%s) - $(date -u +%s)))

printf 'Status: 503 Service Unavailable\r\n'
printf 'Retry-Over-IPv6: ?1\r\n'
printf 'IPv4-Unavailable-Until: %s\r\n' "$UNTIL_HTTP"
printf 'Retry-Over-IPv6-Token: "%s"\r\n' "$TOKEN"
printf 'Cache-Control: private, no-store\r\n'
printf 'Retry-After: %s\r\n' "$RETRY_AFTER"
printf 'Content-Type: application/problem+json\r\n'
printf '\r\n'
cat <<EOF
{"type":"urn:ietf:params:problem:ipv4-unavailable","title":"IPv4 Unavailable","status":503,"detail":"IPv4 unavailable until ${UNTIL_ISO}; retry over IPv6.","ipv4UnavailableUntil":"${UNTIL_ISO}"}
EOF
```

```bash
chmod +x /var/www/cgi-bin/ipv4-unavailable.cgi
```

**VirtualHost:**

```apache
<VirtualHost *:443>
    ServerName example.com
    # Listen on IPv4 and IPv6; signaling is gated by IPV4_CLIENT below.
    # SSLEngine on
    # ...

    SetEnvIf Request_URI "^" IPV4_OUTAGE_MANUAL=0
    SetEnvIf Request_URI "^" IPV4_OUTAGE=0
    SetEnvIfExpr "%{TIME_DAY} == '06' || %{env:IPV4_OUTAGE_MANUAL} -eq 1" IPV4_OUTAGE=1

    SetEnvIf Remote_Addr "^\d+\.\d+\.\d+\.\d+$" IPV4_CLIENT=1
    SetEnvIf Remote_Addr "^127\." IPV4_CLIENT=0

    ScriptAlias /cgi-bin/ /var/www/cgi-bin/
    <Directory /var/www/cgi-bin>
        AllowOverride None
        Options +ExecCGI
        Require all granted
    </Directory>

    # Outage if IPV4_OUTAGE is set (manual override OR calendar day is the 6th).
    <If "%{env:IPV4_OUTAGE} -eq 1">
        RewriteEngine On
        RewriteCond %{ENV:IPV4_CLIENT} =1
        RewriteCond %{REQUEST_METHOD} ^(GET|HEAD|OPTIONS|PUT|DELETE)$
        RewriteRule ^ /cgi-bin/ipv4-unavailable.cgi [L]
    </If>

    # Normal document root / proxy for IPv6 and when outage is off.
    DocumentRoot /var/www/html
    # ProxyPass /app http://127.0.0.1:8080/app
</VirtualHost>
```

Pass `UNIQUE_ID` into CGI if needed:

```apache
SetEnvIf Request_URI ".*" UNIQUE_ID=%{UNIQUE_ID}e
# Or in the CGI, rely on Apache exporting UNIQUE_ID when mod_unique_id is loaded.
```

### Option B — `ErrorDocument 503`

When you prefer not to run CGI/Lua, return `503` with a static body via
**ErrorDocument**:

```apache
ErrorDocument 503 /ipv4-unavailable.json

# Assume IPV4_OUTAGE / IPV4_CLIENT are set as in section 2.
<If "%{env:IPV4_OUTAGE} -eq 1">
    RewriteEngine On
    RewriteCond %{ENV:IPV4_CLIENT} =1
    RewriteCond %{REQUEST_METHOD} ^(GET|HEAD|OPTIONS|PUT|DELETE)$
    RewriteRule ^ - [R=503,L]
</If>

# Headers on the error response:
Header always set Retry-Over-IPv6 "?1" "expr=%{REQUEST_STATUS} == 503"
Header always set IPv4-Unavailable-Until "Sun, 07 Jun 2026 00:00:00 GMT" \
    "expr=%{REQUEST_STATUS} == 503"
Header always set Cache-Control "private, no-store" \
    "expr=%{REQUEST_STATUS} == 503"
```

Ensure `ipv4-unavailable.json` uses `"status": 503` and the registered problem
type URI. See [README.md](README.md) for the shared JSON body.

### Option C — `mod_lua` returning `503`

```apache
LuaMapHandler ^/ /var/www/lua/ipv4_unavailable.lua
```

**`/var/www/lua/ipv4_unavailable.lua`** (sketch; gate on env in Lua or only
map when outage is enabled):

```lua
function handle(r)
    -- Prefer the shared IPV4_OUTAGE flag (handles zero-padded TIME_DAY).
    if r.subprocess_env["IPV4_OUTAGE"] ~= "1" then
        return apache2.DECLINED
    end
    if r.subprocess_env["IPV4_CLIENT"] ~= "1" then
        return apache2.DECLINED
    end
    local m = r.method
    if m ~= "GET" and m ~= "HEAD" and m ~= "OPTIONS"
       and m ~= "PUT" and m ~= "DELETE" then
        return apache2.DECLINED
    end

    -- Until = next UTC midnight (start of the 7th after a day-6 drill).
    local until_http = os.date("!%a, %d %b %Y 00:00:00 GMT",
        os.time({year=os.date("!%Y"), month=os.date("!%m"),
                 day=os.date("!%d")+1, hour=0, min=0, sec=0}))
    local until_iso = os.date("!%Y-%m-%dT00:00:00Z",
        os.time({year=os.date("!%Y"), month=os.date("!%m"),
                 day=os.date("!%d")+1, hour=0, min=0, sec=0}))

    local token = r.subprocess_env["UNIQUE_ID"] or "unknown"
    r.status = 503
    r.status_line = "503 Service Unavailable"
    r.content_type = "application/problem+json"
    r.headers_out["Retry-Over-IPv6"] = "?1"
    r.headers_out["IPv4-Unavailable-Until"] = until_http
    r.headers_out["Retry-Over-IPv6-Token"] = '"' .. token .. '"'
    r.headers_out["Cache-Control"] = "private, no-store"
    r:puts('{"type":"urn:ietf:params:problem:ipv4-unavailable","title":"IPv4 Unavailable","status":503,'
        .. '"detail":"IPv4 unavailable until ' .. until_iso .. '.",'
        .. '"retryOverIPv6":true,'
        .. '"ipv4UnavailableUntil":"' .. until_iso .. '"}')
    return apache2.DONE
end
```

## 4. Calendar schedule and timed windows

### Full day on the 6th (built-in)

`SetEnvIfExpr` with `%{TIME_DAY} == '06'` sets `IPV4_OUTAGE=1` for the whole
calendar day. No cron is required. Set `TZ=UTC` on the httpd service if you
want UTC days.

**Pitfall:** `%{TIME_DAY}` is zero-padded (`01`–`31`). Use `'06'`, not `6`.
`RewriteCond %{TIME_DAY} =6` does not match day 6 (observed in production on
ipv6forum.com).

If you gate with `RewriteCond` instead of `SetEnvIfExpr`, compare the padded
value:

```apache
RewriteCond %{TIME_DAY} ='06'
```

### Shorter window via cron (optional)

```bash
# /etc/cron.d/ipv4-outage-day6  (UTC) — toggle manual override for one hour
0 9 6 * * root sed -i 's/IPV4_OUTAGE_MANUAL=0/IPV4_OUTAGE_MANUAL=1/' /etc/httpd/conf.d/ipv4-outage.conf && systemctl reload httpd
0 10 6 * * root sed -i 's/IPV4_OUTAGE_MANUAL=1/IPV4_OUTAGE_MANUAL=0/' /etc/httpd/conf.d/ipv4-outage.conf && systemctl reload httpd
```

Drop the `%{TIME_DAY} == '06'` half of `SetEnvIfExpr` if cron alone owns the
schedule.

## 5. Enable / reload

```bash
# For a manual drill: set IPV4_OUTAGE_MANUAL=1, then:
sudo apachectl configtest && sudo systemctl reload apache2
# or: sudo systemctl reload httpd
# Day-6 schedule needs no reload when the date changes.
```

| Action | Knob |
|--------|------|
| Start drill | `IPV4_OUTAGE_MANUAL=1`, or wait for `%{TIME_DAY} == '06'` |
| End drill | `IPV4_OUTAGE_MANUAL=0` (day-6 ends at midnight automatically) |
| Rollback | `apachectl configtest && systemctl reload apache2` |
