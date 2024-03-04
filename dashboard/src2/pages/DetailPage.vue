<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="w-full sm:flex sm:items-center sm:justify-between">
			<div class="flex items-center space-x-2">
				<FBreadcrumbs :items="breadcrumbs" />
				<Badge
					class="hidden sm:inline-flex"
					v-if="$resources.document?.doc && badge"
					v-bind="badge"
				/>
			</div>
			<div
				class="mt-1 flex items-center justify-between space-x-2 sm:mt-0"
				v-if="$resources.document?.doc"
			>
				<div class="sm:hidden">
					<Badge v-if="$resources.document?.doc && badge" v-bind="badge" />
				</div>
				<div class="space-x-2">
					<ActionButton
						v-for="button in actions"
						v-bind="button"
						:key="button.label"
					/>
				</div>
			</div>
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

let subscribed = {};

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
	data() {
		return {
			lastRefreshed: null
		};
	},
	resources: {
		document() {
			return {
				type: 'document',
				doctype: this.object.doctype,
				name: this.name,
				whitelistedMethods: this.object.whitelistedMethods || {},
				onSuccess() {
					this.lastRefreshed = new Date();
				}
			};
		}
	},
	mounted() {
		if (!subscribed[this.object.doctype]) {
			this.$socket.emit('doctype_subscribe', this.object.doctype);
			subscribed[this.object.doctype] = true;
		}
		this.$socket.on('list_update', data => {
			if (
				data.doctype === doctype &&
				data.name === this.name &&
				// update document if last refreshed is more than 5 seconds ago
				new Date() - this.lastRefreshed > 5000
			) {
				console.log('reloading', this.object.doctype, this.name);
				this.$resources.document.reload();
			}
		});
	},
	beforeUnmount() {
		if (subscribed[this.object.doctype]) {
			let doctype = this.object.doctype;
			this.$socket.emit('doctype_unsubscribe', doctype);
			subscribed[doctype] = false;
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
