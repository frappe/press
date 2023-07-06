
<template>
		<div class="wrapper" id="card_app">
		<div class="card-form">
		<div class="card-list">
			<div class="card-item" v-bind:class="{ '-active' : isCardFlipped }">
			<div class="card-item__side -front">
				<div class="card-item__focus" v-bind:class="{'-active' : focusElementStyle }" v-bind:style="focusElementStyle" ref="focusElement"></div>
				<div class="card-item__cover">
				<img
				v-bind:src="'https://raw.githubusercontent.com/muhammederdem/credit-card-form/master/src/assets/images/' + currentCardBackground + '.jpeg'" class="card-item__bg">
				</div>
				
				<div class="card-item__wrapper">
				<div class="card-item__top">
					<img src="https://raw.githubusercontent.com/muhammederdem/credit-card-form/master/src/assets/images/chip.png" class="card-item__chip">
					<div class="card-item__type">
					<transition name="slide-fade-up">
						<img v-bind:src="'https://raw.githubusercontent.com/muhammederdem/credit-card-form/master/src/assets/images/' + getCardType + '.png'" v-if="getCardType" v-bind:key="getCardType" alt="" class="card-item__typeImg">
					</transition>
					</div>
				</div>
				
				<label for="cardNumber" class="card-item__number" ref="cardNumber">
                <template v-if="getCardType === 'amex'">
                 <span v-for="(n, $index) in amexCardMask" :key="$index">
                  <transition name="slide-fade-up">
                    <div
                      class="card-item__numberItem"
                      v-if="$index > 4 && $index < 14 && cardNumber.length > $index && n.trim() !== ''"
                    >*</div>
                    <div class="card-item__numberItem"
                      :class="{ '-active' : n.trim() === '' }"
                      :key="$index" v-else-if="cardNumber.length > $index">
                      {{cardNumber[$index]}}
                    </div>
                    <div
                      class="card-item__numberItem"
                      :class="{ '-active' : n.trim() === '' }"
                      v-else
                      :key="$index + 1"
                    >{{n}}</div>
                  </transition>
                </span>
                </template>

                <template v-else>
                  <span v-for="(n, $index) in otherCardMask" :key="$index">
                    <transition name="slide-fade-up">
                      <div
                        class="card-item__numberItem"
                        v-if="$index > 4 && $index < 15 && cardNumber.length > $index && n.trim() !== ''"
                      >*</div>
                      <div class="card-item__numberItem"
                        :class="{ '-active' : n.trim() === '' }"
                        :key="$index" v-else-if="cardNumber.length > $index">
                        {{cardNumber[$index]}}
                      </div>
                      <div
                        class="card-item__numberItem"
                        :class="{ '-active' : n.trim() === '' }"
                        v-else
                        :key="$index + 1 - 1"
                      >{{n}}</div>
                    </transition>
                  </span>
                </template>
              </label>
				<div class="card-item__content">
					<label for="cardName" class="card-item__info" ref="cardName">
					<div class="card-item__holder">Card Holder Name</div>
					<transition name="slide-fade-up">
						<div class="card-item__name" v-if="cardName.length" key="1">
						<transition-group name="slide-fade-right">
							<span class="card-item__nameItem" v-for="(n, $index) in cardName.replace(/\s\s+/g, ' ')" v-if="$index === $index" v-bind:key="$index + 1">{{n}}</span>
						</transition-group>
						</div>
						<div class="card-item__name" v-else key="2">Full Name</div>
					</transition>
					</label>
					<div class="card-item__date" ref="cardDate">
					<label for="cardMonth" class="card-item__dateTitle">Expires</label>
					<label for="cardMonth" class="card-item__dateItem">
						<transition name="slide-fade-up">
						<span v-if="cardMonth" v-bind:key="cardMonth">{{cardMonth}}</span>
						<span v-else key="2">MM</span>
						</transition>
					</label>
					/
					<label for="cardYear" class="card-item__dateItem">
						<transition name="slide-fade-up">
						<span v-if="cardYear" v-bind:key="cardYear">{{String(cardYear).slice(2,4)}}</span>
						<span v-else key="2">YY</span>
						</transition>
					</label>
					</div>
				</div>
				</div>
			</div>
			<div class="card-item__side -back">
				<div class="card-item__cover">
				<img
				v-bind:src="'https://raw.githubusercontent.com/muhammederdem/credit-card-form/master/src/assets/images/' + currentCardBackground + '.jpeg'" class="card-item__bg">
				</div>
				<div class="card-item__band"></div>
				<div class="card-item__cvv">
					<div class="card-item__cvvTitle">CVV</div>
					<div class="card-item__cvvBand">
					<span v-for="(n, $index) in cardCvv" :key="$index">
						*
					</span>

				</div>
					<div class="card-item__type">
						<img v-bind:src="'https://raw.githubusercontent.com/muhammederdem/credit-card-form/master/src/assets/images/' + getCardType + '.png'" v-if="getCardType" class="card-item__typeImg">
					</div>
				</div>
			</div>
			</div>
		</div>
		<div class="card-form__inner">
			<div class="card-input">
			<label for="cardNumber" class="card-input__label">Card Number</label>
			<input type="text" id="cardNumber" class="card-input__input" v-mask="generateCardNumberMask" v-model="cardNumber" v-on:focus="focusInput" v-on:blur="blurInput" data-ref="cardNumber" autocomplete="off">
			
			</div>
			<div class="card-input">
			<label for="cardName" class="card-input__label">Card Holders Name</label>
			<input type="text" id="cardName" class="card-input__input" v-model="cardName" v-on:focus="focusInput" v-on:blur="blurInput" data-ref="cardName" autocomplete="off">
			</div>
			<div class="card-form__row">
			<div class="card-form__col">
				<div class="card-form__group">
				<label for="cardMonth" class="card-input__label">Expiration Date</label>
				<select class="card-input__input -select" id="cardMonth" v-model="cardMonth" v-on:focus="focusInput" v-on:blur="blurInput" data-ref="cardDate">
					<option value="" disabled selected>Month</option>
					<option v-bind:value="n < 10 ? '0' + n : n" v-for="n in 12" v-bind:disabled="n < minCardMonth" v-bind:key="n">
						{{n < 10 ? '0' + n : n}}
					</option>
				</select>
				<select class="card-input__input -select" id="cardYear" v-model="cardYear" v-on:focus="focusInput" v-on:blur="blurInput" data-ref="cardDate">
					<option value="" disabled selected>Year</option>
					<option v-bind:value="$index + minCardYear" v-for="(n, $index) in 12" v-bind:key="n">
						{{$index + minCardYear}}
					</option>
				</select>
				</div>
			</div>
			<div class="card-form__col -cvv">
				<div class="card-input">
				<label for="cardCvv" class="card-input__label">CVV</label>
				<input type="text" class="card-input__input" id="cardCvv" v-mask="'####'" maxlength="4" v-model="cardCvv" v-on:focus="flipCard(true)" v-on:blur="flipCard(false)" autocomplete="off">
				</div>
			</div>
			</div>

			<button class="card-form__button"  @click="get_midtrans_card_token" :loading="addingCard">
			Save Card
			</button>
		</div>
		</div>
		
	</div>

