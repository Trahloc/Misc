#!/bin/bash

# Refined script to gather relevant IRQ and device information for Fedora 41

echo "-------------------- Focused IRQ Information --------------------"
echo " "
echo "--- /proc/interrupts (Filtered for NVMe and USB/Logitech) ---"
grep -iE "nvme|usb|logitech" /proc/interrupts
echo " "

echo "-------------------- PCI Device Information (NVMe and USB Controllers) --------------------"
echo " "
echo "--- lspci -v (Filtered for NVMe and USB Controllers) ---"
lspci -v | grep -iE "nvme|usb controller" -A 20
echo " "

echo "-------------------- USB Device Information (Logitech) --------------------"
echo " "
echo "--- lsusb -v (Filtered for Logitech) ---"
lsusb -v | grep -i "Logitech" -A 10
echo " "

echo "-------------------- NVMe Device Information --------------------"
echo " "
echo "--- nvme list --- (if nvme-cli is installed)"
if command -v nvme >/dev/null 2>&1; then
  nvme list
else
  echo "nvme-cli is not installed. Install it for NVMe device info (sudo dnf install nvme-cli)"
fi
echo " "

echo "-------------------- End of Information --------------------"
echo " "
echo "Please run this refined script and provide the output."
echo "You can save the output to a file:  ./refined_script_name.sh > refined_system_info.txt"
echo " "
