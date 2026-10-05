"""Runner skill cek-baterai."""
import sys
sys.path.insert(0, ".")
from actions.termux import battery

r = battery()
if not r["ok"]:
    print("gagal baca baterai:", r.get("error"))
    sys.exit(1)
d = r["data"]
pct = d.get("percentage")
status = d.get("status")
temp = d.get("temperature")
print("Baterai: %s%% | status: %s | suhu: %sC" % (pct, status, temp))
