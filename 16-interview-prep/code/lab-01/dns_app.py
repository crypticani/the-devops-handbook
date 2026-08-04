import urllib.request, time, sys
while True:
    try:
        resp = urllib.request.urlopen("http://datastore:6379/ping", timeout=3)
        print(f"Connected: {resp.read().decode()}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
    time.sleep(5)
