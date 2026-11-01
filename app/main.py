import os
from flask import Flask, jsonify, render_template, request, session

from app.admin_agent import AdministratorAgent
from app.chatbot import Chatbot
from app.database import Database
from app.vector_store import StaticVectorStore

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def create_app(test_config=None):
    config = test_config or {}
    app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
    app.secret_key = config.get("SECRET_KEY", os.environ.get("CHATBOT_SECRET_KEY", "dev-only-change-me"))
    db_path = config.get("DATABASE", os.path.join(DATA_DIR, "chatbot.db"))
    chroma_path = config.get("CHROMA_PATH", os.path.join(DATA_DIR, "chroma"))
    database = Database(db_path)
    database.initialize()
    vector_store = StaticVectorStore(chroma_path, os.path.join(DATA_DIR, "static_knowledge.json"))
    administrator_agent = AdministratorAgent(database)
    chatbot = Chatbot(vector_store, database, administrator_agent)
    app.extensions["chatbot"] = chatbot
    app.extensions["administrator_agent"] = administrator_agent

    @app.get("/")
    def index():
        if "chat_session_id" not in session:
            session["chat_session_id"] = os.urandom(16).hex()
        return render_template("index.html")

    @app.post("/api/chat")
    def chat():
        payload = request.get_json(silent=True) or {}
        message = payload.get("message", "")
        if not isinstance(message, str) or not message.strip():
            return jsonify({"error": "Message is required."}), 400
        if "chat_session_id" not in session:
            session["chat_session_id"] = os.urandom(16).hex()
        response = chatbot.process(session["chat_session_id"], message.strip())
        return jsonify(response)

    @app.post("/api/reset")
    def reset():
        session_id = session.get("chat_session_id")
        if session_id:
            chatbot.sessions.pop(session_id, None)
            chatbot.pending_reservations.pop(session_id, None)
        return jsonify({"reply": "Conversation reset.", "session": {}})

    @app.get("/api/admin/requests")
    def admin_requests():
        status = request.args.get("status", "pending")
        return jsonify({"requests": administrator_agent.list_requests(status if status != "all" else None)})

    def admin_decision(reference, decision):
        try:
            reservation = administrator_agent.respond(reference, decision)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        if not reservation:
            return jsonify({"error": "Reservation request not found."}), 404
        return jsonify({"reservation": reservation})

    @app.post("/api/admin/respond")
    def admin_respond():
        payload = request.get_json(silent=True) or {}
        reference = payload.get("reference")
        decision = payload.get("decision")
        if not reference or not decision:
            return jsonify({"error": "Reference and decision are required."}), 400
        return admin_decision(reference, decision)

    @app.post("/api/admin/requests/<reference>/approve")
    def admin_approve(reference):
        return admin_decision(reference, "approve")

    @app.post("/api/admin/requests/<reference>/refuse")
    def admin_refuse(reference):
        return admin_decision(reference, "refuse")

    @app.post("/api/admin/requests/<reference>/reject")
    def admin_reject(reference):
        return admin_decision(reference, "refuse")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "vector_documents": vector_store.collection.count(), "dynamic_database": "connected"})

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
