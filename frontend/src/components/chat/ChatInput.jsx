import { Send, Loader2 } from 'lucide-react'

export default function ChatInput({ input, setInput, sendMessage, isLoading }) {
    return (
        <form onSubmit={sendMessage} className="shrink-0 flex gap-3">
            <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about your finances... (e.g., How much did I spend on Uber?)"
                className="input-field flex-1"
                disabled={isLoading}
            />
            <button
                type="submit"
                disabled={!input.trim() || isLoading}
                className="btn-primary px-4"
            >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
        </form>
    )
}
