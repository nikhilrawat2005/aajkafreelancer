// static/js/notifications.js

document.addEventListener('DOMContentLoaded', function() {

const badge = document.getElementById('notification-badge');
const list = document.getElementById('notification-list');

if(!badge) return;

async function updateNotifications(){

try{

const res = await fetch('/notifications/unread');

if(!res.ok) return;

const data = await res.json();

if(data.count > 0){

badge.textContent = data.count;
badge.style.display = "inline";

}else{

badge.style.display = "none";

}

if(list){

let html = "";

data.notifications.forEach(n=>{

if(n.type==="message"){

html += `<li><a class="dropdown-item" href="/chat/">New message</a></li>`;

}else{

html += `<li><span class="dropdown-item-text">${n.type}</span></li>`;

}

});

list.innerHTML = html || '<li><span class="dropdown-item-text">No notifications</span></li>';

}

}catch(e){

console.log(e);

}

}

updateNotifications();

setInterval(updateNotifications,20000);

});
