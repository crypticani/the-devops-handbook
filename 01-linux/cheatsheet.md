# Module 01: Linux — Cheat Sheet

> Command reference for daily Linux work. For the *why* behind these, read the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Navigation](#navigation--files) · [Viewing](#viewing-file-contents) · [Search](#finding-things) · [Permissions](#permissions--ownership) · [Users](#users--groups) · [Processes](#processes--signals) · [systemd](#systemd--services) · [Packages](#package-management) · [Text Processing](#text-processing) · [Disk](#disk--storage) · [Network](#networking-from-the-host) · [SSH](#ssh) · [Cron](#cron--scheduling) · [Archives](#archives--compression) · [Environment](#environment--shell) · [Triage](#one-minute-server-triage)

---

## Navigation & Files

| Command | What it does |
|---------|--------------|
| `pwd` | Print working directory |
| `cd -` | Jump back to the **previous** directory |
| `cd` | Go home (same as `cd ~`) |
| `ls -lah` | Long listing, all files, human-readable sizes |
| `ls -lt` / `ls -ltr` | Sort by mtime, newest first / oldest last |
| `ls -lS` | Sort by size, largest first |
| `tree -L 2` | Directory tree, 2 levels deep |
| `mkdir -p a/b/c` | Create nested directories, no error if they exist |
| `cp -a src dst` | Copy preserving **all** attributes (archive mode) |
| `cp -r src dst` | Copy directory recursively |
| `mv old new` | Move or rename |
| `rm -rf dir` | Delete recursively, no prompts — **no undo** |
| `ln -s target link` | Create a symbolic link |
| `readlink -f path` | Resolve a path to its absolute, symlink-free form |
| `basename /a/b/c.txt` | → `c.txt` |
| `dirname /a/b/c.txt` | → `/a/b` |
| `stat file` | Size, permissions, inode, all three timestamps |
| `file archive.bin` | Identify a file's actual type (ignores the extension) |
| `touch file` | Create empty file, or update its mtime |
| `df -h` | Free space per mounted filesystem |
| `du -sh *` | Size of each item in the current directory |

```bash
# Safe rm habits
rm -i file                    # prompt before each delete
rm -rf -- "$dir"              # -- stops a name starting with '-' being read as a flag
[ -n "$dir" ] && rm -rf "$dir"   # never let an empty variable become 'rm -rf /'
```

> ⚠️ `rm -rf $VAR` with `VAR` unset expands to `rm -rf` in the current directory — or worse. Always quote and always guard.

---

## Viewing File Contents

| Command | What it does |
|---------|--------------|
| `cat file` | Print the whole file |
| `cat -n file` | ...with line numbers |
| `less file` | Page through it (`/` search, `n` next, `G` end, `q` quit) |
| `less +F file` | Follow mode — like `tail -f` but you can Ctrl-C and scroll |
| `head -n 20 file` | First 20 lines |
| `tail -n 50 file` | Last 50 lines |
| `tail -f file` | **Follow** a growing log in real time |
| `tail -F file` | Follow, and survive log rotation |
| `tail -f a.log b.log` | Follow multiple files with headers |
| `wc -l file` | Count lines (`-w` words, `-c` bytes) |
| `nl file` | Number only non-blank lines |
| `zcat` / `zless` / `zgrep` | Same tools, for `.gz` files — no need to decompress |

```bash
# Follow a log but only show what matters
tail -f /var/log/nginx/error.log | grep --line-buffered -i "upstream"
#                                       ^^^^^^^^^^^^^^^ without this, grep
#                                       buffers and output appears in bursts
```

---

## Finding Things

### `find` — search by metadata

```bash
find /var/log -name "*.log"                  # by name (case-sensitive)
find . -iname "*.YAML"                       # case-insensitive
find . -type f -size +100M                   # files over 100 MB
find . -type d -name node_modules            # directories
find /etc -mtime -1                          # modified in the last 24h
find /tmp -mmin +60 -delete                  # older than 60 min, delete
find . -type f -perm 0777                    # world-writable files
find . -user deploy -group www-data          # by ownership
find . -name "*.log" -exec gzip {} \;        # run a command per result
find . -name "*.log" -print0 | xargs -0 rm   # safe with spaces in filenames

# Exclude a directory (note the ordering)
find . -path ./node_modules -prune -o -name "*.js" -print
```

### `grep` — search by content

```bash
grep "ERROR" app.log                  # basic
grep -i "error" app.log               # case-insensitive
grep -r "TODO" ./src                  # recursive
grep -rn "func main" .                # with line numbers
grep -v "healthcheck" access.log      # INVERT — exclude matches
grep -c "ERROR" app.log               # count matching lines
grep -l "apiKey" -r .                 # list filenames only
grep -A 5 -B 5 "panic" app.log        # 5 lines After / Before
grep -C 3 "panic" app.log             # 3 lines of Context both sides
grep -E "warn|error|fatal" app.log    # extended regex (alternation)
grep -w "id" file                     # whole word only — not "uuid"
grep -o "[0-9]\{1,3\}\.[0-9...]"      # print only the matched part
grep --include="*.py" -r "import os" .   # filter by filename pattern
```

| Other locators | Use |
|----------------|-----|
| `which python3` | Path of the binary that will run |
| `type -a ls` | Shows aliases, functions, **and** all binaries named `ls` |
| `command -v tool` | Portable "does this exist?" test in scripts |
| `whereis nginx` | Binary, source, and man page locations |
| `locate filename` | Instant search of a prebuilt index (`sudo updatedb` to refresh) |
| `lsof /path/to/file` | Which processes have this file open |
| `fuser -v /mnt/data` | Who is using this mount (blocks unmounting) |

---

## Permissions & Ownership

```
-rwxr-xr--  1  deploy  www-data  4096  Aug  4 09:12  deploy.sh
│└┬┘└┬┘└┬┘     └──┬─┘  └───┬──┘
│ │  │  └── other: r--     └── group
│ │  └───── group: r-x
│ └──────── owner: rwx
└────────── type: - file, d dir, l symlink
```

| Numeric | Symbolic | Meaning | Typical use |
|---------|----------|---------|-------------|
| `400` | `r--------` | Owner read only | Root-owned secrets |
| `600` | `rw-------` | Owner read/write | **SSH private keys**, `.env`, tokens |
| `640` | `rw-r-----` | Owner rw, group read | Config with secrets, shared with a service group |
| `644` | `rw-r--r--` | Owner rw, everyone read | Normal config, HTML, `authorized_keys` |
| `700` | `rwx------` | Owner full | `~/.ssh`, private script dirs |
| `750` | `rwxr-x---` | Owner full, group execute | Service directories |
| `755` | `rwxr-xr-x` | Owner full, everyone read/execute | **Directories**, binaries, scripts |
| `775` | `rwxrwxr-x` | Group can write | Shared team directories |
| `777` | `rwxrwxrwx` | Everyone everything | ❌ Never in production |

```bash
chmod 640 config.yml               # numeric
chmod u+x script.sh                # symbolic: add execute for owner
chmod g-w,o-rwx file               # remove group write, all other access
chmod -R u+rwX,go-w dir/           # capital X = execute on DIRS only, not files
chown deploy:www-data file         # change owner and group
chown -R deploy: /srv/app          # trailing colon = set group to owner's group
chgrp docker /var/run/docker.sock  # change group only

# Special bits
chmod u+s binary          # setuid  (4xxx) — runs as the file's OWNER
chmod g+s shared/         # setgid  (2xxx) — new files inherit the DIRECTORY's group
chmod +t /tmp             # sticky  (1xxx) — only the owner can delete their files

umask                     # show default-permission mask (022 → new files 644, dirs 755)
```

**Access Control Lists** — when the owner/group/other model isn't enough:

```bash
getfacl file                                 # view ACLs
setfacl -m u:jenkins:rx /srv/app             # grant one user read+execute
setfacl -m d:u:jenkins:rx /srv/app           # d: = default for new files in this dir
setfacl -x u:jenkins /srv/app                # remove that entry
setfacl -b file                              # strip all ACLs
```

> 💡 A `+` at the end of `ls -l` permissions (`-rw-r--r--+`) means an ACL exists. If permissions "look right" but access still fails, check `getfacl` — and on RHEL-family systems, check SELinux with `ls -Z` and `ausearch -m avc -ts recent`.

---

## Users & Groups

```bash
whoami                              # current username
id                                  # uid, gid, and all group memberships
id -nG deploy                       # just the group names for a user
groups                              # your groups
who / w                             # who is logged in (w adds what they're doing)
last -n 20                          # recent logins
lastb                               # FAILED login attempts

# Create a service account with no login shell
sudo useradd -r -s /usr/sbin/nologin -d /srv/app -M appuser
sudo useradd -m -s /bin/bash alice            # normal user with a home dir
sudo passwd alice
sudo usermod -aG docker,sudo alice            # -aG = APPEND (omitting -a wipes groups!)
sudo usermod -L alice                         # lock the account
sudo userdel -r alice                         # delete user and home dir

sudo groupadd deployers
sudo gpasswd -d alice docker                  # remove alice from docker group
```

| File | Contains |
|------|----------|
| `/etc/passwd` | Usernames, UIDs, home dirs, shells (world-readable, no passwords) |
| `/etc/shadow` | Password hashes and aging policy (root only) |
| `/etc/group` | Group definitions and members |
| `/etc/sudoers`, `/etc/sudoers.d/` | Who may run what as whom — edit with `visudo` only |

```bash
sudo visudo                          # validates syntax before saving — ALWAYS use this
sudo visudo -f /etc/sudoers.d/deploy # per-purpose drop-in file (preferred)
# deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart myapp
sudo -l                              # what am I allowed to run?
sudo -u postgres psql                # run as another user
```

> ⚠️ `usermod -G` **replaces** a user's supplementary groups. Forgetting `-a` is how you lock yourself out of `sudo`. Group changes also only apply to **new** sessions — log out and back in, or run `newgrp docker`.

---

## Processes & Signals

```bash
ps aux                              # every process, BSD syntax
ps -ef                              # every process, System V syntax
ps aux --sort=-%mem | head          # top memory consumers
ps aux --sort=-%cpu | head          # top CPU consumers
ps -eo pid,ppid,user,%cpu,%mem,etime,cmd --sort=-%cpu | head
ps -p 1234 -o etime,cmd             # how long has PID 1234 been running
pstree -p                           # process tree with PIDs
pgrep -a nginx                      # PIDs matching a name, with command line
pgrep -u deploy                     # processes owned by a user

top                                 # live view (press M=mem, P=cpu, 1=per-core, q=quit)
htop                                # nicer top (F6 sort, F9 kill, / search)
```

### Signals

| Signal | Number | Effect | When to use |
|--------|--------|--------|-------------|
| `SIGTERM` | 15 | Polite shutdown request — **catchable** | Default. Always try this first |
| `SIGINT` | 2 | Interrupt, what Ctrl-C sends | Interactive stop |
| `SIGHUP` | 1 | Historically "hang up"; most daemons **reload config** | `kill -HUP $(pidof nginx)` |
| `SIGKILL` | 9 | Immediate, uncatchable, no cleanup | Last resort — leaves temp files and locks behind |
| `SIGSTOP` / `SIGCONT` | 19 / 18 | Pause / resume | Freeze a runaway job to investigate |
| `SIGUSR1` / `SIGUSR2` | 10 / 12 | App-defined | e.g. Nginx log reopen |

```bash
kill 1234                  # SIGTERM (default)
kill -9 1234               # SIGKILL
kill -HUP 1234             # reload config
pkill -f "python worker"   # match the FULL command line
killall nginx              # by exact process name
kill -l                    # list all signal names
```

### Job control & background work

```bash
command &                  # start in background
jobs                       # list this shell's jobs
fg %1                      # bring job 1 to foreground
bg %1                      # resume job 1 in background
Ctrl-Z                     # suspend the foreground job
disown -h %1               # detach job from the shell so it survives logout
nohup ./long.sh > out.log 2>&1 &     # immune to hangup
setsid ./long.sh           # fully detach into a new session

nice -n 10 ./batch.sh      # start with lower priority (19 = nicest)
renice -n 5 -p 1234        # change priority of a running process
ionice -c3 -p 1234         # idle-priority disk I/O
timeout 30s ./flaky.sh     # kill it if it exceeds 30 seconds
```

### Resource inspection

```bash
free -h                    # memory; look at "available", not "free"
vmstat 1 5                 # 5 samples, 1s apart — r/b queues, si/so swap
iostat -xz 1               # per-device disk latency (%util, await)
uptime                     # load average: 1min, 5min, 15min
nproc                      # number of CPUs (load avg should be judged against this)
lsof -p 1234               # every file/socket that PID has open
lsof -i :8080              # what is using port 8080
cat /proc/1234/limits      # ulimits actually applied to a running process
cat /proc/1234/environ | tr '\0' '\n'   # its environment variables
ulimit -a                  # your shell's limits (-n open files is the usual culprit)
```

---

## systemd & Services

```bash
# ─── Status and control ───
systemctl status nginx                 # state + recent log lines + PID + cgroup
systemctl start|stop|restart nginx
systemctl reload nginx                 # re-read config WITHOUT dropping connections
systemctl reload-or-restart nginx      # reload if supported, else restart
systemctl enable nginx                 # start at boot
systemctl disable nginx
systemctl enable --now nginx           # enable AND start in one step
systemctl is-active nginx              # scriptable: exits 0 if running
systemctl is-enabled nginx
systemctl mask nginx                   # make it impossible to start (stronger than disable)
systemctl unmask nginx

# ─── Discovery ───
systemctl list-units --type=service                 # loaded services
systemctl list-units --type=service --state=failed  # ⭐ what is broken right now
systemctl list-unit-files --state=enabled           # what starts at boot
systemctl list-dependencies nginx
systemctl cat nginx                    # the effective unit file + all overrides
systemctl show nginx -p Restart -p ExecStart        # query specific properties

# ─── Editing (never edit files in /lib/systemd directly) ───
sudo systemctl edit nginx              # creates a drop-in override
sudo systemctl edit --full nginx       # copy the whole unit to /etc for editing
sudo systemctl daemon-reload           # ⚠️ REQUIRED after any unit file change
```

### journalctl

```bash
journalctl -u nginx                    # all logs for one unit
journalctl -u nginx -f                 # follow (like tail -f)
journalctl -u nginx -n 100             # last 100 lines
journalctl -u nginx --since "10 min ago"
journalctl -u nginx --since today --until "2026-08-04 14:00"
journalctl -u nginx -p err             # priority err and worse (emerg..debug)
journalctl -u nginx -o json-pretty     # full structured fields
journalctl -k                          # kernel messages (dmesg)
journalctl -b                          # this boot;  -b -1 = previous boot
journalctl --list-boots
journalctl -xe                         # ⭐ end of the log with explanations — after a failed start
journalctl _PID=1234                   # by PID
journalctl --disk-usage
sudo journalctl --vacuum-time=7d       # trim logs older than 7 days
```

### Minimal unit file

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application
After=network-online.target
Wants=network-online.target

[Service]
Type=simple                  # simple | exec | forking | oneshot | notify
User=appuser
Group=appuser
WorkingDirectory=/srv/app
EnvironmentFile=-/etc/myapp/env      # leading '-' = don't fail if missing
ExecStart=/srv/app/bin/server
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5s

# Hardening — cheap and effective
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/srv/app/data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now myapp
systemd-analyze verify /etc/systemd/system/myapp.service   # lint it
systemd-analyze blame                                      # slowest units at boot
```

### Timers (the modern cron)

```bash
systemctl list-timers --all            # all timers with next/last run
sudo systemctl enable --now backup.timer
journalctl -u backup.service           # timers log under the SERVICE name
```

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Nightly backup
[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true              # run on next boot if the machine was off
RandomizedDelaySec=300       # spread load across a fleet
[Install]
WantedBy=timers.target
```

---

## Package Management

**Debian/Ubuntu (`apt`) and RHEL-family (`dnf`) side by side.** RHEL-family = RHEL, Rocky, AlmaLinux, CentOS Stream, Fedora, Amazon Linux 2023 (`yum` is a symlink to `dnf` on modern systems).

| Task | Debian / Ubuntu | RHEL family |
|------|-----------------|-------------|
| Refresh metadata | `sudo apt update` | `sudo dnf check-update` (automatic) |
| Upgrade everything | `sudo apt upgrade` | `sudo dnf upgrade` |
| Full/dist upgrade | `sudo apt full-upgrade` | `sudo dnf distro-sync` |
| Install | `sudo apt install nginx` | `sudo dnf install nginx` |
| Install a local file | `sudo apt install ./pkg.deb` | `sudo dnf install ./pkg.rpm` |
| Remove | `sudo apt remove nginx` | `sudo dnf remove nginx` |
| Remove + config files | `sudo apt purge nginx` | *(no exact equivalent)* |
| Remove orphans | `sudo apt autoremove` | `sudo dnf autoremove` |
| Search | `apt search nginx` | `dnf search nginx` |
| Show package info | `apt show nginx` | `dnf info nginx` |
| Is it installed? | `dpkg -l \| grep nginx` | `rpm -q nginx` |
| List installed files | `dpkg -L nginx` | `rpm -ql nginx` |
| Which package owns a file | `dpkg -S /usr/sbin/nginx` | `rpm -qf /usr/sbin/nginx` |
| Available versions | `apt-cache policy nginx` | `dnf --showduplicates list nginx` |
| Pin/hold a version | `sudo apt-mark hold nginx` | `sudo dnf versionlock add nginx` |
| List repos | `ls /etc/apt/sources.list.d/` | `dnf repolist` |
| Add a repo | `add-apt-repository ppa:...` | `dnf config-manager --add-repo URL` |
| Clean cache | `sudo apt clean` | `sudo dnf clean all` |
| Transaction history | `/var/log/apt/history.log` | `dnf history` / `dnf history undo N` |
| Security updates only | `sudo unattended-upgrade` | `sudo dnf update --security` |
| Does a reboot pending? | `ls /var/run/reboot-required` | `dnf needs-restarting -r` |

```bash
# Non-interactive install in scripts and Dockerfiles (Debian)
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && sudo apt-get install -y --no-install-recommends nginx
sudo rm -rf /var/lib/apt/lists/*        # shrink container images

# RHEL equivalent
sudo dnf install -y nginx && sudo dnf clean all
```

**Language/tool package managers you'll also meet:** `snap`, `flatpak`, `pip`, `npm`, `cargo`, `go install`, `brew`.

---

## Text Processing

### `sed` — stream editing

```bash
sed 's/old/new/' file              # replace FIRST match on each line
sed 's/old/new/g' file             # replace ALL matches
sed 's/old/new/gi' file            # ...case-insensitive
sed -i 's/old/new/g' file          # edit the file IN PLACE
sed -i.bak 's/old/new/g' file      # in place, keeping file.bak  ⭐ safer
sed -n '10,20p' file               # print only lines 10-20
sed '5d' file                      # delete line 5
sed '/^#/d' file                   # delete comment lines
sed '/^$/d' file                   # delete blank lines
sed -e 's/a/b/' -e 's/c/d/' file   # multiple expressions
sed 's|/old/path|/new/path|g' f    # use | when the text contains /
sed '$a\appended line' file        # append after the last line
```

### `awk` — column and field processing

```bash
awk '{print $1}' file                          # first whitespace-separated field
awk '{print $NF}' file                         # LAST field
awk -F: '{print $1, $7}' /etc/passwd           # custom delimiter
awk -F'\t' '{print $2}' data.tsv
awk '$3 > 100' file                            # filter rows by a numeric field
awk '/ERROR/ {print $0}' app.log               # filter by pattern
awk '{sum += $2} END {print sum}' file         # sum a column
awk '{sum += $2} END {print sum/NR}' file      # average
awk 'NR % 2 == 0' file                         # every even line
awk '!seen[$0]++' file                         # dedupe, PRESERVING order ⭐
awk '{print NR": "$0}' file                    # number the lines
awk 'BEGIN{OFS=","} {print $1,$3}' file        # change output separator

# Top 10 IPs in an Nginx access log
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -10
```

### `cut`, `sort`, `uniq`, `tr`, `column`

```bash
cut -d: -f1,7 /etc/passwd          # fields 1 and 7, colon-delimited
cut -c1-10 file                    # characters 1-10
sort file                          # alphabetical
sort -n file                       # numeric
sort -rn file                      # numeric, descending
sort -u file                       # sort and dedupe
sort -k3 -n file                   # sort by the 3rd field, numerically
sort -t, -k2 file.csv              # comma-delimited, 2nd field
uniq -c                            # count occurrences (input MUST be sorted)
uniq -d                            # show only duplicated lines
tr 'a-z' 'A-Z' < file              # upper-case
tr -d '\r' < win.txt > unix.txt    # strip carriage returns
tr -s ' '                          # squeeze repeated spaces
column -t file                     # align into columns
paste a.txt b.txt                  # join files side by side
join -t, -1 1 -2 1 a.csv b.csv     # relational join on a key
comm -13 sorted_a sorted_b         # lines only in b
diff -u old new                    # unified diff
diff <(cmd1) <(cmd2)               # ⭐ diff two command outputs directly
```

### `jq` and `yq` — structured data

```bash
jq '.' file.json                                  # pretty-print
jq -r '.items[].name' file.json                   # -r = raw strings, no quotes
jq '.items | length' file.json
jq '.[] | select(.status == "failed")' file.json
jq -r '.[] | [.name, .ip] | @tsv' file.json       # tab-separated output
jq 'map(.cost) | add' file.json                   # sum a field
curl -s api/endpoint | jq -r '.data.token'
jq --arg env prod '.envs[$env]' file.json         # pass a shell variable in

yq '.spec.replicas' deployment.yml                # same idea, for YAML
yq -i '.spec.replicas = 5' deployment.yml         # edit in place
yq -o=json '.' file.yml                           # YAML → JSON
```

---

## Disk & Storage

```bash
df -h                              # free space per filesystem
df -i                              # INODE usage — "No space left" with df -h clean? this is why
du -sh /var/log                    # total size of a directory
du -h --max-depth=1 /var | sort -h # ⭐ find the big subdirectory
du -ah /var | sort -rh | head -20  # 20 largest items
ncdu /var                          # interactive disk usage browser

lsblk                              # block devices and mount points
lsblk -f                           # ...with filesystem type and UUID
blkid                              # UUIDs for /etc/fstab
mount | column -t                  # what's mounted where
findmnt                            # mount tree

sudo mount /dev/sdb1 /mnt/data
sudo umount /mnt/data
sudo mount -a                      # mount everything in /etc/fstab (test before reboot!)

sudo mkfs.ext4 /dev/sdb1           # format — DESTROYS DATA
sudo fsck -f /dev/sdb1             # check filesystem (unmounted only)
sudo resize2fs /dev/sdb1           # grow ext4 after enlarging the disk
sudo xfs_growfs /mnt/data          # grow XFS

# LVM
pvs / vgs / lvs                    # physical / volume group / logical volume summary
sudo lvextend -L +10G -r /dev/vg0/lv_data   # -r also resizes the filesystem
```

> 💡 **"Disk full" but `df -h` shows space?** Three usual causes: **(1)** inodes exhausted → `df -i`; **(2)** a deleted file still held open by a process → `lsof +L1` or `lsof | grep deleted`, then restart that process; **(3)** you're looking at a different filesystem than the one that's full.

---

## Networking from the Host

```bash
ip a                               # interfaces and addresses (replaces ifconfig)
ip -br a                           # brief, one line per interface
ip r                               # routing table
ip route get 8.8.8.8               # which interface/gateway would be used
ip neigh                           # ARP table

ss -tlnp                           # ⭐ TCP listening sockets + owning process
ss -tunap                          # TCP+UDP, all states, numeric, with process
ss -s                              # socket summary counts
ss state time-wait | wc -l         # TIME_WAIT count

ping -c 4 host
traceroute host                    # or: mtr host  (continuous, better)
dig +short example.com
curl -sSf -o /dev/null -w '%{http_code} %{time_total}s\n' https://example.com
nc -zv host 443                    # port reachability test
sudo tcpdump -i any -nn port 443 -c 20     # capture 20 packets

# Firewalls
sudo ufw status verbose            # Debian/Ubuntu
sudo firewall-cmd --list-all       # RHEL family
sudo iptables -L -n -v --line-numbers
sudo nft list ruleset              # nftables (modern)
```

Full networking reference: **[Module 02 cheat sheet](../02-networking/cheatsheet.md)**

---

## SSH

```bash
ssh user@host
ssh -i ~/.ssh/id_ed25519 user@host
ssh -p 2222 user@host
ssh -v user@host                   # verbose — the first debugging step (-vvv for more)
ssh user@host 'uptime; df -h'      # run a command and exit
ssh -J bastion user@private-host   # ⭐ jump/bastion host in one flag

# Keys
ssh-keygen -t ed25519 -C "you@example.com"     # ed25519 is the modern default
ssh-copy-id user@host                          # install your public key remotely
ssh-add -l                                     # keys loaded in the agent
eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519
ssh-keyscan host >> ~/.ssh/known_hosts         # pre-trust a host (verify the fingerprint!)

# Tunnels
ssh -L 8080:localhost:80 user@host    # LOCAL: my :8080 → host's :80
ssh -R 9000:localhost:3000 user@host  # REMOTE: host's :9000 → my :3000
ssh -D 1080 user@host                 # SOCKS proxy through the host
ssh -fN -L 5432:db.internal:5432 user@bastion   # background, no shell

# File transfer
scp file user@host:/path/
scp -r dir/ user@host:/path/
rsync -avz --progress src/ user@host:/dst/      # ⭐ resumable, only sends deltas
rsync -avz --delete --dry-run src/ dst/         # preview a mirroring sync
```

```
# ~/.ssh/config — stop typing flags
Host prod
    HostName 10.0.1.50
    User deploy
    Port 22
    IdentityFile ~/.ssh/prod_ed25519
    ProxyJump bastion
    ServerAliveInterval 60
    ForwardAgent no
```

**Required permissions** — SSH silently refuses keys otherwise:

| Path | Mode |
|------|------|
| `~/.ssh` | `700` |
| `~/.ssh/id_*` (private) | `600` |
| `~/.ssh/id_*.pub` | `644` |
| `~/.ssh/authorized_keys` | `600` |
| `~` (home dir) | not group/world writable |

**Server hardening** (`/etc/ssh/sshd_config`, then `sudo sshd -t && sudo systemctl reload sshd`):

```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
AllowUsers deploy admin
```

> ⚠️ Always `sudo sshd -t` (config test) **before** reloading, and keep your current session open until you've verified a new one works.

---

## Cron & Scheduling

```
┌───── minute (0-59)
│ ┌─── hour (0-23)
│ │ ┌─ day of month (1-31)
│ │ │ ┌─ month (1-12)
│ │ │ │ ┌─ day of week (0-7, both 0 and 7 = Sunday)
│ │ │ │ │
* * * * *  command
```

| Expression | Runs |
|------------|------|
| `*/5 * * * *` | Every 5 minutes |
| `0 * * * *` | Top of every hour |
| `30 2 * * *` | 02:30 daily |
| `0 3 * * 0` | 03:00 every Sunday |
| `0 0 1 * *` | Midnight on the 1st of each month |
| `0 9-17 * * 1-5` | Hourly, 9am–5pm, weekdays |
| `@reboot` | Once at boot |
| `@daily` / `@hourly` | Shorthand |

```bash
crontab -e                         # edit YOUR crontab
crontab -l                         # list it
crontab -r                         # ⚠️ delete it (no confirmation)
sudo crontab -u deploy -l          # another user's crontab
ls /etc/cron.d/ /etc/cron.daily/   # system-wide cron drop-ins
grep CRON /var/log/syslog          # Debian: did it run?
journalctl -u crond                # RHEL: did it run?
```

```bash
# A cron entry that will actually work
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
MAILTO=ops@example.com
30 2 * * * /srv/app/backup.sh >> /var/log/backup.log 2>&1
```

> ⚠️ **Cron's environment is nearly empty.** No `PATH` beyond a minimal default, no shell profile, no `$HOME` assumptions. Use **absolute paths** for every binary and file, redirect both stdout and stderr, and test with `env -i /bin/bash --noprofile --norc -c '/srv/app/backup.sh'` to simulate it. For anything important, prefer a **systemd timer** — you get logging, dependencies, and `systemctl list-timers` for free.

---

## Archives & Compression

```bash
tar -czvf out.tar.gz dir/          # Create gZipped, Verbose, File
tar -xzvf in.tar.gz                # eXtract
tar -xzvf in.tar.gz -C /target     # extract to a specific directory
tar -tzvf in.tar.gz                # lisT contents without extracting  ⭐
tar -czf out.tar.gz --exclude='*.log' dir/
tar -cJvf out.tar.xz dir/          # xz — smaller, slower
tar --strip-components=1 -xzf in.tar.gz   # drop the top-level directory

gzip file / gunzip file.gz
zip -r out.zip dir/ / unzip in.zip
unzip -l in.zip                    # list without extracting
```

> 💡 Mnemonic: **c**reate, e**x**tract, **t**est-list — plus **f** for file, always last.

---

## Environment & Shell

```bash
env                                # all environment variables
printenv PATH
echo $PATH
export KEY=value                   # set for this shell and its children
unset KEY
set -o vi                          # vi keybindings at the prompt

history                            # command history
history | grep docker
!!                                 # repeat last command
sudo !!                            # repeat last command with sudo  ⭐
!$                                 # last argument of the previous command
Ctrl-R                             # reverse search through history
```

| File | Loaded when |
|------|-------------|
| `/etc/profile`, `/etc/profile.d/*` | Any login shell, all users |
| `~/.bash_profile` / `~/.profile` | Login shells (SSH) |
| `~/.bashrc` | Interactive non-login shells (new terminal tabs) |
| `~/.bash_logout` | Logout |
| `/etc/environment` | System-wide vars — **not** a script, `KEY=value` only |

```bash
# Useful aliases for ~/.bashrc
alias ll='ls -lah'
alias ..='cd ..'
alias grep='grep --color=auto'
alias df='df -h'
alias ports='ss -tulnp'
alias serve='python3 -m http.server 8000'
```

### Redirection quick table

| Syntax | Effect |
|--------|--------|
| `cmd > f` | stdout to file (overwrite) |
| `cmd >> f` | stdout to file (append) |
| `cmd 2> f` | stderr to file |
| `cmd > f 2>&1` | both to the same file |
| `cmd &> f` | both (bash shorthand) |
| `cmd 2>/dev/null` | discard errors |
| `cmd \| tee f` | to screen **and** file |
| `cmd \| tee -a f` | ...appending |
| `cmd1 \| cmd2` | pipe stdout of cmd1 into cmd2 |
| `cmd1 \|& cmd2` | pipe stdout **and** stderr |
| `<(cmd)` | process substitution — treat output as a file |

---

## One-Minute Server Triage

The order matters: cheapest checks first, and each one narrows the search.

```bash
uptime                                          # 1. load average vs nproc
free -h                                         # 2. memory + swap pressure
df -h && df -i                                  # 3. disk space AND inodes
dmesg -T | tail -30                             # 4. OOM kills, disk errors, kernel complaints
systemctl list-units --state=failed             # 5. what services are down
journalctl -p err --since "1 hour ago" -n 50    # 6. recent errors, all units
ps aux --sort=-%cpu | head -10                  # 7. top CPU
ps aux --sort=-%mem | head -10                  # 8. top memory
ss -s && ss -tlnp                               # 9. sockets and listeners
iostat -xz 1 3                                  # 10. disk latency (%util, await)
who && last -n 10                               # 11. who's been on this box
```

**Copy-paste one-liner** — save it as `~/bin/triage`:

```bash
#!/usr/bin/env bash
set -uo pipefail
echo "=== UPTIME/LOAD ($(nproc) CPUs) ==="; uptime
echo "=== MEMORY ===";                        free -h
echo "=== DISK ===";                          df -h --output=pcent,size,avail,target -x tmpfs -x devtmpfs
echo "=== INODES ===";                        df -i --output=ipcent,target -x tmpfs -x devtmpfs
echo "=== FAILED UNITS ===";                  systemctl list-units --state=failed --no-pager --no-legend
echo "=== TOP CPU ===";                       ps -eo pcpu,pmem,pid,user,comm --sort=-pcpu | head -6
echo "=== TOP MEM ===";                       ps -eo pmem,pcpu,pid,user,comm --sort=-pmem | head -6
echo "=== LISTENERS ===";                     ss -tlnp 2>/dev/null | head -15
echo "=== RECENT KERNEL ===";                 dmesg -T 2>/dev/null | tail -15
```

**Interpreting what you find:**

| Observation | Likely meaning |
|-------------|----------------|
| Load average >> `nproc`, low CPU% | Processes blocked on **I/O**, not CPU — check `iostat`, `vmstat` `b` column |
| `available` memory low, swap active | Memory pressure — expect OOM kills soon (`dmesg \| grep -i oom`) |
| `df -h` fine, `df -i` at 100% | Inode exhaustion — millions of tiny files, often in a cache or mail dir |
| Disk full but nothing large found | Deleted-but-open file — `lsof +L1`, restart the holder |
| High `%util` + high `await` in `iostat` | Disk is the bottleneck |
| Many `TIME_WAIT` sockets | Connection churn — enable keep-alive/pooling |

---

<div align="center">

[← Module 01 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
