<template>
	<div>
		<div id="header-site" class="py-2 //border-b //border-gray-400">
		  <div class="flex flex-row">
			<span class="self-center text-lg font-bold">New Site</span>
		  </div>
		</div>
		<div class="mt-5">
			<div class="flex flex-wrap -mx-3 mb-8">
				<div class="w-64 px-3">
					<label class="block uppercase tracking-wide text-gray-700 text-xs font-bold mb-2" for="grid-password">
					Site Name
					</label>
					<input v-model="site.name" class="appearance-none block w-full bg-gray-200 text-gray-700 border border-gray-200 rounded py-3 px-4 mb-3 leading-tight focus:outline-none focus:bg-white focus:border-gray-500" id="grid-password" type="text" placeholder="frappe.erpnext.com">
				</div>
		  	</div>
		  	<div class="-mx-3 mb-8">
				<div class="px-3">
					<label class="block uppercase tracking-wide text-gray-700 text-xs font-bold mb-2" for="grid-password">
					Select Apps to Install
					</label>
					<div class="flex flex-wrap -mx-3">
						<div v-for="app in bench.apps" :key="app" class="w-1/6 p-3">
							<input type="checkbox" v-model="site.apps" :value="app" class="px-4 py-4 bg-gray-400 rounded hover:shadow">{{ app }}</div>
						</div>
						</div>
						</div>
						</div>
		  	<div class="-mx-3 mb-8 flex flex-row">
		  		<div class="w-1/2 pr-12">
					<div class="px-3">
						<label class="block uppercase tracking-wide text-gray-700 text-xs font-bold mb-2" for="grid-password">
						Number of Emails
						</label>
						<input class="appearance-none block w-full bg-gray-200 text-gray-700 border border-gray-200 rounded py-3 px-4 mb-3 leading-tight focus:outline-none focus:bg-white focus:border-gray-500" id="grid-password" type="number" placeholder="2000">
					</div>
					<div class="px-3">
						<label class="block uppercase tracking-wide text-gray-700 text-xs font-bold mb-2" for="grid-password">
						Number of Users
						</label>
						<input class="appearance-none block w-full bg-gray-200 text-gray-700 border border-gray-200 rounded py-3 px-4 mb-3 leading-tight focus:outline-none focus:bg-white focus:border-gray-500" id="grid-password" type="number" placeholder="2000">
					</div>
					<div class="px-3">
						<label class="block uppercase tracking-wide text-gray-700 text-xs font-bold mb-2" for="grid-password">
						Site Expiry
						</label>
						<input class="appearance-none block w-full bg-gray-200 text-gray-700 border border-gray-200 rounded py-3 px-4 mb-3 leading-tight focus:outline-none focus:bg-white focus:border-gray-500" id="grid-password" type="date">
					</div>
					<div class="flex px-3">
						<label class="md:w-2/3 block text-gray-700 font-bold">
						  <input class="mr-2 leading-tight" type="checkbox">
						  <span class="text-xs">
						    Enable Server Scripts
						  </span>
						</label>
					</div>
				</div>
				<div class="w-1/2 pr-12">
					<div class="px-3">
						<label class="block uppercase tracking-wide text-gray-700 text-xs font-bold mb-2" for="grid-password">
						SMTP Server
						</label>
						<input class="appearance-none block w-full bg-gray-200 text-gray-700 border border-gray-200 rounded py-3 px-4 mb-3 leading-tight focus:outline-none focus:bg-white focus:border-gray-500" id="grid-password" type="text" placeholder="hello.com">
					</div>
					<div class="px-3">
						<label class="block uppercase tracking-wide text-gray-700 text-xs font-bold mb-2" for="grid-password">
						Username
						</label>
						<input class="appearance-none block w-full bg-gray-200 text-gray-700 border border-gray-200 rounded py-3 px-4 mb-3 leading-tight focus:outline-none focus:bg-white focus:border-gray-500" id="grid-password" type="text" placeholder="email123">
					</div>
					<div class="px-3">
						<label class="block uppercase tracking-wide text-gray-700 text-xs font-bold mb-2" for="grid-password">
						Password
						</label>
						<input class="appearance-none block w-full bg-gray-200 text-gray-700 border border-gray-200 rounded py-3 px-4 mb-3 leading-tight focus:outline-none focus:bg-white focus:border-gray-500" id="grid-password" type="password" placeholder="****************">
					</div>
				</div>
		  	</div>
		  	<div class="mb-8">
		  		<button v-on:click="create()" class="bg-gray-900 rounded border-b-2 border-gray-700 px-3 py-2 text-white">Create Site</button>
		  	</div>
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
				apps: [],
			},
			bench: {
				name: null,
				apps: [],
			}
		};
	},
	mounted() {
		this.get();
	},
	methods: {
		get: async function() {
			let response = await fetch("/api/method/press.api.site.available");
			if (response.ok) {
				const bench = await response.json();
				this.bench = bench.message;
			} else {
				console.log("Something Went Wrong");
			}
		},
		create: async function() {
			let data = {site: this.site};
			let response = await fetch("/api/method/press.api.site.new", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(data)
			});
			if (response.ok) {
				const site = await response.json();
			} else {
				console.log("Something Went Wrong");
			}
		}
	}
};
</script>
