const socket = io();

const messageContainer = document.getElementById("message-container");
const messageForm = document.getElementById("message-form");
const messageInput = document.getElementById("message-input");
const typingIndicator = document.getElementById("typing-indicator");

socket.emit("join",{
conversation_id:conversationId
});

messageForm.addEventListener("submit",(e)=>{

e.preventDefault();

const text = messageInput.value.trim();

if(!text) return;

socket.emit("send_message",{
conversation_id:conversationId,
message:text
});

messageInput.value="";

});

socket.on("new_message",(msg)=>{

const wrapper=document.createElement("div");

wrapper.className="mb-2 d-flex "+(
msg.sender==currentUserId
?"justify-content-end"
:"justify-content-start"
);

wrapper.innerHTML=`
<div class="d-inline-block p-2 rounded"
style="max-width:70%;
background-color:${msg.sender==currentUserId?'var(--pastel-sky)':'var(--pastel-mint)'};
border:2px solid black;
border-radius:20px 5px 20px 5px;">

${msg.text}

<small class="text-muted d-block">
${msg.timestamp}
</small>

</div>
`;

messageContainer.appendChild(wrapper);

messageContainer.scrollTop=messageContainer.scrollHeight;

});

messageInput.addEventListener("input",()=>{

socket.emit("typing",{
conversation_id:conversationId
});

});

socket.on("typing",()=>{

typingIndicator.innerText="typing...";

setTimeout(()=>{
typingIndicator.innerText="";
},1000);

});