<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="flex items-center space-x-2">
			<FBreadcrumbs :items="breadcrumbs" />
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
import { Tabs, Breadcrumbs } from 'frappe-ui';
import { getObject } from '../objects';

export default {
	name: 'DetailPage',
	props: {
		objectType: {
			type: String,
			required: true
		},
		name: {
			type: String,
			required: true
		}
	},
	components: {
		FTabs: Tabs,
		FBreadcrumbs: Breadcrumbs
	},
	data() {
		return {
			currentTab: 0
		};
	},
	beforeRouteUpdate(to, from, next) {
		this.setTabToRoute(to);
		next();
	},
	mounted() {
		this.setTabToRoute(this.$route);
	},
	watch: {
		currentTab(value) {
			let tab = this.object.detail.tabs[value];
			this.$router.replace({ name: tab.routeName });
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
	methods: {
		setTabToRoute(route) {
			for (let tab of this.object.detail.tabs) {
				if (route.name === tab.routeName) {
					this.currentTab = this.object.detail.tabs.indexOf(tab);
					break;
				}
			}
		}
	},
	computed: {
		object() {
			return getObject(this.objectType);
		},
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
		},
		breadcrumbs() {
			let items = [
				{ label: this.object.list.title, route: this.object.list.route },
				{
					label: this.title,
					route: {
						name: `${this.object.doctype} Detail`,
						params: { name: this.name }
					}
				}
			];
			if (this.object.detail.breadcrumbs && this.$resources.document?.doc) {
				let result = this.object.detail.breadcrumbs({
					documentResource: this.$resources.document,
					items
				});
				if (Array.isArray(result)) {
					items = result;
				}
			}
			return items;
		}
	}
};
</script>
