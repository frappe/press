<script setup lang="ts">
import { useRoute } from 'vue-router'
import { date } from '@/utils/format'
import { createListResource } from 'frappe-ui'

const route = useRoute()

const pipelines = createListResource({
	doctype: 'Release Pipeline',
	auto: true,
	fields: ['name', 'status', 'creation', 'duration'],
	orderBy: 'creation desc',
})
</script>

<template>
	<div class="grid gap-4">
		<table class="w-full">
			<thead class="text-left">
				<tr class="bg-surface-gray-2 *:p-2 *:font-normal text-ink-gray-4">
					<th class="rounded-l">Created</th>
					<th class="rounded-r">Status</th>
				</tr>
			</thead>

      <br/>
			<tbody>
				<tr
					v-for="pipeline in pipelines.data || []"
					:key="pipeline.name"
					class="hover:bg-surface-gray-1"
				>
					<td class="p-2">
						<router-link
							class="block w-full"
							:to="{
								name: 'Release Pipeline',
								params: {
									id: pipeline.name,
									name: route.params.name
								}
							}"
						>
							{{ date(pipeline.creation) }}
						</router-link>
					</td>

					<td class="p-2">
						<router-link
							class="block w-full"
							:to="{
								name: 'Release Pipeline',
								params: {
									id: pipeline.name,
									name: route.params.name
								}
							}"
						>
							{{ pipeline.status }}
						</router-link>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>
