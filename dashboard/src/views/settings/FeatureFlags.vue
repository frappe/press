<template>
	<Card title="Advanced features" v-if="$account.hasRole('Press Admin')">
		<div class="flex flex-col space-y-4">
			<FormControl
				v-for="field in fields"
				type="checkbox"
				:label="field.label"
				v-model="values[field.fieldname]"
			/>
		</div>
		<div class="mt-4">
			<Button
				variant="solid"
				v-if="isDirty"
				@click="$resources.updateFeatureFlags.submit()"
				:loading="$resources.updateFeatureFlags.loading"
			>
				Save changes
			</Button>
		</div>
	</Card>
</template>
<script>
import { FormControl } from 'frappe-ui';

let fields = [
	{ label: 'Enable private benches', fieldname: 'benches_enabled' },
	{ label: 'Enable servers', fieldname: 'servers_enabled' },
	{
		label: 'Enable self-hosted servers',
		fieldname: 'self_hosted_servers_enabled'
	},
	{
		label: 'Enable security portal',
		fieldname: 'security_portal_enabled'
	}
];

export default {
	name: 'FeatureFlags',
	components: { FormControl },
	data() {
		let values = {};

		for (let field of fields) {
			values[field.fieldname] = Boolean(this.$account.team[field.fieldname]);
		}

		return {
			values,
			fields
		};
	},
	resources: {
		updateFeatureFlags() {
			return {
				url: 'press.api.account.update_feature_flags',
				params: {
					values: this.values
				},
				onSuccess() {
					this.$account.fetchAccount();
				}
			};
		}
	},
	computed: {
		isDirty() {
			return Object.keys(this.values).some(
				key => Number(this.values[key]) !== Number(this.$account.team[key])
			);
		}
	}
};
</script>
