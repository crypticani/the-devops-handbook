import time, os
log_dir = "/app/logs"
os.makedirs(log_dir, exist_ok=True)
counter = 0
print("Application started, writing logs...")
while True:
    with open(f"{log_dir}/app.log", "a") as f:
        f.write(f"Log entry {counter}: " + "x" * 10000 + "\n")
    counter += 1
    if counter % 100 == 0:
        size = os.path.getsize(f"{log_dir}/app.log")
        print(f"Log file size: {size / 1024 / 1024:.1f} MB")
    time.sleep(0.01)
