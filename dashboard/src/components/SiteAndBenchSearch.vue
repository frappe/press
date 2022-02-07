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
				class="md:w-40 lg:w-60"
				ref="search"
				@focus="toggleDropdown()"
				@keydown.down="highlightItemDown()"
				@keydown.up="highlightItemUp()"
				@keydown.enter="
					selectHighlightedItem();
					toggleDropdown(false);
					$refs.search.blur();
				"
				:value="searchText"
				@input="val => (searchText = val)"
				placeholder="Search (Ctrl + /)"
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
		allSites: {
			method: 'press.api.site.search_list',
			auto: true,
			default: []
		},
		allBenches: {
			method: 'press.api.bench.search_list',
			auto: true,
			default: []
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
					d.action = () => this.navigateSite(d.name);
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

			if (siteList.length === 0 && benchList.length === 0) {
				return [{ label: 'No results found' }];
			} else {
				return siteList.concat(benchList);
			}
		},
		navigateSite(siteName) {
			this.$router.push(`/sites/${siteName}/overview`);
		},
		navigateBench(benchName) {
			this.$router.push(`/benches/${benchName}/overview`);
		}
	}
};
</script>
