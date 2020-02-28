import Vue from 'vue';
import auth from './auth';
import account from './account';
import socket from './socket';

let store = Vue.observable({
    auth: new Vue(auth),
    account: new Vue(account),
    socket
});

export default store;
