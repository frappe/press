<!-- <template>

// Make an API call to the backend to initiate the M-Pesa payment
// The backend will return a URL to redirect the user to
// The URL will contain the payment details
// The user will be redirected to the M-Pesa payment page
// The user will be prompted to enter their M-Pesa PIN
// The user will receive a confirmation message from M-Pesa
// The user will be redirected back to the platform
// The user will receive a confirmation message from the platform
// The user will receive a confirmation email from the platform
</script>
-->

<template>
    <div>
      <label class="block mt-4">
        <span class="text-sm leading-4 text-gray-700">
          <!-- M-Pesa Payments -->
        </span>
        <ErrorMessage class="mt-1" :message="paymentErrorMessage" />
      </label>
  
      <ErrorMessage class="mt-2" :message="errorMessage" />
  
        <!-- Select field for Partner -->
     <!-- Select field for Partner -->
     <label for="partner" class="block mb-2 text-sm text-gray-700">Partner</label>
    <select 
      id="partner" 
      v-model="partnerInput" 
      class="form-select w-full mb-6">
      <option disabled value="">Select a partner</option>
      <option v-for="partner in partners" :key="partner" :value="partner">
        {{ partner }}
      </option>
    </select>

  
      <!-- Input field for M-Pesa Phone Number using FormControl -->
      <FormControl
        label="M-Pesa Phone Number"
        v-model.number="phoneNumberInput"
        name="phone_number"
        autocomplete="off"
        class="mb-5"
        type="tel"
        placeholder="Enter phone number"
      >
        <template #prefix>
          <div class="grid w-4 place-items-center text-sm text-gray-700">
            <!-- Prefix could be optional if needed -->
          </div>
        </template>
      </FormControl>
  
       <!-- Input field for Customer Tax Id using FormControl -->
       <FormControl
        label="Tax ID"
        v-model="taxIdInput"
        name="tax_id"
        autocomplete="off"
        class="mb-5"
        type="string"
        placeholder="Enter company's Tax ID"
      >
        <template #prefix>
          <div class="grid w-4 place-items-center text-sm text-gray-700">
            <!-- Prefix could be optional if needed -->
          </div>
        </template>
      </FormControl>

      <!-- Button to make payment -->
      <div class="mt-4 flex w-full justify-end">
        <Button
          variant="solid"
          @click="onPayClick"
          :loading="paymentInProgress"
        >
          Make payment via M-Pesa
        </Button>
      </div>
    </div>
  </template>
  
  <script>
  import { toast } from 'vue-sonner';
  import { DashboardError } from '../utils/error';

  export default {
    name: 'BuyPrepaidCreditMpesa',
    props: {
      amount: {
        type: Number,
        required: true
      },
      amountKES:{
        type: Number,
        required: true,
        default:1
      },
      minimumAmount: {
        type: Number,
       
        required: true,
      default: 10
    }
  },

  data() {
    return {
      paymentErrorMessage: null,
      errorMessage: null,
      paymentInProgress: false,
      partnerInput: '', // initialize partner input
      phoneNumberInput: '', // initialize phone number input
      taxIdInput: '', // initialize tax id input
      partners: ['Administrator', 'Partner B', 'Partner C'] // Dummy data for partners
    };
  },

  // async mounted(){
  //   try{

  //       await this.$resources.fetchMpesaPartners.load();
  //   }catch(error){
  //     this.errorMessage = error.message || 'Failed to load partners details';
  //   }
  // },

  resources: {
    requestForPayment() {
      return {
        url: 'press.api.billing.request_for_payment',
        params: {
          request_amount: this.amountKES, // use amount in KES
          sender: this.phoneNumberInput, // use input value for phone number
          partner: this.partnerInput, // use input value for partner
          tax_id:this.taxIdInput
        },
        validate() {
          if (this.amount < this.minimumAmount) {
            throw new DashboardError(
              `Amount is less than the minimum allowed: ${this.minimumAmount}`
            );
          }
          if (!this.partnerInput || !this.phoneNumberInput) {
            throw new DashboardError(
              'Both partner and phone number are required for payment.'
            );
          }
        },
        async onSuccess(data) {
           if (data?.ResponseCode === '0') {
    toast.success(data.ResponseDescription || 'Please follow the instructions on your phone');
  } else {
    toast.error(data.ResponseDescription || 'Something went wrong. Please try again.');
  }
        }
      };
    },

    // fetchMpesaPartners(){
    //   return{
    //     url: 'press.api.billing.display_mpesa_payment_partners',
    //     async onSuccess(data){
    //       this.partners = data || [];
    //     },
    //     validate(){
    //       // No validation needed
    //     }
    //   };
      
    // }
  },

  methods: {
    async onPayClick() {
  this.paymentInProgress = true;
  try {
    const response = await this.$resources.requestForPayment.submit();
    console.log("Response Data:", response);

    if (response.ResponseCode === '0') {
      toast.success(response.Success || 'Payment Initiated successfully, check your phone for instructions');
      this.$emit('success');
    } else {
      console.log("Payment Error:", response.ResponseDescription);
      throw new Error(response.ResponseDescription || 'Payment failed');
    }
  } catch (error) {
    this.paymentErrorMessage = error.message || 'Payment failed. Please try again.';
    toast.error(this.paymentErrorMessage);
  } finally {
    this.paymentInProgress = false;
  }
}

}

};
</script>
  