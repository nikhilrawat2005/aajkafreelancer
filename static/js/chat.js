// static/js/chat.js – Firebase Firestore realtime chat

(function () {

  const db = firebase.firestore();
  const auth = firebase.auth();

  // Ensure user is signed in to Firebase (for Firestore access)
  async function ensureFirebaseAuth() {
    if (auth.currentUser) return true;
    try {
      const resp = await fetch('/auth/firebase-token', { credentials: 'same-origin' });
      const data = await resp.json();
      if (data.token) {
        await auth.signInWithCustomToken(data.token);
        return true;
      }
    } catch (e) {
      console.error('Firebase auth failed:', e);
    }
    return false;
  }

  function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // =========================================================
  // CHAT ROOM
  // =========================================================

  async function initChatRoom() {
    const container = document.getElementById("message-container");
    const form = document.getElementById("message-form");
    const input = document.getElementById("message-input");
    const conversationId = window.CONVERSATION_ID;
    const currentUserId = window.CURRENT_USER_ID;

    if (!container || !form || !conversationId) return;

    const ok = await ensureFirebaseAuth();
    if (!ok) {
      container.innerHTML = '<p class="text-danger">Unable to load chat. Please sign in again.</p>';
      return;
    }

    const messagesRef = db.collection("conversations").doc(conversationId).collection("messages");
    const convRef = db.collection("conversations").doc(conversationId);

    function renderMessage(msg) {
      if (document.getElementById(`msg-${msg.id}`)) return;
      const wrapper = document.createElement("div");
      wrapper.id = `msg-${msg.id}`;
      wrapper.className = "mb-2 d-flex " + (msg.sender_id === currentUserId ? "justify-content-end" : "justify-content-start");
      wrapper.innerHTML = `
        <div class="d-inline-block p-2 rounded" style="max-width:70%; background-color:${msg.sender_id === currentUserId ? "var(--pastel-sky)" : "var(--pastel-mint)"}; border:2px solid black; border-radius:20px 5px 20px 5px;">
          ${msg.content}
          <small class="text-muted d-block">${formatTime(msg.created_at)}</small>
        </div>
      `;
      container.appendChild(wrapper);
    }

    function scrollToBottom() {
      container.scrollTop = container.scrollHeight;
    }

    // Load initial messages
    const snapshot = await messagesRef.orderBy("created_at", "desc").limit(30).get();
    const msgs = [];
    snapshot.forEach(doc => msgs.push({ id: doc.id, ...doc.data() }));
    msgs.reverse().forEach(renderMessage);
    scrollToBottom();

    // Mark messages as seen
    if (msgs.length) {
      const batch = db.batch();
      msgs.forEach(m => {
        if (m.sender_id !== currentUserId && !m.seen) {
          batch.update(messagesRef.doc(m.id), { seen: true });
        }
      });
      try { await batch.commit(); } catch (e) { console.warn(e); }
    }

    // Realtime listener
    messagesRef.orderBy("created_at", "desc").limit(1).onSnapshot(snap => {
      snap.docChanges().forEach(change => {
        if (change.type === "added") {
          const m = { id: change.doc.id, ...change.doc.data() };
          if (!document.getElementById(`msg-${m.id}`)) {
            renderMessage(m);
            scrollToBottom();
            if (m.sender_id !== currentUserId) {
              messagesRef.doc(m.id).update({ seen: true });
            }
          }
        }
      });
    });

    // Send message
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;

      const doc = {
        conversation_id: conversationId,
        sender_id: currentUserId,
        content: text,
        message_type: "text",
        seen: false,
        created_at: firebase.firestore.FieldValue.serverTimestamp()
      };

      try {
        await messagesRef.add(doc);
        await convRef.set({
          last_message: text,
          last_message_time: firebase.firestore.FieldValue.serverTimestamp()
        }, { merge: true });
        input.value = "";
      } catch (err) {
        console.error("Send error:", err);
        alert("Message failed");
      }
    });
  }

  // =========================================================
  // CHAT LIST
  // =========================================================

  async function initChatList() {
    const container = document.getElementById("conversation-list");
    const currentUserId = window.CURRENT_USER_ID;
    if (!container) return;

    const ok = await ensureFirebaseAuth();
    if (!ok) {
      container.innerHTML = '<p class="notebook-lead">Unable to load conversations.</p>';
      return;
    }

    const membersRef = db.collection("conversation_members");
    const usersRef = db.collection("users");
    const convsRef = db.collection("conversations");

    const myMembers = await membersRef.where("user_id", "==", currentUserId).get();
    const convIds = [...new Set(myMembers.docs.map(d => d.data().conversation_id))];

    if (!convIds.length) {
      container.innerHTML = '<p class="notebook-lead">No conversations yet.</p>';
      return;
    }

    const conversations = [];

    for (const convId of convIds) {
      const convSnap = await convsRef.doc(convId).get();
      const convData = convSnap.exists ? convSnap.data() : {};
      const members = await membersRef.where("conversation_id", "==", convId).get();
      const other = members.docs.find(d => d.data().user_id !== currentUserId);
      let otherUser = null;
      if (other) {
        const uid = other.data().user_id;
        const uSnap = await usersRef.doc(String(uid)).get();
        otherUser = uSnap.exists ? uSnap.data() : null;
      }
      const msgsSnap = await db.collection("conversations").doc(convId).collection("messages")
        .where("seen", "==", false)
        .where("sender_id", "!=", currentUserId)
        .get();
      const unread = msgsSnap.size;

      conversations.push({
        id: convId,
        last_message: convData.last_message,
        last_message_time: convData.last_message_time,
        other_user: otherUser,
        unread_count: unread
      });
    }

    conversations.sort((a, b) => {
      const ta = a.last_message_time && (a.last_message_time.toDate ? a.last_message_time.toDate() : new Date(a.last_message_time));
      const tb = b.last_message_time && (b.last_message_time.toDate ? b.last_message_time.toDate() : new Date(b.last_message_time));
      return (tb || 0) - (ta || 0);
    });

    container.innerHTML = "";
    conversations.forEach(conv => {
      const card = document.createElement("div");
      card.className = `notebook-card p-3 mb-3 ${conv.unread_count > 0 ? "card-color-5" : ""}`;
      card.innerHTML = `
        <div class="d-flex align-items-center">
          <img src="/profile-images/${conv.other_user?.profile_image || "default_profile.png"}"
            class="rounded-circle me-2" style="width:40px;height:40px;object-fit:cover">
          <div class="flex-grow-1">
            <h3 class="h5 mb-1">
              <a href="/profile/${conv.other_user?.username || ""}" class="notebook-link">${conv.other_user?.full_name || "Unknown"}</a>
              ${conv.unread_count > 0 ? `<span class="badge bg-danger ms-2">${conv.unread_count} new</span>` : ""}
            </h3>
            <p class="mb-0 text-muted">${conv.last_message ? conv.last_message.substring(0, 50) : "No messages yet"}</p>
          </div>
          <a href="/chat/${conv.id}" class="notebook-btn">Open</a>
        </div>
      `;
      container.appendChild(card);
    });

    // Chat list is static - refresh on page reload. Navbar unread count updates via backend.
  }

  // =========================================================
  // PAGE ROUTER
  // =========================================================

  document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("message-container")) {
      initChatRoom();
    } else if (document.getElementById("conversation-list")) {
      initChatList();
    }
  });

})();
