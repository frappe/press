# Setup the ansible CLI does for itself, needed when Press drives Ansible as a library
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from ansible.plugins.loader import init_plugin_loader
from ansible.utils.collection_loader import AnsibleCollectionConfig

# Without the collection loader no module can load ansible.builtin
if not AnsibleCollectionConfig.collection_finder:
	init_plugin_loader()


def use_callback(tqm: TaskQueueManager, callback: CallbackBase):
	# load_callbacks() loads stdout callbacks by name only, and skips loading once this list is set
	callback._init_callback_methods()
	tqm._callback_plugins = [callback]
