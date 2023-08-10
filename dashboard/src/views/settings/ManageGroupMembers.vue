<template>
	<Dialog
		:options="{ title: `Manage Members for ${group.title}` }"
		:modelValue="show"
		@after-leave="
			() => {
				$emit('close', true);
				this.memberEmail = '';
			}
		"
	>
		<template v-slot:body-content>
			<LoadingText v-if="$resources.groupUsers.loading" />
			<div>
				<ListItem
					v-for="user in $resources.groupUsers.data"
					:title="user"
					:key="user"
				>
					<template #actions>
						<Button
							icon="trash"
							@click="
								() =>
									$resources.removeGroupUser.submit({
										name: group.name,
										user: user
									})
							"
						/>
					</template>
				</ListItem>
			</div>
		</template>
		<template v-slot:actions>
			<Combobox @update:model-value="onSelection">
				<ComboboxInput
					placeholder="Search for your team members"
					class="w-full rounded mb-2 border-gray-400 placeholder-gray-500 form-input"
					@input="onInput"
					autocomplete="off"
					:displayValue="() => memberEmail"
				/>
				<ComboboxOptions
					class="max-h-96 overflow-auto border-t border-gray-100"
					static
				>
					<ComboboxOption
						v-for="option in filteredList"
						:key="`${option.name}`"
						v-slot="{ active }"
						:value="option"
					>
						<div
							class="flex w-full items-center px-4 py-2 text-base text-gray-900"
							:class="{ 'bg-gray-200': active }"
						>
							<span> {{ option.name }}&nbsp; </span>
							<span class="ml-auto text-gray-600">
								{{ option.doctype }}
							</span>
						</div>
					</ComboboxOption>
				</ComboboxOptions>
			</Combobox>
			<Button
				variant="solid"
				label="Add Member"
				class="mt-2 w-full"
				:loading="$resources.groupUsers.loading"
				@click="
					$resources.addGroupUser.submit({
						name: group.name,
						user: memberEmail
					})
				"
			/>
		</template>
	</Dialog>
</template>

<script>
import {
	Combobox,
	ComboboxInput,
	ComboboxOptions,
	ComboboxOption
} from '@headlessui/vue';
import Fuse from 'fuse.js/dist/fuse.basic.esm';

export default {
	name: 'ManageGroupMembers',
	components: {
		Combobox,
		ComboboxInput,
		ComboboxOptions,
		ComboboxOption
	},
	data() {
		return {
			memberEmail: '',
			filteredList: [],
			autoCompleteList: []
		};
	},
	props: ['show', 'group'],
	watch: {
		group() {
			this.$resources.groupUsers.submit();
		}
	},
	methods: {
		onInput(e) {
			let query = e.target.value;
			if (query) {
				this.filteredList = this.fuse.search(query).map(result => result.item);
			} else {
				this.filteredList = this.autoCompleteList;
			}
		},
		onSelection(value) {
			if (value) {
				this.memberEmail = value.name;
			}
		}
	},
	resources: {
		removeGroupUser: {
			method: 'press.api.account.remove_permission_group_user',
			onSuccess() {
				this.$resources.groupUsers.fetch();
			}
		},
		addGroupUser: {
			method: 'press.api.account.add_permission_group_user',
			onSuccess() {
				this.$resources.groupUsers.fetch();
				this.memberEmail = '';
			}
		},
		groupUsers() {
			return {
				method: 'press.api.account.permission_group_users',
				params: {
					name: this.group.name
				},
				onSuccess(r) {
					this.autoCompleteList = this.$account.team_members.filter(user => {
						return (
							!r.includes(user.name) || user.name == this.$account.team.user
						);
					});
					this.fuse = new Fuse(this.autoCompleteList, {
						keys: ['name']
					});
					this.filteredList = this.autoCompleteList;
				}
			};
		}
	}
};
</script>
