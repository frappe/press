"""Tests for press.runner - focused on logic that can break silently."""

import unittest

from press.runner import Ansible, AnsibleAdHoc


class TestParseTasksOutput(unittest.TestCase):
	"""Test _parse_tasks which parses `ansible-playbook --list-tasks` output.

	This is a pure-logic parser that could break from ansible version changes.
	"""

	def test_parses_simple_playbook(self):
		output = """
playbook: /path/to/database.yml

  play #1 (all): Setup Database Server	TAGS: []
    tasks:
      mariadb : Install MariaDB	TAGS: []
      mariadb : Configure MariaDB	TAGS: []
"""
		result = Ansible._parse_tasks(None, output)
		self.assertEqual(result["name"], "Setup Database Server")
		self.assertEqual(len(result["tasks"]), 2)
		self.assertEqual(result["tasks"][0], {"role": "mariadb", "task": "Install MariaDB"})
		self.assertEqual(result["tasks"][1], {"role": "mariadb", "task": "Configure MariaDB"})

	def test_parses_multiple_roles(self):
		output = """
playbook: /path/to/server.yml

  play #1 (all): Setup Server	TAGS: []
    tasks:
      essentials : Install Essential Packages	TAGS: []
      user : Create frappe user	TAGS: []
      node : Install Node.js	TAGS: []
"""
		result = Ansible._parse_tasks(None, output)
		self.assertEqual(result["name"], "Setup Server")
		self.assertEqual(len(result["tasks"]), 3)
		roles = [t["role"] for t in result["tasks"]]
		self.assertEqual(roles, ["essentials", "user", "node"])

	def test_handles_empty_output(self):
		result = Ansible._parse_tasks(None, "")
		self.assertIsNone(result["name"])
		self.assertEqual(result["tasks"], [])

	def test_skips_lines_without_role_separator(self):
		output = """
playbook: /path/to/test.yml

  play #1 (all): Test Play	TAGS: []
    tasks:
      some_role : Valid Task	TAGS: []
      This line has no role separator
"""
		result = Ansible._parse_tasks(None, output)
		self.assertEqual(len(result["tasks"]), 1)

	def test_handles_tagged_tasks(self):
		output = """
playbook: /path/to/test.yml

  play #1 (all): Tagged Play	TAGS: []
    tasks:
      nginx : Configure Nginx	TAGS: [setup]
      nginx : Restart Nginx	TAGS: [setup, restart]
"""
		result = Ansible._parse_tasks(None, output)
		self.assertEqual(len(result["tasks"]), 2)
		self.assertEqual(result["tasks"][0]["task"], "Configure Nginx")
		self.assertEqual(result["tasks"][1]["task"], "Restart Nginx")


class TestInventoryFormat(unittest.TestCase):
	"""Test that inventory strings are formatted correctly for ansible-runner."""

	def test_adhoc_inventory_single_host(self):
		adhoc = AnsibleAdHoc.__new__(AnsibleAdHoc)
		adhoc.hosts = ["10.0.0.1"]
		adhoc.port = 22
		result = adhoc._create_inventory()
		self.assertIn("10.0.0.1", result)

	def test_adhoc_inventory_custom_port(self):
		adhoc = AnsibleAdHoc.__new__(AnsibleAdHoc)
		adhoc.hosts = ["10.0.0.1"]
		adhoc.port = 2222
		result = adhoc._create_inventory()
		self.assertIn("ansible_port=2222", result)

	def test_adhoc_inventory_multiple_hosts(self):
		adhoc = AnsibleAdHoc.__new__(AnsibleAdHoc)
		adhoc.hosts = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
		adhoc.port = 22
		result = adhoc._create_inventory()
		for host in adhoc.hosts:
			self.assertIn(host, result)


