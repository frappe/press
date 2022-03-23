<template>
	<div class="h-full pt-4 sm:pt-16">
		<div>
			<div class="flex">
				<FrappeCloudLogo
					class="mx-auto h-4 w-auto"
					v-on:dblclick="redirect"
				/>
			</div>
			<div
				class="sm:w-0112 mx-auto bg-white px-4 py-8 sm:mt-6 sm:w-96 sm:rounded-lg sm:px-10 sm:shadow-xl"
			>
				<div class="mb-6 text-center">
					<span class="text-lg">{{ title }}</span>
				</div>
				<slot></slot>
			</div>
		</div>
	</div>
</template>

<script>
import FrappeCloudLogo from '@/components/FrappeCloudLogo.vue';
export default {
	name: 'LoginBox',
	props: ['title'],
	components: {
		FrappeCloudLogo
	},
	methods: {
		redirect() {
			this.$router.push('/f-login');
			this.$router.go();
		}
	}
};
</script>
