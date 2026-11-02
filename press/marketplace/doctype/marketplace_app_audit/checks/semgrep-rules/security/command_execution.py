import os
import subprocess

import frappe


def os_system_example(user_input):
	# ruleid: frappe-os-command-exec
	os.system(f"echo {user_input}")


def os_popen_example(user_input):
	# ruleid: frappe-os-command-exec
	os.popen(user_input)


def os_execl_example(user_input):
	# ruleid: frappe-os-command-exec
	os.execl(user_input)


def os_execle_example(user_input):
	# ruleid: frappe-os-command-exec
	os.execle(user_input)


def os_execv_example(user_input):
	# ruleid: frappe-os-command-exec
	os.execv(user_input)


def os_execve_example(user_input):
	# ruleid: frappe-os-command-exec
	os.execve(user_input)


def os_execvp_example(user_input):
	# ruleid: frappe-os-command-exec
	os.execvp(user_input)


def os_execvpe_example(user_input):
	# ruleid: frappe-os-command-exec
	os.execvpe(user_input)


def subprocess_shell_true(user_input):
	# ruleid: frappe-subprocess-shell-true
	subprocess.run(f"ls {user_input}", shell=True)


def subprocess_popen_shell_true(user_input):
	# ruleid: frappe-subprocess-shell-true
	subprocess.Popen(user_input, shell=True)


def subprocess_run_list(user_input):
	# ruleid: frappe-subprocess-exec
	subprocess.run(["ls", user_input])


def subprocess_check_output(user_input):
	# ruleid: frappe-subprocess-exec
	subprocess.check_output(["cat", user_input])


def frappe_execute_in_shell_example(cmd):
	# ruleid: frappe-execute-in-shell
	frappe.utils.execute_in_shell(cmd)


def ok_os_path():
	# ok: frappe-os-command-exec
	return os.path.join("/tmp", "foo")


def ok_os_getenv():
	# ok: frappe-os-command-exec
	return os.getenv("FRAPPE_SITE")
