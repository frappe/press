import io from 'socket.io-client';

let host = window.location.hostname;
let port = window.location.port ? ':9000' : '';
let socket = io(`http://${host}${port}`);

export default socket;
