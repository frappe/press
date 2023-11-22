<template>
	<Dialog
		v-model="show"
		@close="resetValues"
		:options="{ title: 'Upgrade Site Version' }"
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
					@change="
						benchHasCommonServer = false;
						benchValidationStarted = false;
					"
				/>
				<FormControl
					class="mt-4"
					v-if="site.is_public || benchHasCommonServer"
					label="Schedule Site Migration (IST)"
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
		<template v-if="privateReleaseGroups.length" #actions>
			<Button
				v-if="!this.benchValidationStarted"
				class="w-full"
				variant="solid"
				label="Validate Bench for Version Upgrade"
				@click="$resources.validateGroupforUpgrade.submit()"
				:loading="$resources.validateGroupforUpgrade.loading"
			/>
			<Button
				v-else-if="!this.benchHasCommonServer"
				class="w-full"
				variant="solid"
				label="Add Server to Bench"
				@click="$resources.addServerToReleaseGroup.submit()"
				:loading="$resources.addServerToReleaseGroup.loading"
			/>
			<Button
				v-else
				class="w-full"
				variant="solid"
				label="Upgrade"
				:loading="$resources.versionUpgrade.loading"
				@click="
					{
						$resources.versionUpgrade.submit();
						$emit('update:modelValue', false);
					}
				"
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
			benchHasCommonServer: false,
			benchValidationStarted: false
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
		},
		privateReleaseGroups() {
			return this.$resources.getPrivateGroups.data;
		},
		message() {
			if (!this.site.is_public && !this.privateReleaseGroups.length)
				return `Your team don't own any private benches available to upgrade this site to ${this.nextVersion}.`;
			else if (
				!this.site.is_public &&
				this.benchValidationStarted &&
				!this.benchHasCommonServer
			)
				return `The selected bench and site doesn't have a common server. Please add a common server.`;
			else if (
				!this.site.is_public &&
				this.benchValidationStarted &&
				this.benchHasCommonServer
			)
				return `The selected bench and site have a common server. You can proceed with the upgrade to ${this.nextVersion}.`;
			else return '';
		}
	},
	resources: {
		versionUpgrade() {
			return {
				url: 'press.api.site.version_upgrade',
				params: {
					name: this.site?.name,
					destination_group: this.privateReleaseGroup,
					scheduled_datetime: this.targetDateTime
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
					this.$emit('update:modelValue', false);
				}
			};
		},
		validateGroupforUpgrade() {
			return {
				url: 'press.api.site.validate_group_for_upgrade',
				params: {
					name: this.site?.name,
					group_name: this.privateReleaseGroup
				},
				onSuccess(data) {
					this.benchValidationStarted = true;
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
			this.benchValidationStarted = false;
			this.$resources.getPrivateGroups.reset();
		}
	}
};
</script>
