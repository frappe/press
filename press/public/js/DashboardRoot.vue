<template>
	<div>
		<div>
			<router-link to="/">Sites</router-link>
			<router-link to="/site">Site</router-link>
		</div>
		<router-view></router-view>
	</div>
</template>

<script>

export default {
	name: "DashboardRoot"
};
</script>
