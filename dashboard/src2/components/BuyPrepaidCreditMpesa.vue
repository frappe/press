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
  
  <!--select-->
  
    <FormControl
    type="autocomplete"
    :options="teams" 
    size="sm"
    variant="subtle"
    placeholder="Select a partner"
    :disabled="false"
    label="Select Partner"
    v-model="partnerInput" 
    class="mb-5"
/>

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
<!--Show amount after tax-->
      <div v-if="showTaxInfo" >

      <div class="mt-4">
        <p class="text-sm leading-4 text-gray-700">Tax(%):</p>
        <p class="text-md text-red-500">{{ taxPercentage }}%</p>
      </div>
      
      <!--Tax percentage-->
      <div class="mt-4">
        <p class="text-sm leading-4 text-gray-700">Total Amount With Tax:</p>
        <p class="text-md text-red-500">Ksh. {{ amountWithTax }}</p>
      </div>

    </div>
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

        <ErrorMessage v-if="errorMessage" :message="errorMessage" />
    
  </template>
  
  <script>
  import { toast } from 'vue-sonner';
  import { DashboardError } from '../utils/error';
  import { ErrorMessage} from 'frappe-ui';
  import { frappeRequest } from 'frappe-ui';

  let request = options => {
    let _options = options || {};
    _options.headers = options.headers || {};

    // Example of setting team header
    let currentTeam = localStorage.getItem('current_team') || window.default_team;
    if (currentTeam) {
        _options.headers['X-Press-Team'] = currentTeam;
    }

    // Perform the request
    return frappeRequest(_options);
};

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
      partnerInput: '', 
      phoneNumberInput: '', 
      taxIdInput: '', 
      teams:[],
      taxPercentage:1,
      amountWithTax:0,
      showTaxInfo:false,
    };
  },

  resources: {
   requestForPayment() {
      return {
        url: 'press.api.billing.request_for_payment',
        params: {
          request_amount: this.amountKES, 
          sender: this.phoneNumberInput, 
          partner: this.partnerInput.value, 
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
  },

  methods: {
    request(options) {
      let _options = options || {};
      _options.headers = options.headers || {};

      let currentTeam = localStorage.getItem('current_team') || window.default_team;
      if (currentTeam) {
        _options.headers['X-Press-Team'] = currentTeam;
      }

      return frappeRequest(_options);
    },


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
},
async fetchTeams() {
        try {
            const response = await request({
                url: '/api/method/press.api.billing.display_mpesa_payment_partners',
                method: 'GET',
                
            });
            if (Array.isArray(response)) {
            this.teams = response; 
        } else {
            console.log("No Data");
        }
        } catch (error) {
            this.errorMessage = `Failed to fetch teams ${error.message}`;
        }
    },

    async fetchTaxPercentage(){
      try{
          const taxPercentage= await request({
            url: '/api/method/press.api.billing.get_tax_percentage',
            method: 'GET',
            params: {
              payment_partner: this.partnerInput.value
          }
          });
          console.log("Tax Percentage:", taxPercentage);
          this.taxPercentage = taxPercentage;
          
      }catch(error){
        this.errorMessage = `Failed to fetch tax percentage ${error.message}`;
      }
    },

   totalAmountWithTax(){
    console.log("nafoka")
    const amountWithTax= this.amountKES + (this.amountKES * (this.taxPercentage)/100);
    this.amountWithTax = amountWithTax;

}
  },
watch: {
  partnerInput: function(){
    this.fetchTaxPercentage();
    this.totalAmountWithTax();
    this.showTaxInfo = true;
  },
  amountKES: function(){
    this.totalAmountWithTax();
  }
},

mounted() {
  this.fetchTeams();
},

};
</script>
  

