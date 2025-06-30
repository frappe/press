<template>
	<div class="flex flex-col gap-4">
		<FormControl
			label="Website URL"
			type="data"
			name="website_url"
			v-model="domain"
		/>
		<FormControl
			label="Introduction"
			type="textarea"
			name="website_url"
			v-model="domain"
		/>
		<FormControl
			label="Customers"
			type="textarea"
			name="website_url"
			description="Customers should be separated by commas"
			placeholder="Tesla, Micro Corp, Ford"
			v-model="domain"
		/>
		<Button
			variant="solid"
			label="Update Website Info"
			@click="console.log('Update Website Info')"
		/>
	</div>
</template>
<script setup>
import { FormControl } from 'frappe-ui';
</script>
