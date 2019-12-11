<template>
	<div>
		<div>
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
			site: {
				name: null,
				status: null,
			}
		};
	},
	mounted() {
		this.get();
	},
	methods: {
		get: async function() {
			let response = await fetch(`/api/method/press.api.site.get?name=${this.$route.params.name}`);
			if (response.ok) {
				const site = await response.json();
				console.log("Nothing Went Wrong");
				console.log(site);
				this.site = site.message;
			} else {
				console.log("Something Went Wrong");
			}
		}
	}
};
</script>
