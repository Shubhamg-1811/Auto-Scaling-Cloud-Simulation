import time
import requests
import subprocess
import re # <-- 1. IMPORT the regular expression module

# --- Configuration ---
LB_URL = "http://127.0.0.1:8000"
MIN_VMS = 2
MAX_VMS = 5
COOLDOWN_PERIOD = 30  # seconds
SCALE_UP_THRESHOLD = 20   # requests per VM in 10s
SCALE_DOWN_THRESHOLD = 5  # requests per VM in 10s

# --- State ---
active_vms = {}  # { "vm_name": "http://ip:port" }
last_scale_time = 0
# 2. UPDATE the initial VM names
initial_vms = ["web_vm1", "web_vm2"] 

# --- Helper Functions ---
def get_vm_ip(vm_name):
    """Tries to get the IP address of a VM via virsh for up to 60 seconds."""
    print(f"[Scheduler] Attempting to get IP for {vm_name}...")
    for _ in range(360):
        try:
            result = subprocess.run(
                ["virsh", "domifaddr", vm_name, "--source", "agent"],
                capture_output=True, text=True, check=True
            )
            for line in result.stdout.splitlines():
                if "ipv4" in line and "lo" not in line:
                    ip = line.split()[3].split("/")[0]
                    print(f"[Scheduler] Found IP for {vm_name}: {ip}")
                    return ip
        except subprocess.CalledProcessError:
            pass
        time.sleep(0.5)
    print(f"[Scheduler] ERROR: Could not get IP for {vm_name} after 180 seconds.")
    return None

def update_lb():
    """Pushes the current list of active server IPs to the load balancer."""
    server_list = list(active_vms.values())
    try:
        requests.post(f"{LB_URL}/update_servers", json={"servers": server_list}, timeout=5)
        print(f"[Scheduler] Load Balancer updated with servers: {server_list}")
    except requests.exceptions.RequestException as e:
        print(f"[Scheduler] ERROR: Could not update load balancer: {e}")

# --- Scaling Logic ---
def scale_up():
    """Creates a new VM, gets its IP, and updates the LB."""
    global last_scale_time
    if len(active_vms) >= MAX_VMS:
        print("[Scheduler] MAX_VMS reached. Cannot scale up.")
        return
        
    next_vm_idx = 1
    # 3. CHANGE name generation logic to remove the underscore
    while f"web_vm{next_vm_idx}" in active_vms:
        next_vm_idx += 1
    vm_name = f"web_vm{next_vm_idx}"
    
    print(f"[Scheduler] SCALING UP: Creating {vm_name}...")
    
    subprocess.run(["python3", "create_vm_virt.py", vm_name])
    ip = get_vm_ip(vm_name)
    
    if ip:
        active_vms[vm_name] = f"http://{ip}:5000"
        update_lb()
        last_scale_time = time.time()
        print(f"[Scheduler] SCALE UP complete for {vm_name} at {ip}.")
    else:
        print(f"[Scheduler] Cleaning up failed VM creation for {vm_name}")
        subprocess.run(["python3", "delete_vm_virt.py", vm_name])

def scale_down():
    """Removes the most recently added VM and updates the LB."""
    global last_scale_time
    if len(active_vms) <= MIN_VMS:
        print("[Scheduler] MIN_VMS reached. Cannot scale down.")
        return

    # 4. CHANGE sorting logic to use regular expressions
    vm_to_delete = sorted(
        active_vms.keys(),
        key=lambda name: int(re.search(r'(\d+)$', name).group(1))
    )[-1]
    
    ip = active_vms.pop(vm_to_delete)

    print(f"[Scheduler] SCALING DOWN: Deleting {vm_to_delete} ({ip})...")
    
    subprocess.run(["python3", "delete_vm_virt.py", vm_to_delete])
    update_lb()
    last_scale_time = time.time()
    print(f"[Scheduler] SCALE DOWN complete for {vm_to_delete}.")

# --- Main Loop ---
if __name__ == "__main__":
    print("[Scheduler] Initializing...")
    for vm_name in initial_vms:
        ip = get_vm_ip(vm_name)
        if ip:
            active_vms[vm_name] = f"http://{ip}:5000"
        else:
            print(f"[Scheduler] FATAL: Could not get IP for initial VM {vm_name}. Exiting.")
            exit(1)
            
    update_lb()
    last_scale_time = time.time()
    
    print("[Scheduler] Starting monitoring loop...")
    while True:
        time.sleep(10)
        
        try:
            resp = requests.get(f"{LB_URL}/metrics", timeout=5)
            request_count = resp.json().get("request_count_10s", 0)
        except requests.exceptions.RequestException:
            print("[Scheduler] WARN: Could not get metrics from Load Balancer.")
            continue
            
        num_vms = len(active_vms)
        if num_vms == 0:
            print("[Scheduler] WARN: No active VMs!")
            continue

        print(f"[Scheduler] STATUS: {num_vms} VMs | Request count (10s): {request_count}")

        reqs_per_vm = request_count / num_vms
        now = time.time()

        if now - last_scale_time > COOLDOWN_PERIOD:
            if reqs_per_vm > SCALE_UP_THRESHOLD:
                scale_up()
            elif reqs_per_vm < SCALE_DOWN_THRESHOLD:
                scale_down()
        else:
            print(f"[Scheduler] In cooldown period. No scaling actions will be taken.")
