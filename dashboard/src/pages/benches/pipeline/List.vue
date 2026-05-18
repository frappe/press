<script setup lang="ts">
import { useRoute } from 'vue-router'
<<<<<<< HEAD
<<<<<<< HEAD
import { date } from '@/utils/format'
<<<<<<< HEAD
import { createListResource } from 'frappe-ui'

const route = useRoute()

const pipelines = createListResource({
	doctype: 'Release Pipeline',
	auto: true,
	fields: ['name', 'status', 'creation', 'duration', 'release_group'],
	filters: {
		release_group: route.params.name,
	},
	orderBy: 'creation desc',
=======
=======
import { date } from '@/utils/format'
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
const route = useRoute()

=======
>>>>>>> 7f92d4e83 (fix(deploy-ui): add badge status colors)
import { createListResource } from 'frappe-ui'

const route = useRoute()

const pipelines = createListResource({
	doctype: 'Release Pipeline',
	auto: true,
<<<<<<< HEAD
	fields: ['name', 'status', 'creation'],
<<<<<<< HEAD
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
  orderBy: 'creation desc',
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
=======
	fields: ['name', 'status', 'creation', 'duration'],
	orderBy: 'creation desc',
>>>>>>> 7f92d4e83 (fix(deploy-ui): add badge status colors)
})
</script>

<template>
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> 7f92d4e83 (fix(deploy-ui): add badge status colors)
	<div class="grid gap-4">
		<table class="w-full">
			<thead class="text-left">
				<tr class="bg-surface-gray-2 *:p-2 *:font-normal text-ink-gray-4">
					<th class="rounded-l">Created</th>
					<th class="rounded-r">Status</th>
				</tr>
			</thead>
<<<<<<< HEAD

			<br />
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
=======
  <div class='grid'>
=======
  <div class='grid gap-4'>
>>>>>>> 60209a727 (fix(new-deploy-ui): add missing socket events)
=======
>>>>>>> 7f92d4e83 (fix(deploy-ui): add badge status colors)

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

<<<<<<< HEAD
    {{ pipeline.status }}
    {{ date(pipeline.creation) }}
	</router-link>
  </div>
>>>>>>> 699d08889 (refactor(deploy-ui): include layout components)
=======
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
>>>>>>> 7f92d4e83 (fix(deploy-ui): add badge status colors)
</template>
