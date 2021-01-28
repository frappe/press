<template>
	<component :is="promptComponent" :message="promptMessage" />
</template>

<script>
export default {
	name: 'UserPrompts',
	components: {
		UpdateBillingDetails: () => import('@/components/UpdateBillingDetails')
	},
	resources: {
		prompts: {
			method: 'press.api.account.user_prompts',
			auto: true,
			validate() {
				if (document.cookie.includes('user_id=Guest')) {
					return 'Not logged in';
				}
			}
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
