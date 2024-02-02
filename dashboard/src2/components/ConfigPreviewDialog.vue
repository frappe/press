<template>
	<Dialog
		:options="{
			title: 'Config Preview'
		}"
		v-model="showDialog"
	>
		<template #body-content>
			<div
				class="hidden h-fit max-w-full flex-1 overflow-x-scroll whitespace-pre-line rounded bg-gray-100 p-4 font-mono text-base md:block"
				v-html="configPreview"
			></div>
		</template>
	</Dialog>
</template>

<script>
export default {
	props: ['configs'],
	data() {
		return {
			showDialog: true
		};
	},
	computed: {
		configPreview() {
			let obj = {};
			for (let d of this.configs) {
				let value = d.value;
				if (['Boolean', 'Number'].includes(d.type)) {
					value = Number(d.value);
				} else if (d.type === 'JSON') {
					try {
						value = JSON.parse(d.value);
					} catch (error) {
						value = {};
					}
				}
				obj[d.key] = value;
			}
			return JSON.stringify(obj, null, '&nbsp; ');
		}
	}
};
</script>
