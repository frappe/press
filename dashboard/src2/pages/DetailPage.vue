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
		<TabsWithRouter :tabs="object.detail.tabs">
			<template #tab-content="{ tab }">
				<!-- this div is required for some reason -->
				<div></div>
				<router-view
					v-if="$resources.document?.doc"
					:tab="tab"
					:document="$resources.document"
				/>
			</template>
		</TabsWithRouter>
	</div>
</template>

<script>
import Header from '../components/Header.vue';
import ActionButton from '../components/ActionButton.vue';
import { Breadcrumbs } from 'frappe-ui';
import { getObject } from '../objects';
import TabsWithRouter from '../components/TabsWithRouter.vue';

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
		Header,
		ActionButton,
		TabsWithRouter,
		FBreadcrumbs: Breadcrumbs
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
<style scoped>
:deep(button[role='tab']) {
	white-space: nowrap;
}
</style>
