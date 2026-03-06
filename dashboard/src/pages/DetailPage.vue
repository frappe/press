<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="w-full sm:flex sm:justify-between sm:items-center">
			<div class="flex items-center space-x-2">
				<FBreadcrumbs :items="breadcrumbs" />
				<Badge
					class="hidden sm:inline-flex"
					v-if="$resources.document?.doc && badge"
					v-bind="badge"
				/>
			</div>
			<div class="flex justify-between items-center mt-1 space-x-2 sm:mt-0">
				<div class="sm:hidden">
					<Badge v-if="$resources.document?.doc && badge" v-bind="badge" />
				</div>
				<AccessRequestButton
					:doctype="object.doctype"
					:docname="name"
					:doc="$resources.document?.doc"
					:error="$resources.document.get.error"
				/>
				<div class="space-x-2" v-if="$resources.document?.doc">
					<ActionButton
						v-for="action in actions"
						v-bind="action"
						:actionsAccess="$resources.document?.doc?.actions_access"
						:key="action.label"
					/>
				</div>
			</div>
		</div>
	</Header>
	<div>
		<TabsWithRouter
			v-if="!$resources.document.get.error && $resources.document.get.fetched"
			:document="$resources.document?.doc"
			:tabs="tabs"
		>
			<template #tab-item="{ tab }">
				<router-link
					:to="{ name: tab.routeName }"
					class="flex whitespace-nowrap items-center py-2.5 gap-1.5 text-base text-ink-gray-5 duration-300 ease-in-out hover:text-ink-gray-9 data-[state=active]:text-ink-gray-9"
				>
					<component v-if="tab.icon" :is="tab.icon" class="size-4"> </component>

					{{ tab.label }}
				</router-link>
			</template>
			<template #tab-content="{ tab }">
				<router-view
					v-if="$resources.document?.doc"
					:tab="tab"
					:document="$resources.document"
				/>
			</template>
		</TabsWithRouter>
		<DetailPageError
			class="mt-60"
			:doctype="object.doctype"
			:docname="name"
			:error="$resources.document.get.error"
		/>
	</div>
</template>

<script>
import Header from '../components/Header.vue';
import ActionButton from '../components/ActionButton.vue';
import DetailPageError from '../components/DetailPageError.vue';
import { Breadcrumbs } from 'frappe-ui';
import { getObject } from '../objects';
import TabsWithRouter from '../components/TabsWithRouter.vue';
import AccessRequestButton from '../components/AccessRequestButton.vue';

let subscribed = {};

export default {
	name: 'DetailPage',
	props: {
		id: String,
		objectType: {
			type: String,
			required: true,
		},
		name: {
			type: String,
			required: true,
		},
	},
	components: {
		Header,
		ActionButton,
		TabsWithRouter,
		FBreadcrumbs: Breadcrumbs,
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
				},
			};
		},
	},
	mounted() {
		if (!subscribed[`${this.object.doctype}:${this.name}`]) {
			this.$socket.emit('doc_subscribe', this.object.doctype, this.name);
			subscribed[`${this.object.doctype}:${this.name}`] = true;
		}
		this.$socket.on('doc_update', (data) => {
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
		tabs() {
			return this.object.detail.tabs.filter((tab) => {
				if (tab.condition) {
					return tab.condition({
						documentResource: this.$resources.document,
					});
				}
				return true;
			});
		},
		title() {
			let doc = this.$resources.document?.doc;
			return doc ? doc[this.object.detail.titleField || 'name'] : this.name;
		},
		badge() {
			if (this.object.detail.statusBadge) {
				return this.object.detail.statusBadge({
					documentResource: this.$resources.document,
				});
			}
			return null;
		},
		actions() {
			if (this.object.detail.actions && this.$resources.document?.doc) {
				let actions = this.object.detail.actions({
					documentResource: this.$resources.document,
				});
				return actions.filter((action) => {
					if (action.condition) {
						return action.condition({
							documentResource: this.$resources.document,
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
						params: { name: this.name },
					},
				},
			];
			if (this.object.detail.breadcrumbs && this.$resources.document?.doc) {
				let result = this.object.detail.breadcrumbs({
					documentResource: this.$resources.document,
					items,
				});
				if (Array.isArray(result)) {
					items = result;
				}
			}

			// add ellipsis if breadcrumbs too long
			for (let i = 0; i < items.length; i++) {
				if (items[i].label.length > 30 && i !== items.length - 1) {
					items[i].label = items[i].label.slice(0, 30) + '...';
				}
			}

			return items;
		},
	},
};
</script>
<style scoped>
:deep(button[role='tab']) {
	white-space: nowrap;
}
</style>
