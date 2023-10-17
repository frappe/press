<template>
	<div>
		<Header>
			<Breadcrumbs
				:items="[
					{ label: object.list.title, route: object.list.route },
					{ label: name, route: object.detail.route }
				]"
			/>
		</Header>
		<div>
			<FTabs v-model="currentTab" :tabs="object.detail.tabs">
				<template #default="{ tab }">
					<router-view
						:tab="tab"
						:document="$resources.document"
						v-if="$resources.document.doc"
					/>
				</template>
			</FTabs>
		</div>
	</div>
</template>

<script>
import { Tabs } from 'frappe-ui';

export default {
	name: 'Detail',
	props: {
		object: {
			type: Object,
			required: true
		},
		name: {
			type: String,
			required: true
		}
	},
	components: {
		FTabs: Tabs
	},
	data() {
		let currentTab = 0;
		let currentRoute = this.$route.name;
		for (let tab of this.object.detail.tabs) {
			let routeName = `${this.object.doctype} Detail ${tab.label}`;
			if (currentRoute === routeName) {
				currentTab = this.object.detail.tabs.indexOf(tab);
				break;
			}
		}
		return {
			currentTab
		};
	},
	watch: {
		currentTab(value) {
			let tab = this.object.detail.tabs[value];
			let routeName = `${this.object.doctype} Detail ${tab.label}`;
			this.$router.replace({ name: routeName });
		}
	},
	resources: {
		document() {
			return {
				type: 'document',
				doctype: this.object.doctype,
				name: this.name
			};
		}
	}
};
</script>
