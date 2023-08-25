<template>
	<div class="flex flex-row flex-wrap w-full h-fit">
		<div
			v-for="sub in data.subscriptions"
			class="flex flex-col items-center m-2 p-4 w-2/7 rounded cursor-pointer transition-all"
			v-on:click="selectSubscription(sub)"
		>
			<img
				:src="sub.image"
				alt="Logo"
				class="rounded h-[68px] hover:scale-105 transition-all"
			/>
			<span class="text-sm mt-3 font-semibold">{{ sub.title }}</span>
		</div>
	</div>
</template>

<script>
export default {
	name: 'Apps',
	emits: ['update:selectedSubscription', 'update:step'],
	props: {
		data: {
			default: []
		},
		step: {
			default: 1
		},
		selectedSubscription: {
			default: ''
		}
	},
	methods: {
		selectSubscription(sub) {
			this.$emit('update:selectedSubscription', sub);
			this.$emit('update:step', 2);
		}
	}
};
</script>
