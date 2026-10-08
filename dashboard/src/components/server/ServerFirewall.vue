<template>
	<div class="space-y-3">
		<div>
			<h2 class="text-lg font-medium text-ink-gray-9">Firewall</h2>
			<p class="mt-1 text-p-base text-ink-gray-6">
				Allow or block traffic to this server by source, port and protocol.
			</p>
		</div>
		<div v-if="firewall.doc" class="flex items-center justify-between">
			<FormControl
				type="checkbox"
				label="Enabled"
				:model-value="Boolean(firewall.doc.enabled)"
				:disabled="firewall.get.loading"
				@update:model-value="(value) => (firewall.doc.enabled = value ? 1 : 0)"
			/>
			<div class="flex justify-center gap-2">
				<Button
					label="Discard"
					icon-left="trash-2"
					theme="gray"
					:disabled="!firewall.isDirty"
					@click.stop.prevent="() => firewall.reload()"
				/>
				<Button
					label="Save"
					icon-left="save"
					theme="green"
					:disabled="!firewall.isDirty || firewall.save.loading"
					@click.stop.prevent="save"
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
			v-if="firewall.doc"
			:options="{
				data: () => firewall.doc.rules,
				columns: [
					{
						label: 'Source',
						fieldname: 'source',
						format: (value: string) => value || '—',
					},
					{
						label: 'Port',
						fieldname: 'port',
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
							firewall.doc.rules = firewall.doc.rules.filter(
								(rule: any) =>
									!(
										rule.source === row.source &&
										rule.port === row.port &&
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
			@submit="(values) => firewall.doc.rules.push({ ...values })"
		/>
	</div>
</template>

<script setup lang="ts">
import { createDocumentResource, FormControl } from 'frappe-ui'
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import ObjectList from '../../components/ObjectList.vue'
import { getToastErrorMessage } from '../../utils/toast'
import ServerFirewallDialog from './ServerFirewallDialog.vue'

const props = defineProps<{
	id: string
}>()

const openAddDialog = ref(false)

const firewall = createDocumentResource({
	doctype: 'Server Firewall',
	name: props.id,
	auto: true,
	cache: ['Server', 'Firewall', props.id],
})

function save() {
	toast.promise(firewall.save.submit(), {
		loading: 'Saving firewall settings…',
		success: 'Firewall settings saved. They take a few minutes to apply.',
		error: (e) => getToastErrorMessage(e),
	})
}
</script>
