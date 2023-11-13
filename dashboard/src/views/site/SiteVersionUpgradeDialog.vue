<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{
			title: 'Upgrade Site Version',
			actions: [
				{
					label: 'Upgrade',
					variant: 'solid',
					disabled: !site?.is_public && privateReleaseGroups.length === 0,
					onClick: () => {
						this.$resources.versionUpgrade.submit({
							name: this.site?.name,
							destination_group: this.privateReleaseGroup,
							scheduled_datetime: this.targetDateTime
						});
						this.$emit('update:modelValue', false);
					}
				}
			]
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<p v-if="site.is_public" class="text-base">
					The site <b>{{ site.host_name }}</b> will be upgraded to
					<b>{{ nextVersion }}</b>
				</p>
				<FormControl
					v-else-if="privateReleaseGroups.length > 0"
					:label="`Please select a ${nextVersion} bench`"
					class="w-full"
					type="select"
					:options="privateReleaseGroups"
					v-model="privateReleaseGroup"
				/>
				<div
					v-if="site?.is_public || privateReleaseGroups.length > 0"
					class="space-y-4"
				>
					<FormControl
						class="mt-4"
						v-if="privateReleaseGroups.length > 0"
						label="Schedule Site Migration (IST)"
						type="datetime-local"
						:min="new Date().toISOString().slice(0, 16)"
						v-model="targetDateTime"
					/>
				</div>
				<p v-else class="text-base">
					There are no private release groups available to upgrade this site.
				</p>
				<ErrorMessage :message="$resources.versionUpgrade.error" />
			</div>
		</template>
	</Dialog>
</template>

<script>
import { notify } from '@/utils/toast';

export default {
	name: 'SiteVersionUpgradeDialog',
	props: ['site', 'modelValue'],
	emits: ['update:modelValue'],
	data() {
		return {
			targetDateTime: null,
			privateReleaseGroup: '',
			privateReleaseGroups: []
		};
	},
	watch: {
		show(value) {
			if (value) this.$resources.getPrivateGroups.fetch();
		}
	},
	computed: {
		show: {
			get() {
				return this.modelValue;
			},
			set(value) {
				this.$emit('update:modelValue', value);
			}
		},
		nextVersion() {
			return `Version ${Number(this.site?.frappe_version.split(' ')[1]) + 1}`;
		}
	},
	resources: {
		versionUpgrade() {
			return {
				url: 'press.api.site.version_upgrade',
				params: {
					site: this.site?.name,
					destination_group: this.privateReleaseGroup
				},
				onSuccess() {
					notify({
						title: 'Site Version Upgrade',
						message: `Scheduled site upgrade for <b>${this.site?.host_name}</b> to <b>${this.nextVersion}</b>`,
						icon: 'check',
						color: 'green'
					});
				}
			};
		},
		getPrivateGroups() {
			if (this.site?.is_public) return;

			return {
				url: 'press.api.site.get_private_groups_for_upgrade',
				params: {
					name: this.site?.name,
					version: this.site?.frappe_version
				},
				onSuccess(data) {
					this.privateReleaseGroups = data.map(group => ({
						label: group.title || group.name,
						value: group.name
					}));
				}
			};
		}
	},
	methods: {
		resetValues() {
			this.targetDateTime = null;
			this.privateReleaseGroup = '';
			this.privateReleaseGroups = [];
		}
	}
};
</script>
