// static/js/chat.js – Supabase realtime chat (FINAL OPTIMIZED VERSION)

(function () {

  // ---------------------------
  // Initialize Supabase client
  // ---------------------------

  const { createClient } = supabase;
  const supabaseClient = createClient(
    window.SUPABASE_URL,
    window.SUPABASE_ANON_KEY
  );


  // ---------------------------
  // Utility: format timestamp
  // ---------------------------

  function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }


  // =========================================================
  // CHAT ROOM LOGIC
  // =========================================================

  function initChatRoom() {

    const container = document.getElementById("message-container");
    const form = document.getElementById("message-form");
    const input = document.getElementById("message-input");

    const conversationId = window.CONVERSATION_ID;
    const currentUserId = window.CURRENT_USER_ID;

    if (!container || !form || !conversationId) return;


    // ----------------------------------
    // Load last 30 messages
    // ----------------------------------

    async function loadInitialMessages() {

      const { data, error } = await supabaseClient
        .from("messages")
        .select("*")
        .eq("conversation_id", conversationId)
        .order("created_at", { ascending: false })
        .limit(30);

      if (error) {
        console.error("Message load error:", error);
        return;
      }

      data.reverse().forEach(renderMessage);

      scrollToBottom();

      // mark messages as seen
      if (data.length) {

        await supabaseClient
          .from("messages")
          .update({ seen: true })
          .eq("conversation_id", conversationId)
          .neq("sender_id", currentUserId)
          .is("seen", false);

      }

    }


    // ----------------------------------
    // Render message bubble
    // ----------------------------------

    function renderMessage(msg) {

      if (document.getElementById(`msg-${msg.id}`)) return;

      const wrapper = document.createElement("div");

      wrapper.id = `msg-${msg.id}`;

      wrapper.className =
        "mb-2 d-flex " +
        (msg.sender_id === currentUserId
          ? "justify-content-end"
          : "justify-content-start");

      wrapper.innerHTML = `
        <div class="d-inline-block p-2 rounded"
        style="
        max-width:70%;
        background-color:${
          msg.sender_id === currentUserId
            ? "var(--pastel-sky)"
            : "var(--pastel-mint)"
        };
        border:2px solid black;
        border-radius:20px 5px 20px 5px;
        ">

        ${msg.content}

        <small class="text-muted d-block">
        ${formatTime(msg.created_at)}
        </small>

        </div>
      `;

      container.appendChild(wrapper);

    }


    function scrollToBottom() {
      container.scrollTop = container.scrollHeight;
    }


    // ----------------------------------
    // Realtime subscription
    // ----------------------------------

    supabaseClient
      .channel(`room-${conversationId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "messages",
          filter: `conversation_id=eq.${String(conversationId)}`
        },
        (payload) => {

          const newMsg = payload.new;

          renderMessage(newMsg);

          scrollToBottom();

          // mark as seen
          if (newMsg.sender_id !== currentUserId) {

            supabaseClient
              .from("messages")
              .update({ seen: true })
              .eq("id", newMsg.id);

          }

        }
      )
      .subscribe();


    // ----------------------------------
    // Send message
    // ----------------------------------

    form.addEventListener("submit", async (e) => {

      e.preventDefault();

      const text = input.value.trim();

      if (!text) return;

      const { error } = await supabaseClient
        .from("messages")
        .insert({
          conversation_id: conversationId,
          sender_id: currentUserId,
          content: text,
          message_type: "text",
          seen: false
        });

      if (error) {

        console.error("Send error:", error);
        alert("Message failed");

        return;

      }

      input.value = "";

      // update conversation preview
      await supabaseClient
        .from("conversations")
        .update({
          last_message: text,
          last_message_time: new Date().toISOString()
        })
        .eq("id", conversationId);

    });


    loadInitialMessages();

  }



  // =========================================================
  // CHAT LIST
  // =========================================================

  async function initChatList() {

    const container = document.getElementById("conversation-list");
    const currentUserId = window.CURRENT_USER_ID;

    if (!container) return;


    // ----------------------------------
    // Load conversation memberships
    // ----------------------------------

    const { data: memberships, error } = await supabaseClient
      .from("conversation_members")
      .select(`
        conversation_id,
        conversations (
          id,
          last_message,
          last_message_time
        )
      `)
      .eq("user_id", currentUserId);


    if (error) {

      console.error("Conversation load error:", error);

      container.innerHTML =
        '<p class="notebook-lead">Error loading conversations.</p>';

      return;

    }


    if (!memberships.length) {

      container.innerHTML =
        '<p class="notebook-lead">No conversations yet.</p>';

      return;

    }


    // ----------------------------------
    // Fetch extra data
    // ----------------------------------

    const convPromises = memberships.map(async (m) => {

      const convId = m.conversation_id;
      const conv = m.conversations;

      const { data: otherMember } = await supabaseClient
        .from("conversation_members")
        .select("user_id")
        .eq("conversation_id", convId)
        .neq("user_id", currentUserId)
        .single();

      let otherUser = null;

      if (otherMember) {

        const { data: user } = await supabaseClient
          .from("users")
          .select("id, full_name, username, profile_image")
          .eq("id", otherMember.user_id)
          .single();

        otherUser = user;

      }

      const { count } = await supabaseClient
        .from("messages")
        .select("*", { count: "exact", head: true })
        .eq("conversation_id", convId)
        .neq("sender_id", currentUserId)
        .eq("seen", false);

      return {

        id: convId,
        last_message: conv.last_message,
        last_message_time: conv.last_message_time,
        other_user: otherUser,
        unread_count: count || 0

      };

    });


    const conversations = await Promise.all(convPromises);

    conversations.sort(
      (a, b) =>
        new Date(b.last_message_time) - new Date(a.last_message_time)
    );


    // ----------------------------------
    // Render chat list
    // ----------------------------------

    container.innerHTML = "";

    conversations.forEach((conv) => {

      const card = document.createElement("div");

      card.className = `notebook-card p-3 mb-3 ${
        conv.unread_count > 0 ? "card-color-5" : ""
      }`;

      card.innerHTML = `
        <div class="d-flex align-items-center">
          <img
            src="/static/uploads/profile_images/${
              conv.other_user?.profile_image || "default_profile.png"
            }"
            class="rounded-circle me-2"
            style="width:40px;height:40px;object-fit:cover"
          >

          <div class="flex-grow-1">

            <h3 class="h5 mb-1">

              <a href="/profile/${conv.other_user?.username}"
                 class="notebook-link">

                 ${conv.other_user?.full_name || "Unknown"}

              </a>

              ${
                conv.unread_count > 0
                  ? `<span class="badge bg-danger ms-2">${conv.unread_count} new</span>`
                  : ""
              }

            </h3>

            <p class="mb-0 text-muted">
              ${
                conv.last_message
                  ? conv.last_message.substring(0, 50)
                  : "No messages yet"
              }
            </p>

          </div>

          <a href="/chat/${conv.id}" class="notebook-btn">
            Open
          </a>

        </div>
      `;

      container.appendChild(card);

    });


    // ----------------------------------
    // Realtime updates
    // ----------------------------------

    supabaseClient
      .channel("chat-list-updates")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "messages" },
        (payload) => {

          const newMsg = payload.new;

          if (newMsg.sender_id === currentUserId) return;

          initChatList();

        }
      )
      .subscribe();

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