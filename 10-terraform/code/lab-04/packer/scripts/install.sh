#!/bin/sh
#
# Runs INSIDE the image at build time. Everything slow, shared, and identical across the
# fleet belongs here — not in user_data, and not in the application's Dockerfile.
#
# Note the shell: this runs in the image being built, which may not have bash.

set -eux

apt-get update
apt-get install -y --no-install-recommends curl ca-certificates procps
rm -rf /var/lib/apt/lists/* # ⭐ or the package index ships in every instance forever

# A monitoring agent, standing in for node_exporter / the CloudWatch agent / your APM.
cat >/usr/local/bin/metrics-agent <<'EOF'
#!/bin/sh
echo "metrics-agent 1.4.0"
EOF
chmod 0755 /usr/local/bin/metrics-agent

# The entrypoint every service built on this base inherits.
cat >/usr/local/bin/app-entrypoint <<'EOF'
#!/bin/sh
echo "app-base ready: $(metrics-agent)"
exec "$@"
EOF
chmod 0755 /usr/local/bin/app-entrypoint

# Non-root by default, so no service built on this base has to remember.
id -u appuser >/dev/null 2>&1 || useradd -r -u 1000 -m -d /app appuser
mkdir -p /app
chown appuser:appuser /app

python -m pip install --no-cache-dir --upgrade pip
