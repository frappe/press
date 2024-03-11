<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Upgrade Site Version' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<p v-if="site?.group_public && nextVersion" class="text-base">
					The site <b>{{ site.host_name }}</b> will be upgraded to
					<b>{{ nextVersion }}</b>
				</p>
				<FormControl
					v-else-if="privateReleaseGroups.length > 0 && nextVersion"
					:label="`Please select a ${nextVersion} bench to upgrade your site from ${site.frappe_version}`"
					class="w-full"
					type="select"
					:options="privateReleaseGroups"
					v-model="privateReleaseGroup"
					@change="
						value =>
							$resources.validateGroupforUpgrade.submit({
								name: site.name,
								group_name: value.target.value
							})
					"
				/>
				<FormControl
					class="mt-4"
					v-if="(site.group_public && nextVersion) || benchHasCommonServer"
					label="Schedule Site Migration"
					type="datetime-local"
					:min="new Date().toISOString().slice(0, 16)"
					v-model="targetDateTime"
				/>
				<p v-if="message" class="text-sm text-gray-700">
					{{ message }}
				</p>
				<ErrorMessage
					:message="
						$resources.versionUpgrade.error ||
						$resources.validateGroupforUpgrade.error ||
						$resources.addServerToReleaseGroup.error ||
						$resources.getPrivateGroups.error
					"
				/>
			</div>
		</template>
		<template v-if="site?.group_public || privateReleaseGroups.length" #actions>
			<Button
				v-if="!site.group_public"
				class="mb-2 w-full"
				:disabled="benchHasCommonServer || !privateReleaseGroup || !nextVersion"
				label="Add Server to Bench"
				@click="$resources.addServerToReleaseGroup.submit()"
				:loading="
					$resources.addServerToReleaseGroup.loading ||
					$resources.validateGroupforUpgrade.loading
				"
			/>
			<Button
				class="w-full"
				variant="solid"
				label="Upgrade"
				:disabled="
					((!benchHasCommonServer || !privateReleaseGroup) &&
						!site.group_public) ||
					!nextVersion
				"
				:loading="
					$resources.versionUpgrade.loading ||
					$resources.validateGroupforUpgrade.loading
				"
				@click="$resources.versionUpgrade.submit()"
			/>
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
			benchHasCommonServer: false
		};
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
			const nextNumber = Number(this.site?.frappe_version.split(' ')[1]);
			if (
				isNaN(nextNumber) ||
				this.site?.frappe_version === this.site?.latest_frappe_version
			)
				return null;

			return `Version ${nextNumber + 1}`;
		},
		privateReleaseGroups() {
			return this.$resources.getPrivateGroups.data;
		},
		message() {
			if (this.site.frappe_version === this.site.latest_frappe_version) {
				return 'This site is already on the latest version.';
			} else if (this.site.frappe_version === 'Nightly') {
				return "This site is on a nightly version and doesn't need to be upgraded.";
			} else if (
				!this.site.group_public &&
				this.privateReleaseGroups.length === 0
			)
				return `Your team doesn't own any private benches available to upgrade this site to ${this.nextVersion}.`;
			else if (!this.privateReleaseGroup) {
				return '';
			} else if (!this.site.group_public && !this.benchHasCommonServer)
				return `The selected bench and your site doesn't have a common server. Please add site's server to the bench.`;
			else if (!this.site.group_public && this.benchHasCommonServer)
				return `The selected bench and your site have a common server. You can proceed with the upgrade to ${this.nextVersion}.`;
			else return '';
		},
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			const datetimeInIST = this.$dayjs(this.targetDateTime)
				.tz('Asia/Kolkata')
				.format('YYYY-MM-DDTHH:mm');

			return datetimeInIST;
		}
	},
	resources: {
		versionUpgrade() {
			return {
				url: 'press.api.site.version_upgrade',
				params: {
					name: this.site?.name,
					destination_group: this.privateReleaseGroup,
					scheduled_datetime: this.datetimeInIST
				},
				onSuccess() {
					notify({
						title: 'Site Version Upgrade',
						message: `Scheduled site upgrade for <b>${this.site?.host_name}</b> to <b>${this.nextVersion}</b>`,
						icon: 'check',
						color: 'green'
					});
					this.$emit('update:modelValue', false);
				}
			};
		},
		getPrivateGroups() {
			return {
				url: 'press.api.site.get_private_groups_for_upgrade',
				params: {
					name: this.site?.name,
					version: this.site?.frappe_version
				},
				auto: true,
				validate() {
					if (
						!this.site?.group_public ||
						this.site?.frappe_version === 'Nightly'
					)
						return false;
				},
				transform(data) {
					return data.map(group => ({
						label: group.title || group.name,
						value: group.name
					}));
				},
				initialData: []
			};
		},
		addServerToReleaseGroup() {
			return {
				url: 'press.api.site.add_server_to_release_group',
				params: {
					name: this.site?.name,
					group_name: this.privateReleaseGroup
				},
				onSuccess(data) {
					notify({
						title: 'Server Added to the Bench',
						message: `Added a server to <b>${this.privateReleaseGroup}</b> bench. Please wait for the bench to complete the deploy.`,
						icon: 'check',
						color: 'green'
					});
					this.$router.push({
						name: 'BenchJobs',
						params: {
							benchName: this.privateReleaseGroup,
							jobName: data
						}
					});
					this.resetValues();
					this.$emit('update:modelValue', false);
				}
			};
		},
		validateGroupforUpgrade() {
			return {
				url: 'press.api.site.validate_group_for_upgrade',
				onSuccess(data) {
					this.benchHasCommonServer = data;
				}
			};
		}
	},
	methods: {
		resetValues() {
			this.targetDateTime = null;
			this.privateReleaseGroup = '';
			this.benchHasCommonServer = false;
			this.$resources.getPrivateGroups.reset();
		}
	}
};
</script>
