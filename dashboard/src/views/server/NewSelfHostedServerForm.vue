<template>
	<div>
		<h2 class="text-lg font-semibold space-y-1">Enter the Server Details</h2>
		<div class="mt-6 flex flex-col gap-4">
			<p class="text-base text-black-900">Public IP of the Server </p>
			<Input :value="public_ip" @change="$emit('update:public_ip', $event)" type="text" />
			<p class="text-base text-black-900"> Private IP of the Server</p>
			<Input :value="private_ip" @change="$emit('update:private_ip', $event)" type="text" />
			<p class="text-base text-black-900">SSH User of the Server</p>
			<Input placeholder="root" :value="ssh_user" @change="$emit('update:ssh_user', $event)" type="text" />
			<p class="text-base text-black-900">SSH Port of the Server</p>
			<Input placeholder="22" :value="ssh_port" @change="$emit('update:ssh_port', $event)" type="text" />
		</div>
	</div>
</template>
<script>
import Input from 'frappe-ui/src/components/Input.vue';
export default {
	name: 'SelfHostedServerForm',
	props: ["private_ip", "public_ip", "ssh_user", "ssh_port"],
	emits: ['update:public_ip', 'update:private_ip', 'update:ssh_port', 'update:ssh_user'],
	components: {
		Input
	}
};
</script>
