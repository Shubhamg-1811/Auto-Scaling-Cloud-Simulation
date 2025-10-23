import subprocess, sys, time

if len(sys.argv) < 2:
    print("Usage: python3 delete_vm_virt.py <vm_name>")
    sys.exit(1)

vm_name = sys.argv[1]

print(f"[Script] Shutting down VM: {vm_name}...")
subprocess.run(["virsh", "destroy", vm_name])
time.sleep(2)
print(f"[Script] Undefining VM and removing storage for: {vm_name}...")
subprocess.run(["virsh", "undefine", vm_name, "--remove-all-storage"])
print(f"[Script] Deleted VM: {vm_name}")
