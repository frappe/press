<template>
	<div>
		<div>
			<label>Domain</label>
			<input v-model="site.name" placeholder="yoursite" />
			<span>.frappe.cloud</span>
		</div>
		<div>
			<button v-on:click="create()">Create Site</button>
		</div>
	</div>
</template>

<script>
export default {
	name: "SiteNewForm",
	data() {
		return {
			site: {
				name: null,
			},
		};
	},
	methods: {
		create: async function() {
			let data = {site: this.site};
			data["csrf_token"] = frappe.csrf_token;
			let response = await fetch("/api/method/press.api.site.new", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(data)
			});
			if (response.ok) {
				const site = await response.json();
				console.log("Nothing Went Wrong");
				console.log(site);
			} else {
				console.log("Something Went Wrong");
			}
		}
	}
};
</script>
