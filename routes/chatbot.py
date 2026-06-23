from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from models import db
from models.user import User
from models.property import Property
from models.unit import Unit
from models.tenant import Tenant
from models.payment import Payment
from models.repair import Repair
from models.message import Message
from services.ai_service import LandlordProAI
from routes.landlord import landlord_stats
from routes.tenant import current_month_balance

chatbot_bp = Blueprint("chatbot", __name__)

@chatbot_bp.route("/chat")
@login_required
def chat():
    if current_user.role == "landlord":
        tenants = Tenant.query.join(Unit).join(Property).filter(Property.landlord_id == current_user.id).all()
        contacts = [t.user for t in tenants]
    else:
        tenant = current_user.tenant
        contacts = [tenant.unit.property.landlord] if tenant and tenant.unit else []
    return render_template("chat.html", contacts=contacts)

@chatbot_bp.route("/api/messages/<int:other_user_id>")
@login_required
def messages(other_user_id):
    # Basic access control: only existing counterpart conversations are shown.
    other = db.session.get(User, other_user_id) or abort(404)
    msgs = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other.id)) |
        ((Message.sender_id == other.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    return jsonify([{"id": m.id, "content": m.content, "sender_id": m.sender_id, "is_me": m.sender_id == current_user.id, "time": m.created_at.strftime("%H:%M")} for m in msgs])

@chatbot_bp.route("/api/messages", methods=["POST"])
@login_required
def send_message():
    data = request.get_json() or {}
    receiver_id = int(data.get("receiver_id") or 0)
    content = (data.get("content") or "").strip()
    if not receiver_id or not content:
        return jsonify({"success": False, "message": "Receiver and message are required."}), 400
    receiver = db.session.get(User, receiver_id) or abort(404)
    msg = Message(sender_id=current_user.id, receiver_id=receiver.id, content=content)
    db.session.add(msg)
    db.session.commit()
    return jsonify({"success": True, "message_id": msg.id})

@chatbot_bp.route("/ai-assistant")
@login_required
def ai_assistant():
    return render_template("ai_assistant.html")

@chatbot_bp.route("/api/ai", methods=["POST"])
@login_required
def ai_api():
    question = (request.get_json() or {}).get("question", "")
    if current_user.role == "landlord":
        stats = landlord_stats()
        tenant = None
    else:
        tenant = current_user.tenant
        rent, paid, balance = current_month_balance(tenant)
        stats = {"monthly_rent": rent, "paid": paid, "balance": balance}
    answer = LandlordProAI().answer(current_user, question, stats, tenant)
    return jsonify({"response": answer})

# Optional real-time chat over Socket.IO. The normal REST chat remains as fallback.
from extensions import socketio
from flask_socketio import emit, join_room

@socketio.on("join")
def socket_join(data):
    room = data.get("room")
    if room:
        join_room(room)
        emit("joined", {"room": room})

@socketio.on("send_message")
def socket_send_message(data):
    sender_id = int(data.get("sender_id"))
    receiver_id = int(data.get("receiver_id"))
    content = (data.get("content") or "").strip()
    if not content:
        return
    msg = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.session.add(msg)
    db.session.commit()
    payload = {"id": msg.id, "sender_id": sender_id, "receiver_id": receiver_id, "content": content, "time": msg.created_at.strftime("%H:%M")}
    room = "-".join(map(str, sorted([sender_id, receiver_id])))
    emit("new_message", payload, room=room)
