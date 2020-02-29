import Vue from 'vue';
import auth from './auth';
import account from './account';
import sites from './sites';
import socket from './socket';

let store = Vue.observable({
    auth: new Vue(auth),
    account: new Vue(account),
    sites: new Vue(sites),
    socket
});

export default store;
