<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Upgrade Site Version' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<p v-if="$site.doc?.group_public && nextVersion" class="text-base">
					The site <b>{{ $site.doc.host_name }}</b> will be upgraded to
					<b>{{ nextVersion }}</b>
				</p>
				<FormControl
					v-else-if="privateReleaseGroups.length > 0 && nextVersion"
					variant="outline"
					:label="`Please select a ${nextVersion} bench group to upgrade your site from ${$site.doc.version}`"
					class="w-full"
					type="autocomplete"
					:options="privateReleaseGroups"
					v-model="privateReleaseGroup"
				/>
				<DateTimeControl
					v-if="($site.doc.group_public && nextVersion) || benchHasCommonServer"
					v-model="targetDateTime"
					label="Schedule Time"
				/>
				<FormControl
					v-if="($site.doc.group_public && nextVersion) || benchHasCommonServer"
					label="Skip failing patches if any"
					type="checkbox"
					v-model="skipFailingPatches"
				/>
				<FormControl
					v-if="($site.doc.group_public && nextVersion) || benchHasCommonServer"
					label="Skip backups"
					type="checkbox"
					v-model="skipBackups"
					class="ml-4"
				/>
				<div
					v-if="skipBackups"
					class="flex items-center rounded bg-gray-50 p-4 text-sm text-gray-700"
				>
					<i-lucide-info class="mr-2 h-4 w-8" />
					Backups will not be taken during the upgrade process and incase of any
					failure rollback will not be possible.
				</div>
				<p v-if="message && !errorMessage" class="text-sm text-gray-700">
					{{ message }}
				</p>
				<ErrorMessage :message="errorMessage" />
			</div>
		</template>
		<template
			v-if="$site.doc?.group_public || privateReleaseGroups.length"
			#actions
		>
			<Button
				v-if="!$site.doc.group_public"
				class="mb-2 w-full"
				:disabled="
					benchHasCommonServer || !privateReleaseGroup.value || !nextVersion
				"
				label="Add Server to Bench Group"
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
					((!benchHasCommonServer || !privateReleaseGroup.value) &&
						!$site.doc.group_public) ||
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
import { getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import DateTimeControl from '../DateTimeControl.vue';

export default {
	name: 'SiteVersionUpgradeDialog',
	props: ['site'],
	components: { DateTimeControl },
	data() {
		return {
			show: true,
			targetDateTime: null,
			privateReleaseGroup: {
				value: '',
				label: ''
			},
			skipBackups: false,
			skipFailingPatches: false,
			benchHasCommonServer: false
		};
	},
	watch: {
		privateReleaseGroup: {
			handler(privateReleaseGroup) {
				if (privateReleaseGroup?.value) {
					this.$resources.validateGroupforUpgrade.submit({
						name: this.site,
						group_name: privateReleaseGroup.value
					});
				}
			}
		}
	},
	computed: {
		nextVersion() {
			const nextNumber = Number(this.$site.doc?.version.split(' ')[1]);
			if (
				isNaN(nextNumber) ||
				this.$site.doc?.version === this.$site.doc?.latest_frappe_version
			)
				return null;

			return `Version ${nextNumber + 1}`;
		},
		privateReleaseGroups() {
			return this.$resources.getPrivateGroups.data;
		},
		message() {
			if (this.$site.doc?.version === this.$site.doc?.latest_frappe_version) {
				return 'This site is already on the latest version.';
			} else if (this.$site.doc?.version === 'Nightly') {
				return "This site is on a nightly version and doesn't need to be upgraded.";
			} else if (
				!this.$site.doc?.group_public &&
				this.privateReleaseGroups.length === 0
			)
				return `Your team doesn't own any private bench groups available to upgrade this site to ${this.nextVersion}.`;
			else if (!this.privateReleaseGroup.value) {
				return '';
			} else if (!this.$site.doc?.group_public && !this.benchHasCommonServer)
				return `The selected bench group and your site doesn't have a common server. Please add site's server to the bench.`;
			else if (!this.$site.doc?.group_public && this.benchHasCommonServer)
				return `The selected bench group and your site have a common server. You can proceed with the upgrade to ${this.nextVersion}.`;
			else return '';
		},
		datetimeInIST() {
			if (!this.targetDateTime) return null;
			const datetimeInIST = this.$dayjs(this.targetDateTime).format(
				'YYYY-MM-DDTHH:mm'
			);

			return datetimeInIST;
		},
		errorMessage() {
			return (
				this.$resources.versionUpgrade.error ||
				this.$resources.validateGroupforUpgrade.error ||
				this.$resources.addServerToReleaseGroup.error ||
				this.$resources.getPrivateGroups.error
			);
		},
		$site() {
			return getCachedDocumentResource('Site', this.site);
		}
	},
	resources: {
		versionUpgrade() {
			return {
				url: 'press.api.site.version_upgrade',
				params: {
					name: this.site,
					destination_group: this.privateReleaseGroup.value,
					skip_failing_patches: this.skipFailingPatches,
					skip_backups: this.skipBackups,
					scheduled_datetime: this.datetimeInIST
				},
				onSuccess() {
					toast.success("Site's version upgrade has been scheduled.");
					this.show = false;
				}
			};
		},
		getPrivateGroups() {
			return {
				url: 'press.api.site.get_private_groups_for_upgrade',
				params: {
					name: this.site,
					version: this.$site.doc?.version
				},
				auto:
					this.$site.doc?.version &&
					!this.$site.doc?.group_public &&
					this.$site.doc?.version !== 'Nightly',
				transform(data) {
					return data.map(group => ({
						label: group.title || group.name,
						description: group.name,
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
					name: this.site,
					group_name: this.privateReleaseGroup.value
				},
				onSuccess(data) {
					toast.success('Server Added to the Bench Group', {
						description: `Added a server to ${this.privateReleaseGroup.value} bench. Please wait for the deploy to be completed.`
					});
					this.$router.push({
						name: 'Release Group Job',
						params: {
							name: this.privateReleaseGroup.value,
							id: data
						}
					});
					this.resetValues();
					this.show = false;
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
			this.privateReleaseGroup = {
				label: '',
				value: ''
			};
			this.benchHasCommonServer = false;
			this.$resources.getPrivateGroups.reset();
		}
	}
};
</script>
