<template>
	<component :is="promptComponent" :message="promptMessage" v-model="show" />
</template>

<script>
import { defineAsyncComponent } from 'vue';

export default {
	name: 'UserPrompts',
	components: {
		UpdateBillingDetails: defineAsyncComponent(() =>
			import('../../../src2/components/UpdateBillingDetails.vue')
		)
	},
	resources: {
		prompts() {
			return {
				url: 'press.api.account.user_prompts',
				auto: true,
				validate() {
					if (document.cookie.includes('user_id=Guest')) {
						return 'Not logged in';
					}
				}
			};
		}
	},
	data() {
		return {
			show: true
		};
	},
	computed: {
		promptComponent() {
			let data = this.$resources.prompts.data;
			if (data) {
				return data[0];
			}
			return null;
		},
		promptMessage() {
			let data = this.$resources.prompts.data;
			if (data) {
				return data[1];
			}
			return null;
		}
	}
};
</script>
