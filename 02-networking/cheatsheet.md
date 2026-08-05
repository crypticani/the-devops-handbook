# Module 02: Networking — Cheat Sheet

> Command reference for network diagnosis and configuration. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Triage ladder](#the-triage-ladder) · [Interfaces & routes](#interfaces--routing) · [Sockets](#sockets--listening-ports) · [DNS](#dns) · [curl](#curl) · [Connectivity](#connectivity-testing) · [Packet capture](#packet-capture) · [Firewalls](#firewalls) · [Nginx](#nginx) · [TLS](#tls--certificates) · [Reference tables](#reference-tables)

---

## The Triage Ladder

Run these in order. Each rung eliminates a layer.

```bash
dig +short api.example.com                    # 1. DNS — does the name resolve?
ping -c 3 93.184.216.34                       # 2. L3  — is the host reachable? (ICMP may be blocked)
nc -zv 93.184.216.34 443                      # 3. L4  — is the port open?
openssl s_client -connect host:443 -servername host </dev/null   # 4. TLS
curl -v https://api.example.com/health        # 5. L7  — what does the app say?
mtr -rwc 20 93.184.216.34                     # 6. Path — where are packets being lost?
```

| Result at step 3 | Meaning | Look at |
|------------------|---------|---------|
| **Connection refused** | Packet arrived; nothing is listening | Service down, or bound to `127.0.0.1` |
| **Connection timed out** | Nobody answered at all | Firewall, security group, NACL, routing |
| **No route to host** | Local routing has no path | `ip route`, gateway, subnet config |
| **Connected** | Layers 3 and 4 are fine | Move up to TLS/HTTP |

---

## Interfaces & Routing

```bash
ip a                          # all interfaces + addresses
ip -br a                      # brief one-line-per-interface view
ip -4 a show eth0             # IPv4 only, one interface
ip link                       # link state (UP/DOWN, MTU, MAC)
ip r                          # routing table
ip route get 8.8.8.8          # which route/interface/source IP would be used  ⭐
ip neigh                      # ARP/neighbour cache
ip -s link show eth0          # per-interface error and drop counters

# Temporary changes (lost on reboot)
sudo ip a add 10.0.1.50/24 dev eth0
sudo ip link set eth0 up
sudo ip r add 10.0.2.0/24 via 10.0.1.1
sudo ip r add default via 10.0.1.1

# Persistent config
# Ubuntu:  /etc/netplan/*.yaml   → sudo netplan try && sudo netplan apply
# RHEL:    nmcli con show; sudo nmcli con mod eth0 ipv4.addresses 10.0.1.50/24
#          sudo nmcli con up eth0

hostname -I                   # all IPs of this host
hostnamectl                   # hostname + OS + kernel
cat /etc/hosts                # static overrides (checked BEFORE DNS)
cat /etc/resolv.conf          # active resolvers
resolvectl status             # systemd-resolved: per-link DNS config
```

**MTU issues** — connection opens but large transfers hang:

```bash
ip link show eth0 | grep mtu
ping -M do -s 1472 8.8.8.8    # 1472 + 28 bytes header = 1500; fails if MTU is lower
sudo ip link set eth0 mtu 1450   # common for VPN/overlay networks
```

---

## Sockets & Listening Ports

`ss` replaces the deprecated `netstat`.

```bash
ss -tlnp                      # ⭐ TCP, Listening, Numeric, Process
ss -ulnp                      # same for UDP
ss -tunap                     # TCP+UDP, all states, numeric, with process
ss -tn state established      # established connections only
ss -tn state time-wait | wc -l
ss -tp dst 10.0.1.50          # connections to a specific host
ss -tlnp 'sport = :443'       # filter by port
ss -s                         # summary counts by protocol/state
ss -tin                       # TCP internals: rtt, cwnd, retransmits

lsof -i :8080                 # what's using port 8080
lsof -i -P -n                 # all network files, numeric
sudo fuser -k 8080/tcp        # kill whatever holds port 8080  ⚠️
```

| Socket state | Meaning |
|--------------|---------|
| `LISTEN` | Waiting for connections |
| `ESTAB` | Active connection |
| `SYN-SENT` | We sent SYN, no reply — firewall or dead host |
| `TIME-WAIT` | Local side closed; waits ~60s. Thousands = connection churn |
| `CLOSE-WAIT` | **Remote closed, our app hasn't** — usually an application bug/leak |
| `FIN-WAIT-2` | We closed, waiting on the peer |

> 💡 `0.0.0.0:80` = listening on all interfaces. `127.0.0.1:80` = **localhost only** — unreachable from other machines or from outside a container. This one line explains a huge share of "the service is running but I can't connect."

---

## DNS

```bash
dig example.com                          # full answer with sections
dig +short example.com                   # ⭐ just the answer
dig +short example.com MX
dig example.com NS +short
dig example.com TXT +short
dig @8.8.8.8 example.com                 # query a SPECIFIC resolver — bypasses local cache
dig @ns1.example.com example.com         # ask the authoritative server directly
dig +trace example.com                   # ⭐ walk root → TLD → authoritative yourself
dig -x 8.8.8.8                           # reverse lookup
dig +noall +answer example.com           # answer section only
dig +short example.com | tail -1         # final IP after any CNAME chain
dig example.com | grep -A1 "ANSWER SECTION"   # see the TTL

host example.com                         # simplest form
nslookup example.com                     # legacy but universal
getent hosts example.com                 # ⭐ resolves the way APPLICATIONS do
                                         #    (respects /etc/hosts + nsswitch.conf)

resolvectl query example.com             # systemd-resolved
resolvectl flush-caches                  # clear the local DNS cache
sudo systemd-resolve --statistics
```

**Diagnosing a DNS change that "didn't take":**

```bash
dig +short @ns1.provider.com example.com   # 1. is the authoritative record correct?
dig +short @8.8.8.8 example.com            # 2. has a public resolver picked it up?
dig +short example.com                     # 3. what does MY resolver say?
getent hosts example.com                   # 4. what will my APP see? (/etc/hosts wins)
dig example.com | grep -oP '^\S+\s+\K\d+'  # 5. remaining TTL — how long until caches expire
```

| Record | Maps | Note |
|--------|------|------|
| `A` | name → IPv4 | |
| `AAAA` | name → IPv6 | |
| `CNAME` | name → another name | Cannot coexist with other records at the same name; not allowed at the zone apex |
| `MX` | domain → mail server | Has a priority value |
| `TXT` | name → text | SPF, DKIM, domain verification |
| `NS` | domain → nameservers | Delegation |
| `SRV` | service → host:port | Service discovery |
| `PTR` | IP → name | Reverse DNS; needed for mail reputation |
| `CAA` | domain → allowed CAs | Restricts who can issue certs for you |

---

## curl

```bash
curl https://example.com                       # GET, body to stdout
curl -s URL                                    # silent (no progress meter)
curl -sS URL                                   # silent but still show errors  ⭐
curl -i URL                                    # include response headers
curl -I URL                                    # HEAD — headers only
curl -v URL                                    # verbose: request + response + TLS
curl -L URL                                    # follow redirects
curl -o file URL                               # save to a file
curl -O URL                                    # save using the remote filename
curl -f URL                                    # fail (exit 22) on HTTP >= 400  ⭐ for scripts
curl --max-time 10 --connect-timeout 3 URL     # always set timeouts in automation
curl --retry 3 --retry-delay 2 URL

# Methods and bodies
curl -X POST -H 'Content-Type: application/json' -d '{"k":"v"}' URL
curl -X POST -d @payload.json URL
curl -X PUT -d 'a=1&b=2' URL                   # form-encoded
curl -F 'file=@report.pdf' URL                 # multipart upload

# Auth
curl -u user:pass URL                          # basic auth
curl -H "Authorization: Bearer $TOKEN" URL
curl --cert client.pem --key client.key URL    # mutual TLS

# Debugging aids
curl -k URL                                    # skip cert verification ⚠️ diagnosis only
curl --resolve example.com:443:10.0.1.50 https://example.com   # ⭐ test a specific
                                               #   backend while keeping SNI/Host correct
curl -x http://proxy:3128 URL                  # via a proxy
curl -H 'Host: example.com' http://10.0.1.50/  # test a vhost by IP
curl --http1.1 URL                             # force protocol version
curl -sS URL 2>&1 | head -50
```

**Latency breakdown** — find out *which* phase is slow:

```bash
cat > curl-format.txt <<'EOF'
    dns:  %{time_namelookup}s
    tcp:  %{time_connect}s
    tls:  %{time_appconnect}s
   ttfb:  %{time_starttransfer}s
  total:  %{time_total}s   (http %{http_code}, %{size_download} bytes)
EOF

curl -w "@curl-format.txt" -o /dev/null -s https://example.com
```

**One-liner health check** for scripts and CI:

```bash
curl -sS -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 5 https://example.com/health
```

---

## Connectivity Testing

```bash
ping -c 4 host                     # 4 packets then stop
ping -i 0.2 -c 20 host             # faster interval
ping -s 1400 host                  # larger packets (MTU probing)

traceroute host                    # UDP by default
traceroute -T -p 443 host          # TCP traceroute — gets through more firewalls  ⭐
mtr host                           # continuous traceroute + loss stats
mtr -rwc 50 host                   # 50 cycles, report mode (good for tickets)

nc -zv host 443                    # port open? (-z scan, -v verbose)
nc -zv host 20-25                  # port range
nc -zvu host 53                    # UDP
nc -l 9000                         # listen on 9000 (a throwaway test server)
nc host 80                         # interactive: type an HTTP request by hand

# No netcat installed? bash can do it:
timeout 2 bash -c '</dev/tcp/example.com/443' && echo open || echo closed

nmap -Pn -p 22,80,443 host         # scan specific ports (authorised targets only)
nmap -sV -p 443 host               # service/version detection

telnet host 443                    # legacy but present everywhere
```

---

## Packet Capture

```bash
sudo tcpdump -i any -nn -c 50                      # 50 packets, no name resolution
sudo tcpdump -i eth0 port 443                      # by port
sudo tcpdump -i any host 10.0.1.50                 # by host
sudo tcpdump -i any 'port 80 and host 10.0.1.50'
sudo tcpdump -i any 'tcp[tcpflags] & tcp-syn != 0' # SYN packets only — connection attempts
sudo tcpdump -i any -A port 80                     # print payload as ASCII (plain HTTP)
sudo tcpdump -i any -w capture.pcap port 443       # write for Wireshark
sudo tcpdump -r capture.pcap -nn                   # read it back
sudo tcpdump -i any -nn 'icmp'                     # ICMP only
sudo tcpdump -i any -nn 'port 53'                  # watch DNS queries live
```

| Flag | Why |
|------|-----|
| `-i any` | Capture on all interfaces |
| `-nn` | Don't resolve hostnames **or** port names (much faster, no DNS noise) |
| `-c N` | Stop after N packets — always use this on a busy host |
| `-s 0` | Capture full packets (default is truncated on old versions) |
| `-w file` | Write raw pcap for offline analysis |
| `-A` / `-X` | ASCII / hex payload |

> 💡 On a busy production box, an unfiltered `tcpdump` can saturate the disk in seconds. **Always** pair it with a filter and `-c`.

---

## Firewalls

### ufw (Debian/Ubuntu)

```bash
sudo ufw status verbose
sudo ufw status numbered
sudo ufw allow 22/tcp                       # ⚠️ DO THIS BEFORE 'ufw enable'
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow proto tcp from 203.0.113.0/24 to any port 22
sudo ufw deny 3306
sudo ufw delete 3                           # by rule number
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable / disable
sudo ufw reset
```

### firewalld (RHEL family)

```bash
sudo firewall-cmd --state
sudo firewall-cmd --list-all
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --add-service=https --permanent
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --add-rich-rule='rule family=ipv4 source address=10.0.0.0/8 port port=5432 protocol=tcp accept' --permanent
sudo firewall-cmd --remove-port=8080/tcp --permanent
sudo firewall-cmd --reload                  # ⚠️ --permanent changes need this
sudo firewall-cmd --runtime-to-permanent    # keep changes you tested live
```

### iptables / nftables

```bash
sudo iptables -L -n -v --line-numbers       # list with counters
sudo iptables -t nat -L -n                  # NAT table (Docker writes here)
sudo iptables -D INPUT 3                    # delete rule 3
sudo iptables-save > rules.v4               # backup

sudo nft list ruleset                       # nftables equivalent
```

> ⚠️ **Never enable a firewall before allowing SSH.** The classic sequence that locks you out of a remote box: `ufw enable` with no `allow 22`. If you must risk it, schedule a safety net first: `echo 'ufw disable' | sudo at now + 5 minutes`.

---

## Nginx

```bash
sudo nginx -t                          # ⭐ TEST CONFIG — always before reload
sudo nginx -T                          # test AND dump the full effective config
sudo systemctl reload nginx            # graceful: no dropped connections
sudo systemctl restart nginx           # drops connections — avoid in prod
nginx -v / nginx -V                    # version / version + compile flags

tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log       # ⭐ where the real reason lives
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head    # top client IPs
awk '{print $9}' access.log | sort | uniq -c | sort -rn           # status code counts
grep ' 5[0-9][0-9] ' access.log | tail -20                        # recent 5xx
```

**Minimal reverse proxy:**

```nginx
server {
    listen 80;
    server_name app.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout    60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8080/health;
        access_log off;
    }
}
```

| Nginx error | Meaning |
|-------------|---------|
| `502 Bad Gateway` | Nginx reached nothing — backend down, wrong port, or refused |
| `504 Gateway Timeout` | Backend accepted but didn't answer within `proxy_read_timeout` |
| `413 Request Entity Too Large` | Raise `client_max_body_size` |
| `connect() failed (111: Connection refused)` | Backend isn't listening on that address/port |
| `no live upstreams` | All backends failed their health checks |
| `SSL_do_handshake() failed` | Upstream TLS mismatch — check `proxy_ssl_server_name on;` |

---

## TLS & Certificates

```bash
# Inspect a live endpoint
openssl s_client -connect example.com:443 -servername example.com </dev/null
openssl s_client -connect example.com:443 -servername example.com -brief </dev/null

# Expiry dates
echo | openssl s_client -connect example.com:443 2>/dev/null \
  | openssl x509 -noout -dates

# Everything about the served certificate
echo | openssl s_client -connect example.com:443 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName

# Full chain the server actually sends (missing intermediates show up here)
openssl s_client -connect example.com:443 -showcerts </dev/null

# Local files
openssl x509 -in cert.pem -noout -text            # full details
openssl x509 -in cert.pem -noout -enddate
openssl rsa  -in key.pem  -check                  # is the key valid?
openssl req  -in csr.pem  -noout -text            # inspect a CSR

# Do the cert and key actually match? (the two hashes must be identical)
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa  -noout -modulus -in key.pem  | openssl md5

# Self-signed cert for local testing
openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
  -keyout key.pem -out cert.pem -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

# Protocol support
openssl s_client -connect example.com:443 -tls1_2 </dev/null
nmap --script ssl-enum-ciphers -p 443 example.com
```

| Symptom | Cause | Fix |
|---------|-------|-----|
| `certificate has expired` | Past `notAfter` | Renew; automate with certbot/cert-manager |
| `unable to get local issuer certificate` | **Incomplete chain** — works in browsers, fails in curl/containers | Serve the intermediate; use fullchain.pem |
| `Hostname mismatch` | Requested name not in SAN | Reissue with the correct SANs |
| `self signed certificate` | Untrusted issuer | Add the CA to the trust store, or use a real cert |
| `handshake failure` | No shared protocol/cipher | Check TLS version and cipher config |
| Works by IP, fails by name | SNI not sent or wrong vhost | Use `--resolve` or `-servername` |

---

## Reference Tables

### Common ports

| Port | Service | | Port | Service |
|------|---------|-|------|---------|
| 22 | SSH | | 5601 | Kibana |
| 25 / 587 | SMTP / submission | | 6379 | Redis |
| 53 | DNS (UDP + TCP) | | 8080 | HTTP alt / app servers |
| 80 | HTTP | | 8443 | HTTPS alt |
| 123 | NTP (UDP) | | 9000 | Portainer / SonarQube |
| 443 | HTTPS | | 9090 | Prometheus |
| 3000 | Grafana / Node dev | | 9093 | Alertmanager |
| 3100 | Loki | | 9100 | node_exporter |
| 3306 | MySQL / MariaDB | | 9200 / 9300 | Elasticsearch HTTP / transport |
| 5432 | PostgreSQL | | 27017 | MongoDB |
| 5672 / 15672 | RabbitMQ / its UI | | 2379–2380 | etcd |
| 6443 | Kubernetes API server | | 10250 | kubelet API |

### HTTP status codes

| Code | Meaning | What it tells a DevOps engineer |
|------|---------|--------------------------------|
| **200** | OK | Working |
| **201** | Created | Successful POST |
| **204** | No Content | Success, empty body |
| **301 / 308** | Moved permanently | Cached by browsers — be careful, hard to undo |
| **302 / 307** | Found / temporary redirect | Safe to change later |
| **304** | Not Modified | Cache hit — good |
| **400** | Bad Request | Malformed client request |
| **401** | Unauthorized | **Not authenticated** — missing/invalid credentials |
| **403** | Forbidden | **Authenticated but not allowed** — an authorization problem |
| **404** | Not Found | Wrong path, or the wrong vhost/ingress rule matched |
| **405** | Method Not Allowed | GET where POST was expected |
| **408** | Request Timeout | Client too slow |
| **409** | Conflict | Concurrent modification |
| **413** | Payload Too Large | Raise the proxy body limit |
| **418** | I'm a teapot | Someone had fun |
| **429** | Too Many Requests | Rate limited — check `Retry-After` |
| **500** | Internal Server Error | The app threw — read app logs |
| **502** | Bad Gateway | Proxy couldn't reach the backend |
| **503** | Service Unavailable | Overloaded, or no healthy backends |
| **504** | Gateway Timeout | Backend too slow for the proxy's timeout |

> 💡 **401 vs 403** is the most common interview trip-up: 401 = "who are you?", 403 = "I know who you are, and no."
> **502 vs 504** is the most common ops trip-up: 502 = the backend never answered the connection, 504 = it answered but too slowly.

### CIDR quick math

| CIDR | Mask | Total | Usable | AWS usable* |
|------|------|-------|--------|-------------|
| `/32` | 255.255.255.255 | 1 | 1 | 1 |
| `/30` | 255.255.255.252 | 4 | 2 | — |
| `/28` | 255.255.255.240 | 16 | 14 | 11 |
| `/26` | 255.255.255.192 | 64 | 62 | 59 |
| `/24` | 255.255.255.0 | 256 | 254 | 251 |
| `/22` | 255.255.252.0 | 1,024 | 1,022 | 1,019 |
| `/20` | 255.255.240.0 | 4,096 | 4,094 | 4,091 |
| `/16` | 255.255.0.0 | 65,536 | 65,534 | 65,531 |

\* AWS reserves 5 addresses per subnet, not 2.

**Formula**: host bits = `32 − prefix`; total = `2^host bits`; usable = total − 2 (network + broadcast).

**Private ranges (RFC 1918)**: `10.0.0.0/8` · `172.16.0.0/12` · `192.168.0.0/16`. Also reserved: `127.0.0.0/8` loopback, `169.254.0.0/16` link-local (this is where cloud metadata lives at `169.254.169.254`), `100.64.0.0/10` carrier-grade NAT.

```bash
ipcalc 10.0.1.0/24          # human-readable breakdown
sipcalc 10.0.1.0/24         # alternative
python3 -c "import ipaddress as i; n=i.ip_network('10.0.1.0/24'); print(n.network_address, n.broadcast_address, n.num_addresses)"
```

---

<div align="center">

[← Module 02 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
