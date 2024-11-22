<template>
    <Dialog :class="showDialog" :options="{ title: 'Fetch Partner Payments', size: 'lg' }">
      <template #body-content>
        <div class="grid grid-cols-2 gap-4">
          <!-- Filters -->
          <FormControl
            label="Payment Gateway"
            v-model="paymentGateway"
            name="payment_gateway"
            autocomplete="off"
            class="mb-5"
            type="text"
            placeholder="Enter Payment Gateway"
          />
  
          <FormControl
            label="Partner"
            v-model="partner"
            name="partner"
            autocomplete="off"
            class="mb-5"
            type="text"
            placeholder="Enter Partner"
          />
  
          <FormControl
            label="From Date"
            v-model="fromDate"
            name="from_date"
            autocomplete="off"
            class="mb-5"
            type="date"
            placeholder="Select Start Date"
          />
  
          <FormControl
            label="To Date"
            v-model="toDate"
            name="to_date"
            autocomplete="off"
            class="mb-5"
            type="date"
            placeholder="Select End Date"
          />
  
          <Button
            @click="fetchPayments"
            variant="solid"
            class="justify-center col-span-2 font-bold"
          >
            Fetch Payments
          </Button>
        </div>
  
        <!-- Results Table -->
        <div v-if="payments.length > 0" class="mt-5">
          <table class="w-full border-collapse border border-gray-300">
            <thead>
              <tr>
                <th class="border border-gray-300 p-2">Transaction ID</th>
                <th class="border border-gray-300 p-2">Amount</th>
                <th class="border border-gray-300 p-2">Posting Date</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="payment in payments" :key="payment.name">
                <td class="border border-gray-300 p-2">{{ payment.name }}</td>
                <td class="border border-gray-300 p-2">{{ payment.amount }}</td>
                <td class="border border-gray-300 p-2">{{ payment.posting_date }}</td>
              </tr>
            </tbody>
          </table>
        </div>
  
        <div v-if="payments.length === 0 && fetchAttempted" class="text-center mt-4 text-gray-500">
          No payments found.
        </div>
      </template>
    </Dialog>
  </template>
  
  <script>
  import { toast } from 'vue-sonner';
  
  export default {
    name: 'PartnerPaymentPayout',
    props: {
      showDialog: {
        type: Boolean,
        required: true,
      },
    },
    data() {
      return {
        paymentGateway: '',
        partner: '',
        fromDate: '',
        toDate: '',
        payments: [],
        fetchAttempted: false,
      };
    },
    methods: {
      async fetchPayments() {
        try {
          this.fetchAttempted = true;
          const response = await this.$axios.get('/api/method/press.api.fetch_payments', {
            params: {
              payment_gateway: this.paymentGateway,
              partner: this.partner,
              from_date: this.fromDate,
              to_date: this.toDate,
            },
          });
  
          if (response.data && response.data.message) {
            this.payments = response.data.message;
            toast.success('Payments fetched successfully!');
          } else {
            this.payments = [];
            toast.error('No payments found.');
          }
        } catch (error) {
          toast.error(`Error fetching payments: ${error.message}`);
        }
      },
    },
  };
  </script>
  
  <style scoped>
  table {
    width: 100%;
    text-align: left;
    margin-top: 1rem;
  }
  th,
  td {
    padding: 8px 12px;
  }
  </style>
  