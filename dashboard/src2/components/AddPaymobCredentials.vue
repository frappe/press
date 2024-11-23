<template>
	<Dialog :class="showDialog" :options="{ title: 'Add Paymob Credentials', size: 'lg' }">
	  <template #body-content>
		<div class="grid grid-cols-2 gap-4">
		  <FormControl
			v-for="(field, index) in fields"
			:key="index"
			:label="field.label"
			v-model="field.model"
			:name="field.name"
			:type="field.type"
			:placeholder="field.placeholder"
			:required="field.required"
			:autocomplete="field.autocomplete"
			class="mb-2"
		  />
		</div>
  
		<div class="mt-4 flex w-full bg-red-300 items-center justify-center">
		  <Button @click="savePaymobCredentials" variant="solid" class="justify-center w-full font-bold">
			Save
		  </Button>
		</div>
	  </template>
	</Dialog>
  </template>
  
  <script>
  import { toast } from "vue-sonner";  
  
  export default {
	name: "AddPaymobCredentials",
	props: {
	  showDialog: {
		type: Boolean,
		required: true,
	  },
	},
	data() {
	  return {
		fields: [
		  {
			label: "API Key",
			model: this.apiKey,
			name: "api_key",
			type: "password",
			placeholder: "Enter API Key",
			required: true,
			autocomplete: "off",
		  },
		  {
			label: "Secret Key",
			model: this.secretKey,
			name: "secret_key",
			type: "password",
			placeholder: "Enter Secret Key",
			required: true,
			autocomplete: "off",
		  },
		  {
			label: "Public Key",
			model: this.publicKey,
			name: "public_key",
			type: "password",
			placeholder: "Enter Public Key",
			required: true,
			autocomplete: "off",
		  },
		  {
			label: "HMAC",
			model: this.hmac,
			name: "hmac",
			type: "password",
			placeholder: "Enter HMAC",
			required: true,
			autocomplete: "off",
		  },
		  {
			label: "Iframe Number",
			model: this.iframe,
			name: "iframe",
			type: "number",
			placeholder: "Enter Iframe ID",
			required: true,
			autocomplete: "off",
		  },
		  {
			label: "Payment Integration ID",
			model: this.paymentIntegration,
			name: "payment_integration",
			type: "number",
			placeholder: "Enter Payment Integration ID",
			required: true,
			autocomplete: "off",
		  },
		],
	  };
	},
	resources: {
        updatePaymobSettings(){
            return{
                url: "press.press.doctype.paymob_settings.paymob_settings.update_paymob_settings",
                params: this.mapFieldsToParams(),
				validate() {
                    this.validateFields()
                },

				async onSuccess(data) {
                    if(data){
						toast.success("Paymob Credentials saved", data);
						// reset the model
						for (let field of this.fields) {
							field.model = ""
						}
                    }else{
                        toast.error("Error Saving Paymob Credentials");
                    }
                }

            }
        }
    },
	methods: {
		validateFields() {
		for (let field of this.fields) {
		  if (field.required && !field.model) {
			toast.error(`${field.label} is required`);
			return false;
		  }
		}
		return true; 
		},
		mapFieldsToParams() {
			const params = {};
			this.fields.forEach((field) => {
				params[field.name] = field.model;
			});
			return params;
		},
	  async savePaymobCredentials() {
		// Validate all required fields before proceeding
		if (!this.validateFields()) return;
  
		try {
		  const response = await this.$resources.updatePaymobSettings.submit();
		  this.$emit("closeDialog");
		} catch (error) {
		  toast.error(`Error saving Paymob credentials: ${error.message}`);
		}
	  },
	},
  };
  </script>
  