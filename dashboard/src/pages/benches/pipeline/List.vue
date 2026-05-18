<script setup lang="ts">
import { useRoute } from 'vue-router'
import { date } from '@/utils/format'
const route = useRoute()

import { createListResource } from 'frappe-ui'

const pipelines = createListResource({
	doctype: 'Release Pipeline',
	auto: true,
	fields: ['name', 'status', 'creation'],
  orderBy: 'creation desc',
})
</script>

<template>
  <div class='grid gap-4'>

	<router-link
		v-for="pipeline in pipelines.data"
		:key="pipeline.name"
		:to="{
      name: 'Release Pipeline',
      params: {
        id: pipeline.name,
        name: route.params.name
      }
    }"
	>
		{{ pipeline.name }}

    {{ pipeline.status }}
    {{ date(pipeline.creation) }}
	</router-link>
  </div>
</template>
