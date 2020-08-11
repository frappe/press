<template>
	<component :is="$resources.prompts.data" />
</template>

<script>
export default {
	name: 'UserPrompts',
	components: {
		UpdateGSTIN: () => import('@/components/UpdateGSTIN'),
		UpdateBillingAddress: () => import('@/components/UpdateBillingAddress')
	},
	resources: {
		prompts: {
			method: 'press.api.account.user_prompts',
			auto: true
		}
	}
};
</script>