class TestGenerateCmdline(unittest.TestCase):
	"""Test command line generation, especially bastion host proxy."""

	def test_basic_cmdline(self):
		ansible = Ansible.__new__(Ansible)
		ansible.user = "root"
		ansible.server = type("Server", (), {"bastion_host": None})()
		result = ansible.generate_cmdline()
		self.assertEqual(result, "--user=root")

	def test_custom_user(self):
		ansible = Ansible.__new__(Ansible)
		ansible.user = "frappe"
		ansible.server = type("Server", (), {"bastion_host": None})()
		result = ansible.generate_cmdline()
		self.assertEqual(result, "--user=frappe")

	def test_bastion_host_adds_proxy_command(self):
		bastion = type("Bastion", (), {"ssh_user": "admin", "ip": "10.0.0.99", "ssh_port": 22})()
		server = type("Server", (), {"bastion_host": bastion})()
		ansible = Ansible.__new__(Ansible)
		ansible.user = "root"
		ansible.server = server
		result = ansible.generate_cmdline()
		self.assertIn("ProxyCommand", result)
		self.assertIn("10.0.0.99", result)
		self.assertIn("admin", result)


class TestAnsibleRunnerOnOkAsyncHandling(unittest.TestCase):
	"""Test that async job_ids are detected and saved from runner_on_ok events."""

	def test_detects_async_job_id(self):
		"""runner_on_ok should call _save_async_job_id when event has ansible_job_id."""
		ansible = Ansible.__new__(Ansible)
		ansible.tasks = {"copy": {"Copy files": "TASK-001"}}
		ansible.task_list = ["TASK-001"]
		ansible.play = "PLAY-001"

		saved = {}

		def mock_save(event, job_id):
			saved["event"] = event
			saved["job_id"] = job_id

		def mock_update_task(status, result=None, task=None):
			pass

		def mock_process(event):
			pass

		ansible._save_async_job_id = mock_save
		ansible.update_task = mock_update_task
		ansible.process_task_success = mock_process

		event = {
			"role": "copy",
			"task": "Copy files",
			"res": {"ansible_job_id": "JOB-12345", "started": 1},
		}
		ansible.runner_on_ok(event)

		self.assertEqual(saved["job_id"], "JOB-12345")

	def test_skips_non_async_events(self):
		"""runner_on_ok should not call _save_async_job_id for regular tasks."""
		ansible = Ansible.__new__(Ansible)

		saved = {}

		def mock_save(event, job_id):
			saved["called"] = True

		def mock_update_task(status, result=None, task=None):
			pass

		def mock_process(event):
			pass

		ansible._save_async_job_id = mock_save
		ansible.update_task = mock_update_task
		ansible.process_task_success = mock_process

		event = {
			"role": "mariadb",
			"task": "Install MariaDB",
			"res": {"changed": True, "rc": 0},
		}
		ansible.runner_on_ok(event)

		self.assertNotIn("called", saved)


class TestEventHandlerDispatch(unittest.TestCase):
	"""Test that event_handler correctly routes events to methods."""

	def test_routes_known_events(self):
		ansible = Ansible.__new__(Ansible)
		called = {}

		ansible.runner_on_ok = lambda data: called.update({"runner_on_ok": data})
		ansible.runner_on_failed = lambda data: called.update({"runner_on_failed": data})

		ansible.event_handler({"event": "runner_on_ok", "event_data": {"host": "test"}})
		self.assertEqual(called["runner_on_ok"], {"host": "test"})

	def test_ignores_unknown_events(self):
		ansible = Ansible.__new__(Ansible)
		# Should not raise
		ansible.event_handler({"event": "some_unknown_event", "event_data": {}})


class TestAdhocDurationParsing(unittest.TestCase):
	"""Test duration string parsing in AnsibleAdHoc."""

	def test_parses_normal_duration(self):
		adhoc = AnsibleAdHoc.__new__(AnsibleAdHoc)
		self.assertEqual(adhoc._parse_duration("0:00:01.234567"), 1)

	def test_parses_minutes(self):
		adhoc = AnsibleAdHoc.__new__(AnsibleAdHoc)
		self.assertEqual(adhoc._parse_duration("0:02:30.000000"), 150)

	def test_parses_hours(self):
		adhoc = AnsibleAdHoc.__new__(AnsibleAdHoc)
		self.assertEqual(adhoc._parse_duration("1:00:00.000000"), 3600)

	def test_handles_none(self):
		adhoc = AnsibleAdHoc.__new__(AnsibleAdHoc)
		self.assertEqual(adhoc._parse_duration(None), 0)

	def test_handles_invalid(self):
		adhoc = AnsibleAdHoc.__new__(AnsibleAdHoc)
		self.assertEqual(adhoc._parse_duration("invalid"), 0)
