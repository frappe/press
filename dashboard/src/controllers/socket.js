import { io } from 'socket.io-client';

let host = window.location.hostname;
let port = window.location.port ? ':9000' : '';
let protocol = port ? 'http' : 'https';
let url = `${protocol}://${host}${port}`;
let socket = io(url, { withCredentials: true });

export default socket;
