<template>
	<Dialog
		:options="{
			title: 'Config Environment Variable',
		}"
		v-model="showDialog"
	>
		<template #body-content>
			<pre
				class="overflow-x-scroll rounded bg-gray-100 p-4 text-base"
				v-html="configEnvironmentVariable"
			></pre>
		</template>
	</Dialog>
</template>

<script>
export default {
	props: ['environment_variables'],
	data() {
		return {
			showDialog: true
		};
	},
	computed: {
		configEnvironmentVariable() {
			let obj = {};
			for (let d of this.environment_variables) {
				obj[d.key] = d.value;
			}
			return JSON.stringify(obj, null, '&nbsp; ');
		}
	}
};
</script>
