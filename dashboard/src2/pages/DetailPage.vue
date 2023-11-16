<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="flex items-center space-x-2">
			<Breadcrumbs
				:items="[
					{ label: object.list.title, route: object.list.route },
					{
						label: title,
						route: {
							name: `${object.doctype} Detail`,
							params: { name: this.name }
						}
					}
				]"
			/>
			<Badge v-if="$resources.document?.doc && badge" v-bind="badge" />
		</div>
		<div class="flex items-center space-x-2" v-if="$resources.document?.doc">
			<ActionButton
				v-for="button in actions"
				v-bind="button"
				:key="button.label"
			/>
		</div>
	</Header>
	<div>
		<FTabs v-model="currentTab" :tabs="object.detail.tabs">
			<template #default="{ tab }">
				<router-view
					:tab="tab"
					:document="$resources.document"
					v-if="$resources.document?.doc"
				/>
			</template>
		</FTabs>
	</div>
</template>

<script>
import { Tabs } from 'frappe-ui';

export default {
	name: 'DetailPage',
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
				name: this.name,
				whitelistedMethods: this.object.whitelistedMethods || {}
			};
		}
	},
	computed: {
		title() {
			let doc = this.$resources.document?.doc;
			return doc ? doc[this.object.detail.titleField || 'name'] : this.name;
		},
		badge() {
			if (this.object.detail.statusBadge) {
				return this.object.detail.statusBadge({
					documentResource: this.$resources.document
				});
			}
			return null;
		},
		actions() {
			if (this.object.detail.actions && this.$resources.document?.doc) {
				let actions = this.object.detail.actions({
					documentResource: this.$resources.document
				});
				return actions.filter(action => {
					if (action.condition) {
						return action.condition({
							documentResource: this.$resources.document
						});
					}
					return true;
				});
			}
			return [];
		}
	}
};
</script>
