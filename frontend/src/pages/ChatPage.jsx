import { useEffect, useRef, useState } from "react";
import { sendChat, getContent } from "../services/api";
import ContentCard from "../components/ContentCard";
import styles from "./ChatPage.module.css";

// Conversational recommendations. The backend /chat returns a natural-
// language reply (plain text), so to show "cards in chat" we load the
// catalog once and surface any catalog titles the assistant mentions as
// movie cards beneath its message.
export default function ChatPage() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hi! Ask me for something like \"show me movies like Dune\".",
      movies: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [catalog, setCatalog] = useState([]);
  const bottomRef = useRef(null);

  // Load the catalog once so we can match titles in assistant replies.
  useEffect(() => {
    getContent({ limit: 500 })
      .then(setCatalog)
      .catch(() => setCatalog([])); // non-fatal: chat still works as text
  }, []);

  // Auto-scroll to the newest message.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  // Find catalog movies whose title appears in the reply text.
  function moviesMentionedIn(text) {
    const lower = text.toLowerCase();
    return catalog.filter((m) => lower.includes(m.title.toLowerCase()));
  }

  async function handleSend(e) {
    e.preventDefault();
    const message = input.trim();
    if (!message || sending) return;

    setMessages((prev) => [...prev, { role: "user", text: message, movies: [] }]);
    setInput("");
    setSending(true);

    try {
      const { reply } = await sendChat(message);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: reply, movies: moviesMentionedIn(reply) },
      ]);
    } catch (err) {
      // Error handling: surface a friendly assistant bubble instead of crashing.
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `⚠️ ${err.message}`, movies: [] },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>Chat</h1>

      <div className={styles.thread}>
        {messages.map((msg, i) => (
          <div
            key={i}
            className={
              msg.role === "user" ? styles.rowUser : styles.rowAssistant
            }
          >
            <div
              className={
                msg.role === "user" ? styles.bubbleUser : styles.bubbleAssistant
              }
            >
              {msg.text}
              {msg.movies.length > 0 && (
                <div className={styles.cards}>
                  {msg.movies.map((item) => (
                    <ContentCard key={item.id} item={item} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator while waiting on the LLM. */}
        {sending && (
          <div className={styles.rowAssistant}>
            <div className={styles.bubbleAssistant}>
              <span className={styles.typing}>Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className={styles.composer} onSubmit={handleSend}>
        <input
          className={styles.input}
          placeholder="Ask for a recommendation..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
        />
        <button className={styles.send} type="submit" disabled={sending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
