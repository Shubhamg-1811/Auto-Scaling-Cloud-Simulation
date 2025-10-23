import subprocess, sys, time

if len(sys.argv) < 2:
    print("Usage: python3 create_vm_virt.py <new_vm_name>")
    sys.exit(1)

template_name = "ubuntu20.04-3_webTemplate"
new_vm_name = sys.argv[1]

print(f"[Script] Cloning {template_name} to {new_vm_name}...")
subprocess.run(["virt-clone", "--original", template_name, "--name", new_vm_name, "--auto-clone"])
print(f"[Script] Starting VM: {new_vm_name}...")
subprocess.run(["virsh", "start", new_vm_name])
time.sleep(10)
print(f"[Script] Created and started VM: {new_vm_name}")
