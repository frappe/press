<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()

import { createListResource } from 'frappe-ui'

const pipelines = createListResource({
	doctype: 'Release Pipeline',
	auto: true,
	fields: ['name', 'status', 'creation'],
})
</script>

<template>
  <div class='grid'>

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
	</router-link>
  </div>
</template>
