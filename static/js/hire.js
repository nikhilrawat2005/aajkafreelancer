// static/js/hire.js

document.addEventListener('DOMContentLoaded', function() {

const hireBtn = document.getElementById('hire-btn');

if(!hireBtn) return;

const conversationId = hireBtn.dataset.conversationId;

hireBtn.addEventListener("click", async () => {

hireBtn.disabled = true;

try{

const res = await fetch(`/chat/hire/request/${conversationId}`,{
method:"POST",
headers:{
"X-CSRFToken":window.CSRF_TOKEN
}
});

const data = await res.json();

if(data.success){

hireBtn.textContent = "Request Sent";
hireBtn.classList.remove("hire-default");
hireBtn.classList.add("hire-pending");

}else{

alert(data.error);
hireBtn.disabled = false;

}

}catch(err){

console.log(err);
hireBtn.disabled = false;

}

});

});
