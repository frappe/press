<!-- <template>
    <div>
        <label class="block"
        :class="{
            'pointer-events-none h-0.5 opacity-0': step!='Add Payment Details',
            'mt-4':step=='Add Payment Details'
        }">
        <span class="text-sm leading-4 text-gray-700">
                M-Pesa Payments
        </span>
        <ErrorMessage class="mt-1":message="paymentErrorMessage"/>
        </label>

        <div v-if="step == 'setting up M-Pesa'" class="mt-8 flex justify-center">
            <Spinner class="h-4 w-4 text-gray-600"/>

        </div>
        <ErrorMessage class="mt-2" :message="errorMessage"/>
        <div class="mt-4 flex w-full justify-between">
            <div></div>
            <div v-if="step=='Get Amount'">
                <Button
                variant="solid"
                @click="$resources.requestForPayment.submit()"
                :loading="$resources.requestForPayment.loading"
                >
                Proceed to payment using M-Pesa

                </Button>
            </div>

            <div v-if="step=='Add Payment Details'">
                <button
                class="ml-2"
                variant="solid"
                @click="onPayClick"
                :loading="paymentInProgress"
                >
                Make payment via M-Pesa
                </button>
            </div>

        </div>

    </div>
</template>

<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../utils/error';
export default {
    name:'BuyPrepaidCreditMpesa',
    props:{
        amount:{
            type:Number,
            required:true
        },
        minimumAmount:{
            type:Number,
            required:true,
            default: 10
        },
        partner:{
            type:String,
            required:true
        },
        phoneNumber:{
            type:String,
            required:true
        }
    },

    data(){
        return{
            step: 'Get Amount',
            paymentErrorMessage:null,
            errorMessage:null,
            paymentInProgress:false
        };
    },

    resources:{
        requestForPayment(){
            return{
                url: 'press.api.billing.request_for_payment',
                params:{
                    amount:this.amount,
                    phone_number:this.phoneNumber,
                    partner:this.partner
                },
                validate(){
                    if(this.amount < this.minimumAmount){
                        throw new DashboardError(`Amount is less than the minimum allowed: ${this.minimumAmount}`);
                    }
                },
                async onSuccess(data){
                    this.step='Add Payment Details';
                    toast.success(data.message || 'Please follow the instructions on your phone');
                }
            }
        }
    },

    methods:{
        async onPayClick(){
            this.paymentInProgress = true;
            try{
                // Assume backend is checking payment status here
                const response = await this.$resources.requestForPayment.submit();
                toast.success(response.data.message || 'Payment successful');
                this.$emit('success');
            }
            catch(error){
                this.paymentErrorMessage = error.message?.data?.message || 'Payment failed. Please try again.';
            }
            finally{
                this.paymentInProgress = false;
            }
        }

    }
}

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
        <label class="block"
        :class="{
            'pointer-events-none h-0.5 opacity-0': step!='Add Payment Details',
            'mt-4':step=='Add Payment Details'
        }">
        <span class="text-sm leading-4 text-gray-700">
                M-Pesa Payments
        </span>
        <ErrorMessage class="mt-1" :message="paymentErrorMessage"/>
        </label>

        <div v-if="step == 'setting up M-Pesa'" class="mt-8 flex justify-center">
            <Spinner class="h-4 w-4 text-gray-600"/>
        </div>

        <ErrorMessage class="mt-2" :message="errorMessage"/>

        <div class="mt-4 flex w-full justify-between">
            <div></div>
            <div v-if="step=='Get Amount'">
                <Button
                variant="solid"
                @click="$resources.requestForPayment.submit()"
                :loading="$resources.requestForPayment.loading"
                >
                Proceed to payment using M-Pesa
                </Button>
            </div>

            <div v-if="step=='Add Payment Details'">
                <button
                class="ml-2"
                variant="solid"
                @click="onPayClick"
                :loading="paymentInProgress"
                >
                Make payment via M-Pesa
                </button>
            </div>

        </div>

    </div>
</template>

<script>
import { toast } from 'vue-sonner';
import { DashboardError } from '../utils/error';
export default {
    name:'BuyPrepaidCreditMpesa',
    props:{
        amount:{
            type:Number,
            required:true
        },
        minimumAmount:{
            type:Number,
            required:true,
            default: 10
        },
        partner:{
            type:String,
            required:true
        },
        phoneNumber:{
            type:String,
            required:true
        }
    },

    data(){
        return{
            step: 'Get Amount',
            paymentErrorMessage:null,
            errorMessage:null,
            paymentInProgress:false
        };
    },

    resources:{
        requestForPayment(){
            return{
                url: 'press.api.billing.request_for_payment',
                params:{
                    amount:this.amount,
                    phone_number:this.phoneNumber,
                    partner:this.partner
                },
                validate(){
                    if(this.amount < this.minimumAmount){
                        throw new DashboardError(`Amount is less than the minimum allowed: ${this.minimumAmount}`);
                    }
                },
                async onSuccess(data){
                    this.step='Add Payment Details';
                    toast.success(data.message || 'Please follow the instructions on your phone');
                }
            }
        }
    },

    methods:{
        async onPayClick(){
            this.paymentInProgress = true;
            try{
                const response = await this.$resources.requestForPayment.submit();
                toast.success(response.data.message || 'Payment successful');
                this.$emit('success');
            }
            catch(error){
                this.paymentErrorMessage = error.message?.data?.message || 'Payment failed. Please try again.';
            }
            finally{
                this.paymentInProgress = false;
            }
        }

    }
}
</script>
