<template>
	<div>
		<div class="bg-blue-100 px-4 py-3 mb-3 rounded-md border border-blue-200">
			<p class="text-base space-y-2 leading-relaxed">
				This feature is under development and may not be suitable for production
				use. Use at your own risk. Please report any issues at:
				<a
					href="https://github.com/frappe/press/issues"
					target="_blank"
					class="font-medium"
					>github.com/frappe/press/issues</a
				>
			</p>
		</div>
		<div
			class="bg-yellow-100 px-4 py-3 mb-3 rounded-md border border-yellow-200"
		>
			<p class="text-base space-y-2 leading-relaxed">
				Please note that mis-configuring firewall rules can lead to loss of
				access and should be done with caution. It may take a few minutes for
				changes to take effect.
			</p>
		</div>
		<div class="flex items-center justify-between">
			<Switch
				label="Enabled"
				class="border w-60"
				v-model="server.doc.enabled"
				:disabled="server.get.loading"
			/>
			<div class="flex justify-center gap-2">
				<Button
					label="Discard"
					icon-left="trash-2"
					theme="gray"
					:disabled="!server.isDirty"
					@click.stop.prevent="() => server.reload()"
				/>
				<Button
					label="Save"
					icon-left="save"
					theme="green"
					:disabled="!server.isDirty"
					@click.stop.prevent="() => server.save.submit()"
				/>
				<Button
					label="Add Rule"
					icon-left="plus"
					variant="solid"
					@click="openAddDialog = !openAddDialog"
				/>
			</div>
		</div>
		<ObjectList
			:options="{
				data: () => server.doc.rules,
				columns: [
					{
						label: 'Source',
						fieldname: 'source',
						format: (value: string) => value || '—',
					},
					{
						label: 'Destination',
						fieldname: 'destination',
						format: (value: string) => value || '—',
					},
					{ label: 'Protocol', fieldname: 'protocol' },
					{ label: 'Action', fieldname: 'action' },
					{
						label: '',
						format: (_: any, row: any) => {
							if (row.name) {
								return '';
							}
							return 'Unsaved';
						},
						type: 'Badge',
						theme: 'orange',
						width: '100px',
					},
				],
				rowActions: ({ row }: any) => [
					{
						label: 'Remove',
						onClick: () => {
							server.doc.rules = server.doc.rules.filter(
								(rule: any) =>
									!(
										rule.source === row.source &&
										rule.destination === row.destination &&
										rule.protocol === row.protocol &&
										rule.action === row.action
									),
							);
						},
					},
				],
			}"
		/>
		<ServerFirewallDialog
			v-model="openAddDialog"
			@submit="(values) => server.doc.rules.push({ ...values })"
		/>
	</div>
</template>

<script setup lang="ts">
import { createDocumentResource, Switch } from 'frappe-ui';
import ObjectList from '../../components/ObjectList.vue';
import ServerFirewallDialog from './ServerFirewallDialog.vue';
import { ref } from 'vue';

const props = defineProps<{
	id: string;
}>();

const openAddDialog = ref(false);

const server = createDocumentResource({
	doctype: 'Server Firewall',
	name: props.id,
	auto: true,
	cache: ['Server', 'Firewall', props.id],
});
</script>
