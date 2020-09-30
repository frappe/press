<template>
	<div class="w-1/2">
		<div v-if="!app.marketplace_app && !marketplaceApp">
			<Button type="primary" @click="showForm = true" v-show="!showForm">
				Publish to Marketplace
			</Button>
			<div v-if="showForm">
				<AvatarUploader
					:image.sync="submissionFormValues.image"
					label="App Logo"
				/>
				<Form :fields="submissionFormFields" v-model="submissionFormValues" />
				<ErrorMessage class="mt-4" :error="$resources.submit.error" />
				<Button
					type="primary"
					class="mt-4"
					:loading="$resources.submit.loading"
					@click="$resources.submit.submit()"
				>
					Submit
				</Button>
			</div>
		</div>
		<div v-if="marketplaceApp">
			<Alert v-if="marketplaceApp.status == 'Draft'">
				Your app is queued for approval. You will be notified when your app is
				approved.
			</Alert>
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
		submit() {
			return {
				method: 'press.api.marketplace.submit',
				params: {
					app: this.app.name,
					values: this.submissionFormValues
				},
				validate() {
					let requiredFields = this.submissionFormFields.filter(
						df => df.required
					);

					if (
						requiredFields
							.map(df => df.fieldname)
							.some(field => !this.submissionFormValues[field])
					) {
						return `${requiredFields
							.map(df => df.label)
							.join(', ')} fields are required`;
					}

					let toValidate = this.submissionFormFields.filter(df => df.validate);

					for (let df of toValidate) {
						let value = this.submissionFormValues[df.fieldname];
						let error = df.validate(value);
						if (error) {
							return df.label + ': ' + error;
						}
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
			submissionFormValues: {
				title: this.app.name,
				description: '',
				image: '',
				long_description: '',
				website: '',
				privacy_policy: '',
				documentation: '',
				terms_of_service: '',
				support: ''
			}
		};
	},
	computed: {
		name() {
			return this.data;
		},
		marketplaceApp() {
			return this.$resources.marketplaceApp?.data;
		},
		badgeColor() {
			if (!this.marketplaceApp) return;

			return {
				Published: 'green',
				Approved: 'blue',
				Draft: 'orange'
			}[this.marketplaceApp.status];
		},
		submissionFormFields() {
			let urlValidator = value => {
				if (!value) return;
				let regExp = /^(https?|s?ftp):\/\/(((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:)*@)?(((\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5]))|((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.?)(:\d*)?)(\/((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)+(\/(([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)*)*)?)?(\?((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)|[\uE000-\uF8FF]|\/|\?)*)?(#((([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(%[\da-f]{2})|[!\$&'\(\)\*\+,;=]|:|@)|\/|\?)*)?$/i;
				if (!regExp.test(value)) {
					return 'Invalid URL';
				}
			};
			return [
				{
					fieldname: 'title',
					label: 'App Name',
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
					fieldname: 'website',
					label: 'Public Website',
					placeholder: 'https://example.com',
					validate: urlValidator,
					fieldtype: 'Data',
					required: true
				},
				{
					fieldname: 'support',
					label: 'Support',
					placeholder: 'https://example.com/support',
					validate: urlValidator,
					fieldtype: 'Data'
				},
				{
					fieldname: 'privacy_policy',
					label: 'Privacy Policy',
					placeholder: 'https://example.com/privacy-policy',
					validate: urlValidator,
					fieldtype: 'Data'
				},
				{
					fieldname: 'documentation',
					label: 'Documentation',
					placeholder: 'https://example.com/docs',
					validate: urlValidator,
					fieldtype: 'Data'
				},
				{
					fieldname: 'terms_of_service',
					label: 'Terms of Service',
					placeholder: 'https://example.com/terms',
					validate: urlValidator,
					fieldtype: 'Data'
				}
			];
		}
	}
};
</script>
