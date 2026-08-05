import time, sys, os
print("Starting application...")
print(f"Config file: {os.environ.get('CONFIG_PATH', '/etc/app/config.yml')}")
time.sleep(3)
# Simulate crash: missing required config file
config_path = os.environ.get('CONFIG_PATH', '/etc/app/config.yml')
if not os.path.exists(config_path):
    print(f"FATAL: Config file not found: {config_path}", file=sys.stderr)
    sys.exit(1)
print("Application running normally")
while True:
    time.sleep(10)
