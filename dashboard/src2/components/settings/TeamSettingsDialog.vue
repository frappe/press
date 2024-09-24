<template>
	<Dialog
		:options="{
			title: 'Settings'
		}"
		v-model="show"
	>
		<template #body-content>
			<div class="mt-8 flex flex-col gap-4">
				<Switch
					v-model="enforce2FA"
					label="Enforce 2FA"
					description="Require all team members to enable 2FA"
				/>
				<Switch
					v-model="enableInPlaceUpdates"
					label="Enable In Place Updates"
					description="Allows updating a bench directly without using a build step"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Switch } from 'frappe-ui';

export default {
	data() {
		return {
			show: true
		};
	},
	components: { Switch },
	computed: {
		enforce2FA: {
			get() {
				return Boolean(this.$team?.doc.enforce_2fa);
			},
			set(value) {
				this.$team.setValue.submit({ enforce_2fa: value });
			}
		},
		enableInPlaceUpdates: {
			get() {
				return Boolean(this.$team?.doc.enable_inplace_updates);
			},
			set(value) {
				this.$team.setValue.submit({ enable_inplace_updates: value });
			}
		}
	}
};
</script>
