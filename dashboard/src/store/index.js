import Vue from 'vue';
import auth from './auth';

let store = Vue.observable({
	auth: new Vue(auth)
});

export default store;
