<template>
	<div class="w-1/2">
		<div v-if="!app.marketplace_app && !marketplaceApp">
			<Button type="primary" @click="showForm = true" v-show="!showForm">
				Publish to Marketplace
			</Button>
			<div v-if="showForm">
				<AvatarUploader
					:image.sync="publishFormValues.image"
					label="App Logo"
				/>
				<Form :fields="publishFormFields" v-model="publishFormValues" />
				<ErrorMessage class="mt-4" :error="$resources.publish.error" />
				<Button
					type="primary"
					class="mt-4"
					:loading="$resources.publish.loading"
					@click="$resources.publish.submit()"
				>
					Submit
				</Button>
			</div>
		</div>
		<div v-if="marketplaceApp">
			<div class="flex items-center mb-4 space-x-2">
				<Avatar
					:imageURL="marketplaceApp.image"
					:label="marketplaceApp.title"
				/>
				<h2 class="text-xl font-semibold ">{{ marketplaceApp.title }}</h2>
				<Badge>{{ marketplaceApp.status }}</Badge>
			</div>
			<Form :fields="publishFormFields" v-model="marketplaceApp" />
		</div>
	</div>
</template>
<script>
import Form from '@/components/Form';
import AvatarUploader from '@/components/AvatarUploader';

export default {
	name: 'AppMarketplace',
	props: ['app'],
	components: {
		Form,
		AvatarUploader
	},
	resources: {
		publish() {
			return {
				method: 'press.api.marketplace.publish',
				params: {
					app: this.app.name,
					values: this.publishFormValues
				},
				validate() {
					let requiredFields = this.publishFormFields
						.filter(df => df.required)
						.map(df => df.fieldname)
						.concat('image');

					if (requiredFields.some(field => !this.publishFormValues[field])) {
						return 'All fields are required';
					}
				},
				onSuccess() {
					this.$notify({
						title: 'Your app is in queue for approval.',
						icon: 'check',
						color: 'green'
					});
					this.showForm = false;
					this.$resources.marketplaceApp.reload();
				}
			};
		},
		categories: 'press.api.marketplace.categories',
		marketplaceApp() {
			return {
				method: 'press.api.marketplace.get',
				auto: this.app ? true : false,
				params: {
					app: this.app.name
				}
			};
		}
	},
	data() {
		return {
			showForm: false,
			publishFormValues: {
				title: this.app.name,
				description: '',
				image: '',
				long_description: ''
			}
		};
	},
	computed: {
		name() {
			return this.data;
		},
		marketplaceApp() {
			return this.$resources.marketplaceApp.data;
		},
		publishFormFields() {
			return [
				{
					fieldname: 'title',
					label: 'Title',
					fieldtype: 'Data',
					required: true
				},
				{
					fieldname: 'category',
					label: 'Category',
					fieldtype: 'Select',
					required: true,
					options: this.$resources.categories.data || []
				},
				{
					fieldname: 'description',
					label: 'Short Description',
					fieldtype: 'Data',
					required: true
				},
				{
					fieldname: 'long_description',
					label: 'Readme',
					fieldtype: 'Text',
					rows: 20,
					required: true
				}
			];
		}
	}
};
</script>
