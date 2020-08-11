<template>
	<Dialog title="Update GSTIN" v-model="show" :dismissable="false">
		<p class="text-base">
			As an Indian customer, if you have a registered GSTIN number, you are
			required to update it, so that we can use it to generate a GST Invoice.
		</p>
		<Input class="mt-4" type="text" label="GSTIN" v-model="gstin" />
		<ErrorMessage class="mt-2" :error="$resources.updateGstin.error" />
		<Button slot="actions" class="mr-2" @click="notApplicable">
			I don't have a GSTIN
		</Button>
		<Button
			type="primary"
			slot="actions"
			@click="$resources.updateGstin.submit()"
			:loading="$resources.updateGstin.loading"
		>
			Update GSTIN
		</Button>
	</Dialog>
</template>

<script>
import { validateGST } from '@/utils';

const Not_Applicable = 'Not Applicable';

export default {
	name: 'UpdateGSTIN',
	data() {
		return {
			show: true,
			gstin: null
		};
	},
	resources: {
		updateGstin() {
			return {
				method: 'press.api.account.update_gstin',
				params: {
					gstin: this.gstin
				},
				validate() {
					if (this.gstin === 'Not Applicable') {
						return;
					}
					if (!this.gstin) {
						return 'GSTIN cannot be blank';
					}
					if (!validateGST(this.gstin)) {
						return 'Invalid GSTIN';
					}
				},
				onSuccess() {
					this.show = false;
					if (this.gstin != Not_Applicable) {
						this.$notify({
							title: 'GSTIN Updated Successfully'
						});
					}
				}
			};
		}
	},
	methods: {
		notApplicable() {
			this.gstin = Not_Applicable;
			this.$resources.updateGstin.submit();
		}
	}
};
</script>
