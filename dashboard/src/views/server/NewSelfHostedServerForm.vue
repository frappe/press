<template>
	<div>
		<h2 class="text-lg font-semibold space-y-1">Enter the Server Details</h2>
		<div class="mt-6 flex flex-col gap-4">
			<p class="text-base text-black-900">Public IP of the Server </p>
			<Input class="z-10 w-full rounded-r-none" :value="publicIP" @change="$emit('update:publicIP', $event)" type="text" />
			<p class="text-base text-black-900"> Private IP of the Server</p>
			<Input class="z-10 w-full rounded-r-none" :value="privateIP" @change="$emit('update:privateIP', $event)" type="text"  />
			<ErrorMessage class="mt-3" :message="error"/>
		</div>

	</div>
</template>
<script>
export default {
	name: 'SelfHostedServerForm',
	props: ["privateIP", "publicIP","error"],
	emits: ['update:publicIP', 'update:privateIP'],
};
</script>
