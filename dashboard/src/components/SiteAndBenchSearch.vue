<template>
	<Dropdown :items="dropdownItems()" :dropdown-width-full="true" ref="dropdown">
		<template
			v-slot="{
				toggleDropdown,
				highlightItemUp,
				highlightItemDown,
				selectHighlightedItem
			}"
		>
			<Input
				type="text"
				ref="search"
				@focus="toggleDropdown()"
				@keydown.down="highlightItemDown()"
				@keydown.up="highlightItemUp()"
				@keydown.enter="
					selectHighlightedItem();
					toggleDropdown(false);
				"
				:modelValue="searchText"
				@input="val => (searchText = val)"
				placeholder="Search"
			/>
		</template>
	</Dropdown>
</template>

<script>
export default {
	data() {
		return {
			searchText: ''
		};
	},
	mounted() {
		document.addEventListener('keydown', e => {
			// TODO: Fit it in next iteration of the migration
			return; // TEMP, broken after frappe-ui migration

			if (e.key === '/' && e.ctrlKey) {
				e.preventDefault();
				this.searchText = '';
				this.$refs.search.focus();
				this.$refs.dropdown.toggleDropdown(true);
			} else if (e.key === 'Escape') {
				this.$refs.dropdown.toggleDropdown(false);
			}
		});
	},
	resources: {
		allSites() {
			return {
				method: 'press.api.site.search_list',
				auto: true,
				default: []
			};
		},
		allBenches() {
			return {
				method: 'press.api.bench.search_list',
				auto: true,
				default: []
			};
		},
		allServers() {
			return {
				method: 'press.api.server.search_list',
				auto: true,
				default: []
			};
		}
	},
	methods: {
		dropdownItems() {
			let siteList = this.$resources.allSites.data
				.filter(d => {
					if (!this.searchText) {
						return true;
					}
					if (d.name.toLowerCase().includes(this.searchText.toLowerCase())) {
						return true;
					}
					return false;
				})
				.map(d => {
					d.label = d.name;
					d.action = () => this.navigateSite(d.site);
					return d;
				})
				.slice(0, 5);

			let benchList = this.$resources.allBenches.data
				.filter(d => {
					if (!this.searchText) {
						return true;
					}
					if (d.title.toLowerCase().includes(this.searchText.toLowerCase())) {
						return true;
					}
					return false;
				})
				.map(d => {
					d.label = d.title;
					d.action = () => this.navigateBench(d.name);
					return d;
				})
				.slice(0, 5);

			let serverList = this.$resources.allServers.data
				.filter(d => {
					if (!this.searchText) {
						return true;
					}
					if (d.title.toLowerCase().includes(this.searchText.toLowerCase())) {
						return true;
					}
					return false;
				})
				.map(d => {
					d.label = d.title;
					d.action = () => this.navigateServer(d.server);
					return d;
				})
				.slice(0, 5);

			if (
				siteList.length === 0 &&
				benchList.length === 0 &&
				serverList.length === 0
			) {
				return [{ label: 'No results found' }];
			} else {
				return siteList.concat(benchList).concat(serverList);
			}
		},
		navigateSite(siteName) {
			this.$router.push(`/sites/${siteName}/overview`);
		},
		navigateBench(benchName) {
			this.$router.push(`/benches/${benchName}/overview`);
		},
		navigateServer(serverName) {
			this.$router.push(`/servers/${serverName}/overview`);
		}
	}
};
</script>
