/* چت آنلاین سایت — گفتگو درباره محتوای همین سایت (کاملاً محلی و آفلاین) */
(function () {
  var box = document.getElementById("chatBox");
  var msgs = document.getElementById("chatMsgs");
  var input = document.getElementById("chatText");
  var convId = null;
  var opened = false;

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }
  function addMsg(sender, text, extra) {
    var el = document.createElement("div");
    el.className = "msg " + sender;
    var who = sender === "visitor" ? (window.CHAT_YOU || "You") : (window.CHAT_BOT || "Bot");
    el.innerHTML = "<b>" + esc(who) + "</b> " + esc(text);
    if (extra && extra.link) {
      var a = document.createElement("a");
      a.href = extra.link;
      a.className = "lk";
      a.textContent = extra.link_title || extra.link;
      el.appendChild(a);
    }
    if (extra && extra.suggestions) {
      var wrap = document.createElement("div");
      wrap.className = "sugg";
      extra.suggestions.forEach(function (s) {
        var a = document.createElement("a");
        a.href = s.link;
        a.textContent = s.title;
        wrap.appendChild(a);
      });
      el.appendChild(wrap);
    }
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
  }

  window.chatToggle = function () {
    box.classList.toggle("open");
    if (box.classList.contains("open") && !opened) {
      opened = true;
      addMsg("bot", window.CHAT_GREETING || "");
      input.focus();
    }
  };

  window.chatSend = function () {
    var text = (input.value || "").trim();
    if (!text) return;
    input.value = "";
    addMsg("visitor", text);
    fetch("/chat/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conv_id: convId, body: text })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        convId = d.conv_id;
        if (d.last_reply) {
          if (typeof d.last_reply === "string") {
            addMsg("bot", d.last_reply);
          } else {
            addMsg("bot", d.last_reply.text, d.last_reply);
          }
        }
        try { localStorage.setItem("site_conv", String(convId)); } catch (e) {}
      })
      .catch(function () {
        addMsg("bot", "...");
      });
  };
})();
