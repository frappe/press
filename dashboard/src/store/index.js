import Vue from 'vue';
import auth from './auth';
import socket from './socket';

let store = Vue.observable({
    auth: new Vue(auth),
    socket
});

export default store;
