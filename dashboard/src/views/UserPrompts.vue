<template>
	<component :is="promptComponent" :message="promptMessage" />
</template>

<script>
export default {
	name: 'UserPrompts',
	components: {
		UpdateBillingAddress: () => import('@/components/UpdateBillingAddress')
	},
	resources: {
		prompts: {
			method: 'press.api.account.user_prompts',
			auto: true
		}
	},
	computed: {
		promptComponent() {
			let data = this.$resources.prompts.data;
			if (data) {
				return data[0];
			}
		},
		promptMessage() {
			let data = this.$resources.prompts.data;
			if (data) {
				return data[1];
			}
		}
	}
};
</script>
