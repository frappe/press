"""Report which press modules import cleanly, and which fail and why.

Run it from the bench root, then read the file named by `PROBE_OUTPUT`:

    bench --site press.localhost console < press/utils/probe_module_imports.py

Run it against several environments and diff the results: a module that
imports on one and not another is a framework compatibility finding, while
one that fails on both is pre-existing. It walks with a site connected as
Administrator, because an unbound site reports breakage that is not real.
"""

import importlib
import os
import pkgutil

import frappe
import frappe.utils

OUTPUT = os.environ.get("PROBE_OUTPUT", "/tmp/opencode/probe_result.txt")

# Skipped because they are expected to be unavailable in a given env rather than
# broken, and their absence is a supported state.
SKIP_SUBSTRINGS = (".mcp.", ".tests.")
SKIP_SUFFIXES = (".mcp",)


def probe() -> None:
	"""Write the report to `PROBE_OUTPUT`."""
	# Frappe writes log files under <bench>/<site>/logs, and resolves the bench
	# dir by walking up from cwd. Create the log dir for both, so the walk can
	# land anywhere.
	sites_path = os.environ.get("PROBE_SITES_PATH") or None
	for root in (frappe.utils.get_bench_path(), os.getcwd()):
		if root:
			os.makedirs(os.path.join(root, "press.localhost", "logs"), exist_ok=True)
	os.makedirs("press.localhost/logs", exist_ok=True)

	frappe.init(site="press.localhost", sites_path=sites_path)
	frappe.connect()
	frappe.set_user("Administrator")

	import press

	failures = []
	imported = 0
	modules = [
		m.name
		for m in pkgutil.walk_packages(press.__path__, "press.")
		if not any(s in m.name for s in SKIP_SUBSTRINGS)
		and not m.name.endswith(SKIP_SUFFIXES)
		and "test_" not in m.name
	]

	for name in modules:
		try:
			importlib.import_module(name)
			imported += 1
		except Exception as e:
			failures.append((name, type(e).__name__, str(e).split("\n")[0][:100]))

	frappe.db.rollback()

	lines = [f"RESULT imported={imported} failed={len(failures)} total={len(modules)}"]
	lines += [f"FAIL {n} | {t} | {m}" for n, t, m in sorted(failures)]
	os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
	with open(OUTPUT, "w") as f:
		f.write("\n".join(lines) + "\n")
	print("PROBE wrote", OUTPUT)


if __name__ == "__main__":
	# Importing the module is enough; the report runs when probe() is invoked.
	pass
