<template>
	<div class="flex h-full flex-col">
		<div class="sticky top-0 z-10 shrink-0">
			<Header>
				<Breadcrumbs
					:items="[{ label: object.list.title, route: object.list.route }]"
				/>
			</Header>
		</div>
		<div class="p-5">
			<AlertAddPaymentMode class="mb-5" v-if="!$team.doc.payment_mode" />
			<ObjectList :options="listOptions" />
		</div>
	</div>
</template>

<script>
import Header from '../components/Header.vue';
import ObjectList from '../components/ObjectList.vue';
import { Breadcrumbs, Button, Dropdown, TextInput } from 'frappe-ui';
import { getObject } from '../objects';
import { defineAsyncComponent } from 'vue';

export default {
	components: {
		Header,
		Breadcrumbs,
		ObjectList,
		Button,
		Dropdown,
		TextInput,
		AlertAddPaymentMode: defineAsyncComponent(() =>
			import('../components/AlertAddPaymentMode.vue')
		)
	},
	props: {
		objectType: {
			type: String,
			required: true
		}
	},
	methods: {
		getRoute(row) {
			return {
				name: `${this.object.doctype} Detail`,
				params: {
					name: row.name
				}
			};
		}
	},
	computed: {
		object() {
			return getObject(this.objectType);
		},
		listOptions() {
			return {
				...this.object.list,
				doctype: this.object.doctype,
				route: this.object.detail ? this.getRoute : null
			};
		}
	}
};
</script>
