class ChatMessage {
  final String text;
  final bool isUser;
  final String? infoUrl; // Link xem chi tiết (nếu có)

  const ChatMessage({required this.text, required this.isUser, this.infoUrl});
}
