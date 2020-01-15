<template>
	<div>
		<div id="header-site" class="py-2 //border-b //border-gray-400">
			<div class="flex flex-row">
			<i data-feather="server" class="mr-2 h-5 w-5 self-center text-gray-700"></i>
			<span class="self-center font-bold">{{ site.name }}</span>
			</div>
		</div>
		<div id="stats-for-site" class="py-2 //border-b //border-gray-400 flex justify-between">
			<div class="flex flex-row text-xs">
				<div class="mr-5">
				Backups: <b>Enabled</b>
				</div>
				<div class="mr-5">
				Monitoring: <b>Enabled</b>
				</div>
				<div class="mr-5">
				Deploy: <b>Enabled</b>
				</div>
			</div>
			<div class="text-xs text-gray-500">
				Last Updated: 20 mins ago
			</div>
		</div>
		<div id="stats-for-site" class="flex flex-row flex-wrap text-xs mt-5">
			<div class="w-1/6 flex flex-col">
				<span class="py-1 cursor-pointer text-indigo-800 font-semibold">Graphs</span>
				<span class="py-1 cursor-pointer text-gray-600 hover:text-gray-900">Admin Area</span>
				<span class="py-1 cursor-pointer text-gray-600 hover:text-gray-900">History</span>
				<span class="py-1 cursor-pointer text-gray-600 hover:text-gray-900">Backups</span>
				<span class="py-1 cursor-pointer text-gray-600 hover:text-gray-900">Destroy</span>
			</div>
			<div class="w-5/6 flex flex-wrap">
				<div class="p-2 w-1/2">
					<div class="h-48 bg-gray-200">
					</div>
				</div>
				<div class="p-3 w-1/2">
					<div class="h-48 bg-gray-200">
					</div>
				</div>
				<div class="p-3 w-1/2">
					<div class="h-48 bg-gray-200">
					</div>
				</div>
				<div class="p-3 w-1/2">
					<div class="h-48 bg-gray-200">
					</div>
				</div>
				<div class="p-3 w-1/2">
					<div class="h-48 bg-gray-200">
					</div>
				</div>
				<div class="p-3 w-1/2">
					<div class="h-48 bg-gray-200">
					</div>
				</div>
			</div>
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
