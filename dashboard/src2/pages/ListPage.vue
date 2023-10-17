<template>
	<div class="flex h-full flex-col">
		<div class="sticky top-0 z-10 shrink-0">
			<Header>
				<Breadcrumbs
					:items="[{ label: object.list.title, route: object.list.route }]"
				/>
				<!-- <Button>Actions</Button> -->
			</Header>
		</div>
		<ObjectList :list="listProp" />
	</div>
</template>

<script>
import { Breadcrumbs, Button, Dropdown, TextInput } from 'frappe-ui';

export default {
	components: {
		Breadcrumbs,
		Button,
		Dropdown,
		TextInput
	},
	props: {
		object: {
			type: Object,
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
		listProp() {
			return {
				...this.object.list,
				doctype: this.object.doctype,
				route: this.getRoute
			};
		}
	}
};
</script>
