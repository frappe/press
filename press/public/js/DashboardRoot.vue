<template>
	<div>
		<div>
			<router-link :to="{ name: 'site-list' }">Sites</router-link>
			<router-link :to="{ name: 'site-detail' }">Site</router-link>
			<router-link :to="{ name: 'site-new' }">New Site</router-link>
			<router-link :to="{ name: 'payment-list' }">Payments</router-link>
		</div>
		<router-view></router-view>
	</div>
</template>

<script>
export default {
	name: "DashboardRoot"
};
</script>
