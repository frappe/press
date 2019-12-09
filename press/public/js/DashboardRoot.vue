<template>
	<div>
		<div>
			<router-link to="/sites">Sites</router-link>
			<router-link to="/site">Site</router-link>
			<router-link to="/sites/new">New Site</router-link>
			<router-link to="/payments">Payments</router-link>
		</div>
		<router-view></router-view>
	</div>
</template>

<script>

export default {
	name: "DashboardRoot"
};
</script>
