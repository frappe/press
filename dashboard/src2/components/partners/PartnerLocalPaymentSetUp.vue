<template>
    <div class="p-5">
        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
          
          <!-- Adding Mpesa Details -->
           
          <div v-if="$team.doc.country === 'Kenya'" class="flex flex-col gap-2 rounded-md border p-4">
            <div class="flex justify-between items-center text-sm text-gray-700">
              <div>Add M-Pesa Express Credentials</div>
              <Button @click="showAddMpesaDialog = true">Add</Button>
            </div>
            <div class="overflow-hidden text-ellipsis text-base font-medium">
              <span class="font-normal text-gray-600">Not set</span>
            </div>
          </div>
          <!-- End of M-Pesa Adding -->
  
          <AddMpesaCredentials v-model="showAddMpesaDialog" @closeDialog="showAddMpesaDialog = false" />
  
          <!-- Add Payment Gateway -->
          <div class="flex flex-col gap-2 rounded-md border p-4">
            <div class="flex justify-between items-center text-sm text-gray-700">
              <div>Add Payment Gateway</div>
              <Button @click="showAddPaymentGatewayDialog = true">Add</Button>
            </div>
            <div class="overflow-hidden text-ellipsis text-base font-medium">
              <span class="font-normal text-gray-600">Not set</span>
            </div>
          </div>
          <!-- End of Payment Gateway Adding -->
  
          <AddPaymentGateway v-model="showAddPaymentGatewayDialog" @closeDialog="showAddPaymentGatewayDialog = false" />

          <!--Add currency exchange-->
          <div class="flex flex-col gap-2 rounded-md border p-4">
            <div class="flex justify-between items-center text-sm text-gray-700">
              <div>Add Exchange Rate</div>
              <Button @click="showExchangeRateDialog = true">Add</Button>
            </div>
            <div class="overflow-hidden text-ellipsis text-base font-medium">
              <span class="font-normal text-gray-600">Not set</span>
            </div>
          </div>
          <!--End of Currency exchange-->

        <!-- Parent Component -->
        <AddExchangeRate v-model="showExchangeRateDialog" @closeDialog="showExchangeRateDialog = false" />

        <!--Submit Payment Transaction To Frappe-->
        <div class="flex flex-col gap-2 rounded-md border p-4">
            <div class="flex justify-between items-center text-sm text-gray-700">
              <div>Partner Payment Payout</div>
              <Button @click="showPartnerPaymentPayout = true">Add</Button>
            </div>
            <div class="overflow-hidden text-ellipsis text-base font-medium">
              <span class="font-normal text-gray-600">Not set</span>
            </div>
          </div>
          <!--End of payment transaction-->

        <!-- Parent Component -->
        <PartnerPaymentPayout v-model="showPartnerPaymentPayout" @closeDialog="showPartnerPaymentPayout = false" />
        </div>
      </div>
  
    
  </template>
  
  <script>
  import { defineAsyncComponent } from 'vue';
  
  export default {
    name: 'LocalPaymentSetUp',
    components: {
      AddMpesaCredentials: defineAsyncComponent(() =>
        import('../AddMpesaCredentials.vue')
      ),
      AddPaymentGateway: defineAsyncComponent(() =>
        import('../AddPaymentGateway.vue')
      ),
      AddExchangeRate: defineAsyncComponent(() =>
        import('../AddExchangeRate.vue')
      ),
      PartnerPaymentPayout: defineAsyncComponent(() =>
        import('../PartnerPaymentPayout.vue')
      ),
     
    },
    data() {
      return {
        showAddMpesaDialog: false,
        showAddPaymentGatewayDialog: false,
        showExchangeRateDialog:false,
        showPartnerPaymentPayout:false,
      };
    },
  
  };
  </script>
  