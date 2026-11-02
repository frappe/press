<template>
	<div class="flex h-full flex-col">
		<Header :sticky="true">
			<Breadcrumbs
				:items="[{ label: object.list.title, route: object.list.route }]"
			/>
		</Header>
		<div class="p-5 pb-0">
			<BillingAlerts ctx-type="List Page" />
			<ObjectList :options="listOptions" />
		</div>
	</div>
</template>

<script>
import { Breadcrumbs, Button, Dropdown, TextInput } from 'frappe-ui'
import BillingAlerts from '../components/BillingAlerts.vue'
import Header from '../components/Header.vue'
import ObjectList from '../components/ObjectList.vue'
import { getObject } from '../objects'

export default {
	components: {
		Header,
		Breadcrumbs,
		ObjectList,
		Button,
		Dropdown,
		TextInput,
		BillingAlerts,
	},
	props: {
		objectType: {
			type: String,
			required: true,
		},
	},
	methods: {
		getRoute(row) {
			return {
				name: `${this.object.doctype} Detail`,
				params: {
					name: row.name,
				},
			}
		},
	},
	computed: {
		object() {
			return getObject(this.objectType)
		},
		listOptions() {
			return {
				...this.object.list,
				doctype: this.object.doctype,
				route: this.object.detail ? this.getRoute : null,
			}
		},
	},
}
</script>