</template>

<script>
	/*
See on github: https://github.com/muhammederdem/credit-card-form
*/

export default {
	name: 'MidTransCard',
	props: ['withoutAddress'],
	emits: ['complete'],
	data() {
		return {
		currentCardBackground: Math.floor(Math.random()* 25 + 1), // just for fun :D
		cardName: "",
		cardNumber: "",
		cardMonth: "",
		cardYear: "",
		cardCvv: "",
		minCardYear: new Date().getFullYear(),
		amexCardMask: "#### ###### #####",
		otherCardMask: "#### #### #### ####",
		cardNumberTemp: "",
		isCardFlipped: false,
		focusElementStyle: null,
		isInputFocused: false,
		addingCard : false
		};
	},
	async mounted() {
		this.cardNumberTemp = this.otherCardMask;
		document.getElementById("cardNumber").focus();

		let client_key = await this.$call(
			'optibizpro.utils.get_client_key'
		);
		//add midtrans js checkout
		const midtransCheckoutJS = document.createElement('script');
		midtransCheckoutJS.setAttribute(
			'src',
			'https://api.midtrans.com/v2/assets/js/midtrans-new-3ds.min.js'
		);
		midtransCheckoutJS.setAttribute(
			'id',
			'midtrans-script'
		);
		midtransCheckoutJS.setAttribute(
			'data-environment',
			"production"
		);
		midtransCheckoutJS.setAttribute(
			'data-client-key',
			client_key
		);
		
		midtransCheckoutJS.async = true;
		document.head.appendChild(midtransCheckoutJS);
	},
	computed: {
		getCardType () {
		let number = this.cardNumber;
		let re = new RegExp("^4");
		if (number.match(re) != null) return "visa";

		re = new RegExp("^(34|37)");
		if (number.match(re) != null) return "amex";

		re = new RegExp("^5[1-5]");
		if (number.match(re) != null) return "mastercard";

		re = new RegExp("^6011");
		if (number.match(re) != null) return "discover";
		
		re = new RegExp('^9792')
		if (number.match(re) != null) return 'troy'

		// re = new RegExp('^3(?:0([0-5]|9)|[689]\\d?)\\d{0,11}')
		// if (number.match(re) != null) return 'dinersclub'

		// re = new RegExp('^35(2[89]|[3-8])')
		// if (number.match(re) != null) return 'jcb'

		return "visa"; // default type
		},
			generateCardNumberMask () {
				return this.getCardType === "amex" ? this.amexCardMask : this.otherCardMask;
		},
		minCardMonth () {
		if (this.cardYear === this.minCardYear) return new Date().getMonth() + 1;
		return 1;
		}
	},
	watch: {
		cardYear () {
		if (this.cardMonth < this.minCardMonth) {
			this.cardMonth = "";
		}
		}
	},
	methods: {
		flipCard (status) {
		this.isCardFlipped = status;
		},
		focusInput (e) {
		this.isInputFocused = true;
		let targetRef = e.target.dataset.ref;
		let target = this.$refs[targetRef];
		this.focusElementStyle = {
			width: `${target.offsetWidth}px`,
			height: `${target.offsetHeight}px`,
			transform: `translateX(${target.offsetLeft}px) translateY(${target.offsetTop}px)`
		}
		},
		blurInput() {
		let vm = this;
		setTimeout(() => {
			if (!vm.isInputFocused) {
			vm.focusElementStyle = null;
			}
		}, 300);
		vm.isInputFocused = false;
		},
		get_midtrans_card_token(){
			var cardData = {
				"card_number": this.cardNumber,
				"card_exp_month": this.cardMonth,
				"card_exp_year": this.cardYear,
				"card_cvv": this.cardCvv,
			};

			var options = {
				onSuccess:(response)=>{
					// Success to get card token_id, implement as you wish here
					this.addingCard = true
					var token_id = response.token_id;

					
					response["team"] = this.$account.team.name
					this.$resources.CreatePaymentMethod.submit({response});
					this.$emit('complete');

					// Implement sending the token_id to backend to proceed to next step
				},
				onFailure: function(response){
					// Fail to get card token_id, implement as you wish here
					console.log('Fail to get card token_id, response:', response);

					// you may want to implement displaying failure message to customer.
					// Also record the error message to your log, so you can review
					// what causing failure on this transaction.
					}
			};
			console.log(cardData)
			MidtransNew3ds.getCardToken(cardData, options);

		},
		filterNonNumeric() {
			// Replace non-numeric characters with an empty string
			
			// this.cardNumber = this.cardNumber.replace(/[^0-9]/g, "");
		}

	},
	resources : {
		CreatePaymentMethod() {
			return {
				method: 'optibizpro.utils.create_midtrans_payment_method',
				onSuccess() {
					this.$emit('success');
				}
			};
		},
	}
}

</script>

<style scoped src="../assets/card.scss">
/* @import '../assets/css/startpage.css'; */
	
</style>