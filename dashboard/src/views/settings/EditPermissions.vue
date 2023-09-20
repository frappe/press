<template>
	<Dialog
		:options="{
			title: `Editing permissions for ${
				type === 'group' ? 'group' : 'member'
			} ${name}`,
			size: '3xl'
		}"
		:modelValue="show"
		@after-leave="
			() => {
				$emit('close', true);
			}
		"
	>
		<template v-slot:body-content>
			<Input
				class="mb-2"
				placeholder="Search"
				v-on:input="e => updateSearchTerm(e)"
			/>
			<LoadingText v-if="$resources.options.loading" />
			<div v-else class="mb-8 flex flex-col max-h-96 overflow-auto">
				<div v-for="(option, index) in filteredList" class="border-b pt-2">
					<span class="mr-2 mt-4 w-full pb-2 text-lg text-gray-600">
						{{ option.doctype }}
					</span>
					<span class="inline-block align-middle text-base font-bold">
						{{ option.title ? option.title : option.name }}
					</span>
					<Input
						class="pt-4"
						type="checkbox"
						label="Select All"
						@change="val => toggleSelectAll(option, index, val)"
					/>
					<div class="grid grid-cols-4 gap-4 py-4">
						<Input
							v-for="[label, action] in Object.entries(actions[option.doctype])"
							type="checkbox"
							:checked="isSelected(option, action)"
							:label="label"
							@change="() => updateAction(option, index, action)"
						>
						</Input>
					</div>
				</div>
			</div>
		</template>
		<template v-slot:actions>
			<Button
				variant="solid"
				class="w-full"
				@click="$resources.updatePermissions.submit()"
			>
				Save
			</Button>
		</template>
	</Dialog>
</template>

<script>
import Fuse from 'fuse.js/dist/fuse.basic.esm';
import { notify } from '@/utils/toast';

export default {
	name: 'EditPermissions',
	props: ['show', 'name', 'type'],
	data() {
		return {
			updated: {},
			filteredList: []
		};
	},
	resources: {
		options() {
			return {
				url: 'press.api.account.get_permission_options',
				auto: true,
				params: {
					name: this.name,
					ptype: this.type
				},
				onSuccess(r) {
					this.fuse = new Fuse(r.options, {
						keys: ['name'],
						threshold: 0.3
					});
					this.filteredList = r.options;
				}
			};
		},
		updatePermissions() {
			return {
				url: 'press.api.account.update_permissions',
				params: {
					user: this.name,
					ptype: this.type,
					updated: this.updated
				},
				onSuccess() {
					notify({
						title: 'Permissions Updated',
						color: 'green',
						icon: 'check'
					});
					this.$emit('close', true);
					this.$resources.options.fetch();
				}
			};
		}
	},
	methods: {
		isSelected(option, action) {
			let alreadyAdded = false;
			if (option.perms !== null) {
				alreadyAdded = option.perms.includes(action);
			}
			return (
				alreadyAdded ||
				(this.updated?.[option.doctype]?.[option.name] || []).includes(action)
			);
		},
		updateSearchTerm(value) {
			if (value) {
				this.filteredList = this.fuse.search(value).map(result => result.item);
			} else {
				this.filteredList = this.options;
			}
		},
		updateAction(option, index, action) {
			// create updated object for doctype if it doesn't exists
			if (!this.updated[option.doctype]) {
				// if an entry for docname doesn't exists add it to update object with default permission
				this.updated[option.doctype] = {};
			}
			// create updated record for docname if it doesn't exists and set all existing perms
			if (!this.updated[option.doctype][option.name]) {
				this.updated[option.doctype][option.name] =
					option.perms === null ? [] : option.perms.split(',');
			}
			if (this.updated[option.doctype][option.name].includes(action)) {
				// toggle off
				this.updated[option.doctype][option.name] = this.updated[
					option.doctype
				][option.name].filter(item => item !== action);
			} else {
				// toggled on
				this.updated[option.doctype][option.name].push(action);
			}
		},
		toggleSelectAll(option, index, selected) {
			if (!this.updated[option.doctype]) {
				this.updated[option.doctype] = {};
			}
			const allActions = Object.values(this.actions[option.doctype]);
			this.updated[option.doctype][option.name] = selected
				? Object.assign([], allActions)
				: [];
			this.filteredList[index].perms = selected ? allActions.join(',') : '';
		}
	},
	computed: {
		options() {
			if (!this.$resources.options.data) return [];
			return this.$resources.options.data.options;
		},
		actions() {
			if (!this.$resources.options.data) return {};
			return this.$resources.options.data.actions;
		}
	}
};
</script>
