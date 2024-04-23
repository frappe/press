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
		<TabsWithRouter
			v-if="!$resources.document.get.error && $resources.document.get.fetched"
			:tabs="object.detail.tabs"
		>
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
		<div
			v-else-if="$resources.document.get.error"
			class="mx-auto mt-60 w-fit rounded border border-dashed px-12 py-8 text-center text-gray-600"
		>
			<i-lucide-alert-triangle class="mx-auto mb-4 h-6 w-6 text-red-600" />
			<ErrorMessage :message="$resources.document.get.error" />
		</div>
	</div>
</template>

<script>
import LucideFrown from '~icons/lucide/frown';
import Header from '../components/Header.vue';
import ActionButton from '../components/ActionButton.vue';
import { Breadcrumbs } from 'frappe-ui';
import { getObject } from '../objects';
import TabsWithRouter from '../components/TabsWithRouter.vue';

let subscribed = {};

export default {
	name: 'DetailPage',
	props: {
		id: String,
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
		LucideFrown,
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
				whitelistedMethods: this.object.whitelistedMethods || {},
				onError(error) {
					for (let message of error?.messages || []) {
						if (message.redirect) {
							window.location.href = message.redirect;
							return;
						}
					}
				}
			};
		}
	},
	mounted() {
		if (!subscribed[`${this.object.doctype}:${this.name}`]) {
			this.$socket.emit('doc_subscribe', this.object.doctype, this.name);
			subscribed[`${this.object.doctype}:${this.name}`] = true;
		}
		this.$socket.on('doc_update', data => {
			if (data.doctype === this.object.doctype && data.name === this.name) {
				this.$resources.document.reload();
			}
		});
	},
	beforeUnmount() {
		let doctype = this.object.doctype;
		if (subscribed[`${doctype}:${this.name}`]) {
			this.$socket.emit('doc_unsubscribe', doctype, this.name);
			subscribed[`${doctype}:${this.name}`] = false;
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
