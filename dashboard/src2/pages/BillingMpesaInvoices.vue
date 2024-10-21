<template>
    <div>
      <div v-if="invoices && invoices.length" class="overflow-x-auto">
    
        <table class="text w-full border-separate border-spacing-y-2 text-base font-normal text-gray-900">
          <thead class="bg-gray-100">
            <tr class="text-gray-600">
              <th class="rounded-l p-2 text-left font-normal">Invoice Name</th>
              <th class="p-2 text-left font-normal">Date</th>
              <th class="p-2 text-left font-normal">Amount</th>
              <th class="rounded-r p-2 text-left font-normal">Download Invoice</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="invoice in invoices" :key="invoice.name" class="bg-gray-50">
              <td class="p-2">{{ invoice.name }}</td>
              <td class="p-2">{{ invoice.posting_date }}</td>
              <td class="p-2">{{ formatCurrency(invoice.trans_amount) }}</td>
              <td class="p-2">
                <a :href="invoice.local_invoice" target="_blank" class="text-blue-600 hover:underline">View Invoice</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="py-20 text-center" v-if="loading">
        <Button :loading="true">Loading...</Button>
      </div>
      <ErrorMessage v-if="errorMessage" :message="errorMessage" />
    </div>
  </template>
  
  <script>
  import { ErrorMessage } from 'frappe-ui';
  import { frappeRequest } from 'frappe-ui';
  
  export default {
    name: 'BillingMpesaInvoices',
    data() {
      return {
        invoices: [],
        loading: false,
        errorMessage: null,
      };
    },
    methods: {
       
      async fetchInvoices() {
        this.loading = true;
  
        try {
          const response = await frappeRequest({
            url: '/api/method/press.api.billing.display_invoices_by_partner',
            method: 'GET',
          });
          this.invoices = response;
        } catch (error) {
          this.errorMessage = `Failed to load invoices. ${error}`;
        } finally {
          this.loading = false;
        }
      },
      formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'Ksh',
        }).format(value);
      }
    },
    mounted() {
      this.fetchInvoices();
    }
  };
  </script>
  