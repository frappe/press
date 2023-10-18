<template>
	<button
		class="flex w-full flex-row items-center justify-between rounded-lg border border-gray-100 px-4 py-2 shadow focus:outline-none"
		:class="[
			selected || uninstall ? 'ring-2 ring-inset ring-gray-600' : '',
			selectable ? 'hover:border-gray-300' : 'cursor-default'
		]"
		ref="card"
	>
		<div class="flex flex-row items-center gap-2">
			<input
				v-if="selectable"
				@click.self="$refs['card'].click()"
				:checked="selected"
				type="checkbox"
				class="h-4 w-4 cursor-pointer rounded border-gray-300 text-gray-600 focus:ring-transparent"
			/>
			<h3 class="text-left text-lg font-medium text-gray-900">
				{{ app.title }}
			</h3>
		</div>
		<Badge v-if="uninstall" theme="red" label="Will Be Uninstalled " />
		<div v-else class="ml-2 flex flex-row items-center space-x-2">
			<CommitTag
				v-if="deployFrom"
				:tag="deployFrom"
				:link="`${app.repository_url}/commit/${app.current_hash}`"
			/>
			<a
				v-if="deployFrom"
				class="flex cursor-pointer flex-col justify-center"
				:href="`${app.repository_url}/compare/${app.current_hash}...${getHash(
					deployTo.value
				)}`"
				target="_blank"
			>
				<FeatherIcon name="arrow-right" class="w-4" />
			</a>
			<Badge
				v-else
				label="First Deploy"
				theme="green"
				class="whitespace-nowrap"
			/>
			<CommitChooser :options="autocompleteOptions" v-model="deployTo" />
		</div>
	</button>
</template>

<script>
import CommitChooser from './utils/CommitChooser.vue';
import CommitTag from './utils/CommitTag.vue';
export default {
	name: 'AppUpdateCard',
	props: ['app', 'selectable', 'selected', 'uninstall'],
	data() {
		return {
			deployTo: {
				label: this.initialDeployTo(),
				value: this.app.next_release
			}
		};
	},
	watch: {
		deployTo(newVal) {
			this.app.next_release = newVal.value;
			this.$emit('update:app', this.app);
		}
	},
	computed: {
		deployFrom() {
			if (this.app.will_branch_change) {
				return this.app.current_branch;
			}
			return this.app.current_hash
				? this.app.current_tag || this.app.current_hash.slice(0, 7)
				: null;
		},
		autocompleteOptions() {
			return this.app.releases.map(release => {
				const messageMaxLength = 75;
				let message = release.message.split('\n')[0];
				message =
					message.length > messageMaxLength
						? message.slice(0, messageMaxLength) + '...'
						: message;

				return {
					label: release.tag
						? release.tag
						: `${message} (${release.hash.slice(0, 7)})`,
					value: release.name
				};
			});
		}
	},
	methods: {
		initialDeployTo() {
			let next_release = this.app.releases.filter(
				release => release.name === this.app.next_release
			)[0];
			if (this.app.will_branch_change) {
				return this.app.branch;
			} else {
				return next_release.tag || next_release.hash.slice(0, 7);
			}
		},
		getHash(tag) {
			return this.app.releases.find(release => release.name === tag).hash;
		}
	},
	components: { CommitTag, CommitChooser }
};
</script>
