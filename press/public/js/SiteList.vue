<template>
	<div>
		<div>
			<div>Sites</div>
			<div>{{ sites.length }}</div>
		</div>
		<div v-for="site in sites" v-bind:key="site.name">
			<div>{{ site.name }}</div>
			<div>{{ site.status }}</div>
		</div>
	</div>
</template>

<script>
export default {
	name: "SiteList",
	data() {
		return {
			sites: [
				{
					name: "erpnext.com",
					status: "Running"
				},
				{
					name: "erpnext.org",
					status: "Archived"
				}
			]
		};
	}
};
</script>
