<template>
	<div>
		<div>
			<div>Sites</div>
			<div>{{ sites.length }}</div>
		</div>
		<div v-for="site in sites" v-bind:key="site.name">
			<router-link :to="{ name: 'site-detail', params: { name: site.name }}">
				<div>{{ site.name }}</div>
				<div>{{ site.status }}</div>
			</router-link>
		</div>
	</div>
</template>

<script>
export default {
	name: "SiteList",
	data() {
		return {
			sites: []
		};
	},
	mounted() {
		this.get();
	},
	methods: {
		get: async function() {
			let response = await fetch("/api/method/press.api.site.all");
			if (response.ok) {
				const sites = await response.json();
				console.log("Nothing Went Wrong");
				console.log(sites);
				this.sites = sites.message;
			} else {
				console.log("Something Went Wrong");
			}
		}
	}
};
</script>

